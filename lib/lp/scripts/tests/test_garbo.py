# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the database garbage collector."""

__metaclass__ = type
__all__ = []

from datetime import (
    datetime,
    timedelta,
    )
import logging
from StringIO import StringIO
import time

from pytz import UTC
from storm.expr import (
    In,
    Min,
    Not,
    SQL,
    )
from storm.locals import (
    Int,
    Storm,
    )
from storm.store import Store
from testtools.matchers import (
    Equals,
    GreaterThan,
    )
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database import sqlbase
from canonical.database.constants import (
    ONE_DAY_AGO,
    SEVEN_DAYS_AGO,
    THIRTY_DAYS_AGO,
    UTC_NOW,
    )
from canonical.launchpad.database.librarian import TimeLimitedToken
from canonical.launchpad.database.oauth import (
    OAuthAccessToken,
    OAuthNonce,
    )
from canonical.launchpad.database.openidconsumer import OpenIDConsumerNonce
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from canonical.testing.layers import (
    DatabaseLayer,
    LaunchpadScriptLayer,
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.answers.model.answercontact import AnswerContact
from lp.bugs.model.bugnotification import (
    BugNotification,
    BugNotificationRecipient,
    )
from lp.code.bzr import (
    BranchFormat,
    RepositoryFormat,
    )
from lp.code.enums import CodeImportResultStatus
from lp.code.interfaces.codeimportevent import ICodeImportEventSet
from lp.code.model.branchjob import (
    BranchJob,
    BranchUpgradeJob,
    )
from lp.code.model.codeimportevent import CodeImportEvent
from lp.code.model.codeimportresult import CodeImportResult
from lp.registry.interfaces.person import (
    IPersonSet,
    PersonCreationRationale,
    )
from lp.scripts.garbo import (
    AntiqueSessionPruner,
    BulkPruner,
    DailyDatabaseGarbageCollector,
    DuplicateSessionPruner,
    FrequentDatabaseGarbageCollector,
    HourlyDatabaseGarbageCollector,
    OpenIDConsumerAssociationPruner,
    UnusedSessionPruner,
    )
from lp.services.job.model.job import Job
from lp.services.log.logger import NullHandler
from lp.services.messages.model.message import Message
from lp.services.session.model import (
    SessionData,
    SessionPkgData,
    )
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import (
    person_logged_in,
    TestCase,
    TestCaseWithFactory,
    )
from lp.translations.model.potmsgset import POTMsgSet
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )


class TestGarboScript(TestCase):
    layer = LaunchpadScriptLayer

    def test_daily_script(self):
        """Ensure garbo-daily.py actually runs."""
        rv, out, err = run_script(
            "cronscripts/garbo-daily.py", ["-q"], expect_returncode=0)
        self.failIf(out.strip(), "Output to stdout: %s" % out)
        self.failIf(err.strip(), "Output to stderr: %s" % err)
        DatabaseLayer.force_dirty_database()

    def test_hourly_script(self):
        """Ensure garbo-hourly.py actually runs."""
        rv, out, err = run_script(
            "cronscripts/garbo-hourly.py", ["-q"], expect_returncode=0)
        self.failIf(out.strip(), "Output to stdout: %s" % out)
        self.failIf(err.strip(), "Output to stderr: %s" % err)


class BulkFoo(Storm):
    __storm_table__ = 'bulkfoo'
    id = Int(primary=True)


class BulkFooPruner(BulkPruner):
    target_table_class = BulkFoo
    ids_to_prune_query = "SELECT id FROM BulkFoo WHERE id < 5"
    maximum_chunk_size = 2


class TestBulkPruner(TestCase):
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestBulkPruner, self).setUp()

        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        self.store.execute("CREATE TABLE BulkFoo (id serial PRIMARY KEY)")

        for i in range(10):
            self.store.add(BulkFoo())

        self.log = logging.getLogger('garbo')

    def test_bulkpruner(self):
        pruner = BulkFooPruner(self.log)

        # The loop thinks there is stuff to do. Confirm the initial
        # state is sane.
        self.assertFalse(pruner.isDone())

        # An arbitrary chunk size.
        chunk_size = 2

        # Determine how many items to prune and to leave rather than
        # hardcode these numbers.
        num_to_prune = self.store.find(
            BulkFoo, BulkFoo.id < 5).count()
        num_to_leave = self.store.find(
            BulkFoo, BulkFoo.id >= 5).count()
        self.assertTrue(num_to_prune > chunk_size)
        self.assertTrue(num_to_leave > 0)

        # Run one loop. Make sure it committed by throwing away
        # uncommitted changes.
        pruner(chunk_size)
        transaction.abort()

        # Confirm 'chunk_size' items where removed; no more, no less.
        num_remaining = self.store.find(BulkFoo).count()
        expected_num_remaining = num_to_leave + num_to_prune - chunk_size
        self.assertEqual(num_remaining, expected_num_remaining)

        # The loop thinks there is more stuff to do.
        self.assertFalse(pruner.isDone())

        # Run the loop to completion, removing the remaining targetted
        # rows.
        while not pruner.isDone():
            pruner(1000000)
        transaction.abort()

        # Confirm we have removed all targetted rows.
        self.assertEqual(self.store.find(BulkFoo, BulkFoo.id < 5).count(), 0)

        # Confirm we have the expected number of remaining rows.
        # With the previous check, this means no untargetted rows
        # where removed.
        self.assertEqual(
            self.store.find(BulkFoo, BulkFoo.id >= 5).count(), num_to_leave)

        # Cleanup clears up our resources.
        pruner.cleanUp()

        # We can run it again - temporary objects cleaned up.
        pruner = BulkFooPruner(self.log)
        while not pruner.isDone():
            pruner(chunk_size)


class TestSessionPruner(TestCase):
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestCase, self).setUp()

        # Session database isn't reset between tests. We need to do this
        # manually.
        nuke_all_sessions = IMasterStore(SessionData).find(SessionData).remove
        nuke_all_sessions()
        self.addCleanup(nuke_all_sessions)

        recent = datetime.now(UTC)
        yesterday = recent - timedelta(days=1)
        ancient = recent - timedelta(days=61)

        self.make_session(u'recent_auth', recent, 'auth1')
        self.make_session(u'recent_unauth', recent, False)
        self.make_session(u'yesterday_auth', yesterday, 'auth2')
        self.make_session(u'yesterday_unauth', yesterday, False)
        self.make_session(u'ancient_auth', ancient, 'auth3')
        self.make_session(u'ancient_unauth', ancient, False)

        self.log = logging.getLogger('garbo')

    def make_session(self, client_id, accessed, authenticated=None):
        session_data = SessionData()
        session_data.client_id = client_id
        session_data.last_accessed = accessed
        IMasterStore(SessionData).add(session_data)

        if authenticated:
            # Add login time information.
            session_pkg_data = SessionPkgData()
            session_pkg_data.client_id = client_id
            session_pkg_data.product_id = u'launchpad.authenticateduser'
            session_pkg_data.key = u'logintime'
            session_pkg_data.pickle = 'value is ignored'
            IMasterStore(SessionPkgData).add(session_pkg_data)

            # Add authenticated as information.
            session_pkg_data = SessionPkgData()
            session_pkg_data.client_id = client_id
            session_pkg_data.product_id = u'launchpad.authenticateduser'
            session_pkg_data.key = u'accountid'
            # Normally Account.id, but the session pruning works
            # at the SQL level and doesn't unpickle anything.
            session_pkg_data.pickle = authenticated
            IMasterStore(SessionPkgData).add(session_pkg_data)

    def sessionExists(self, client_id):
        store = IMasterStore(SessionData)
        return not store.find(
            SessionData, SessionData.client_id == client_id).is_empty()

    def test_antique_session_pruner(self):
        chunk_size = 2
        pruner = AntiqueSessionPruner(self.log)
        try:
            while not pruner.isDone():
                pruner(chunk_size)
        finally:
            pruner.cleanUp()

        expected_sessions = set([
            u'recent_auth',
            u'recent_unauth',
            u'yesterday_auth',
            u'yesterday_unauth',
            # u'ancient_auth',
            # u'ancient_unauth',
            ])

        found_sessions = set(
            IMasterStore(SessionData).find(SessionData.client_id))

        self.assertEqual(expected_sessions, found_sessions)

    def test_unused_session_pruner(self):
        chunk_size = 2
        pruner = UnusedSessionPruner(self.log)
        try:
            while not pruner.isDone():
                pruner(chunk_size)
        finally:
            pruner.cleanUp()

        expected_sessions = set([
            u'recent_auth',
            u'recent_unauth',
            u'yesterday_auth',
            # u'yesterday_unauth',
            u'ancient_auth',
            # u'ancient_unauth',
            ])

        found_sessions = set(
            IMasterStore(SessionData).find(SessionData.client_id))

        self.assertEqual(expected_sessions, found_sessions)

    def test_duplicate_session_pruner(self):
        # None of the sessions created in setUp() are duplicates, so
        # they will all survive the pruning.
        expected_sessions = set([
            u'recent_auth',
            u'recent_unauth',
            u'yesterday_auth',
            u'yesterday_unauth',
            u'ancient_auth',
            u'ancient_unauth',
            ])

        now = datetime.now(UTC)

        # Make some duplicate logins from a few days ago.
        # Only the most recent 6 will be kept. Oldest is 'old dupe 9',
        # most recent 'old dupe 1'.
        for count in range(1, 10):
            self.make_session(
                u'old dupe %d' % count,
                now - timedelta(days=2, seconds=count),
                'old dupe')
        for count in range(1, 7):
            expected_sessions.add(u'old dupe %d' % count)

        # Make some other duplicate logins less than an hour old.
        # All of these will be kept.
        for count in range(1, 10):
            self.make_session(u'new dupe %d' % count, now, 'new dupe')
            expected_sessions.add(u'new dupe %d' % count)

        chunk_size = 2
        pruner = DuplicateSessionPruner(self.log)
        try:
            while not pruner.isDone():
                pruner(chunk_size)
        finally:
            pruner.cleanUp()

        found_sessions = set(
            IMasterStore(SessionData).find(SessionData.client_id))

        self.assertEqual(expected_sessions, found_sessions)


class TestGarbo(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestGarbo, self).setUp()

        # Silence the root Logger by instructing the garbo logger to not
        # propagate messages.
        self.log = logging.getLogger('garbo')
        self.log.addHandler(NullHandler())
        self.log.propagate = 0

        # Run the garbage collectors to remove any existing garbage,
        # starting us in a known state.
        self.runDaily()
        self.runHourly()
        self.runFrequently()

        # Capture garbo log output to tests can examine it.
        self.log_buffer = StringIO()
        handler = logging.StreamHandler(self.log_buffer)
        self.log.addHandler(handler)

    def runFrequently(self, maximum_chunk_size=2, test_args=()):
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser('garbo_daily')
        collector = FrequentDatabaseGarbageCollector(
            test_args=list(test_args))
        collector._maximum_chunk_size = maximum_chunk_size
        collector.logger = self.log
        collector.main()
        return collector

    def runDaily(self, maximum_chunk_size=2, test_args=()):
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser('garbo_daily')
        collector = DailyDatabaseGarbageCollector(test_args=list(test_args))
        collector._maximum_chunk_size = maximum_chunk_size
        collector.logger = self.log
        collector.main()
        return collector

    def runHourly(self, maximum_chunk_size=2, test_args=()):
        LaunchpadZopelessLayer.switchDbUser('garbo_hourly')
        collector = HourlyDatabaseGarbageCollector(test_args=list(test_args))
        collector._maximum_chunk_size = maximum_chunk_size
        collector.logger = self.log
        collector.main()
        return collector

    def test_OAuthNoncePruner(self):
        now = datetime.now(UTC)
        timestamps = [
            now - timedelta(days=2),  # Garbage
            now - timedelta(days=1) - timedelta(seconds=60),  # Garbage
            now - timedelta(days=1) + timedelta(seconds=60),  # Not garbage
            now,  # Not garbage
            ]
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        store = IMasterStore(OAuthNonce)

        # Make sure we start with 0 nonces.
        self.failUnlessEqual(store.find(OAuthNonce).count(), 0)

        for timestamp in timestamps:
            store.add(OAuthNonce(
                access_token=OAuthAccessToken.get(1),
                request_timestamp=timestamp,
                nonce=str(timestamp)))
        transaction.commit()

        # Make sure we have 4 nonces now.
        self.failUnlessEqual(store.find(OAuthNonce).count(), 4)

        self.runFrequently(
            maximum_chunk_size=60)  # 1 minute maximum chunk size

        store = IMasterStore(OAuthNonce)

        # Now back to two, having removed the two garbage entries.
        self.failUnlessEqual(store.find(OAuthNonce).count(), 2)

        # And none of them are older than a day.
        # Hmm... why is it I'm putting tz aware datetimes in and getting
        # naive datetimes back? Bug in the SQLObject compatibility layer?
        # Test is still fine as we know the timezone.
        self.failUnless(
            store.find(
                Min(OAuthNonce.request_timestamp)).one().replace(tzinfo=UTC)
            >= now - timedelta(days=1))

    def test_OpenIDConsumerNoncePruner(self):
        now = int(time.mktime(time.gmtime()))
        MINUTES = 60
        HOURS = 60 * 60
        DAYS = 24 * HOURS
        timestamps = [
            now - 2 * DAYS,  # Garbage
            now - 1 * DAYS - 1 * MINUTES,  # Garbage
            now - 1 * DAYS + 1 * MINUTES,  # Not garbage
            now,  # Not garbage
            ]
        LaunchpadZopelessLayer.switchDbUser('testadmin')

        store = IMasterStore(OpenIDConsumerNonce)

        # Make sure we start with 0 nonces.
        self.failUnlessEqual(store.find(OpenIDConsumerNonce).count(), 0)

        for timestamp in timestamps:
            store.add(OpenIDConsumerNonce(
                    u'http://server/', timestamp, u'aa'))
        transaction.commit()

        # Make sure we have 4 nonces now.
        self.failUnlessEqual(store.find(OpenIDConsumerNonce).count(), 4)

        # Run the garbage collector.
        self.runFrequently(maximum_chunk_size=60)  # 1 minute maximum chunks.

        store = IMasterStore(OpenIDConsumerNonce)

        # We should now have 2 nonces.
        self.failUnlessEqual(store.find(OpenIDConsumerNonce).count(), 2)

        # And none of them are older than 1 day
        earliest = store.find(Min(OpenIDConsumerNonce.timestamp)).one()
        self.failUnless(
            earliest >= now - 24 * 60 * 60, 'Still have old nonces')

    def test_CodeImportResultPruner(self):
        now = datetime.now(UTC)
        store = IMasterStore(CodeImportResult)

        results_to_keep_count = (
            config.codeimport.consecutive_failure_limit - 1)

        LaunchpadZopelessLayer.switchDbUser('testadmin')
        code_import_id = self.factory.makeCodeImport().id
        machine_id = self.factory.makeCodeImportMachine().id
        requester_id = self.factory.makePerson().id
        transaction.commit()

        def new_code_import_result(timestamp):
            LaunchpadZopelessLayer.switchDbUser('testadmin')
            CodeImportResult(
                date_created=timestamp,
                code_importID=code_import_id, machineID=machine_id,
                requesting_userID=requester_id,
                status=CodeImportResultStatus.FAILURE,
                date_job_started=timestamp)
            transaction.commit()

        new_code_import_result(now - timedelta(days=60))
        for i in range(results_to_keep_count - 1):
            new_code_import_result(now - timedelta(days=19 + i))

        # Run the garbage collector
        self.runDaily()

        # Nothing is removed, because we always keep the
        # ``results_to_keep_count`` latest.
        store = IMasterStore(CodeImportResult)
        self.failUnlessEqual(
            results_to_keep_count,
            store.find(CodeImportResult).count())

        new_code_import_result(now - timedelta(days=31))
        self.runDaily()
        store = IMasterStore(CodeImportResult)
        self.failUnlessEqual(
            results_to_keep_count,
            store.find(CodeImportResult).count())

        new_code_import_result(now - timedelta(days=29))
        self.runDaily()
        store = IMasterStore(CodeImportResult)
        self.failUnlessEqual(
            results_to_keep_count,
            store.find(CodeImportResult).count())

        # We now have no CodeImportResults older than 30 days
        self.failUnless(
            store.find(
                Min(CodeImportResult.date_created)).one().replace(tzinfo=UTC)
            >= now - timedelta(days=30))

    def test_CodeImportEventPruner(self):
        now = datetime.now(UTC)
        store = IMasterStore(CodeImportResult)

        LaunchpadZopelessLayer.switchDbUser('testadmin')
        machine = self.factory.makeCodeImportMachine()
        requester = self.factory.makePerson()
        # Create 6 code import events for this machine, 3 on each side of 30
        # days. Use the event set to the extra event data rows get created
        # too.
        event_set = getUtility(ICodeImportEventSet)
        for age in (35, 33, 31, 29, 27, 15):
            event_set.newOnline(
                machine, user=requester, message='Hello',
                _date_created=(now - timedelta(days=age)))
        transaction.commit()

        # Run the garbage collector
        self.runDaily()

        # Only the three most recent results are left.
        events = list(machine.events)
        self.assertEqual(3, len(events))
        # We now have no CodeImportEvents older than 30 days
        self.failUnless(
            store.find(
                Min(CodeImportEvent.date_created)).one().replace(tzinfo=UTC)
            >= now - timedelta(days=30))

    def test_OpenIDConsumerAssociationPruner(self):
        pruner = OpenIDConsumerAssociationPruner
        table_name = pruner.table_name
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        store_selector = getUtility(IStoreSelector)
        store = store_selector.get(MAIN_STORE, MASTER_FLAVOR)
        now = time.time()
        # Create some associations in the past with lifetimes
        for delta in range(0, 20):
            store.execute("""
                INSERT INTO %s (server_url, handle, issued, lifetime)
                VALUES (%s, %s, %d, %d)
                """ % (table_name, str(delta), str(delta), now - 10, delta))
        transaction.commit()

        # Ensure that we created at least one expirable row (using the
        # test start time as 'now').
        num_expired = store.execute("""
            SELECT COUNT(*) FROM %s
            WHERE issued + lifetime < %f
            """ % (table_name, now)).get_one()[0]
        self.failUnless(num_expired > 0)

        # Expire all those expirable rows, and possibly a few more if this
        # test is running slow.
        self.runFrequently()

        LaunchpadZopelessLayer.switchDbUser('testadmin')
        store = store_selector.get(MAIN_STORE, MASTER_FLAVOR)
        # Confirm all the rows we know should have been expired have
        # been expired. These are the ones that would be expired using
        # the test start time as 'now'.
        num_expired = store.execute("""
            SELECT COUNT(*) FROM %s
            WHERE issued + lifetime < %f
            """ % (table_name, now)).get_one()[0]
        self.failUnlessEqual(num_expired, 0)

        # Confirm that we haven't expired everything. This test will fail
        # if it has taken 10 seconds to get this far.
        num_unexpired = store.execute(
            "SELECT COUNT(*) FROM %s" % table_name).get_one()[0]
        self.failUnless(num_unexpired > 0)

    def test_RevisionAuthorEmailLinker(self):
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        rev1 = self.factory.makeRevision('Author 1 <author-1@Example.Org>')
        rev2 = self.factory.makeRevision('Author 2 <author-2@Example.Org>')
        rev3 = self.factory.makeRevision('Author 3 <author-3@Example.Org>')

        person1 = self.factory.makePerson(email='Author-1@example.org')
        person2 = self.factory.makePerson(
            email='Author-2@example.org',
            email_address_status=EmailAddressStatus.NEW)
        account3 = self.factory.makeAccount(
            'Author 3', 'Author-3@example.org')

        self.assertEqual(rev1.revision_author.person, None)
        self.assertEqual(rev2.revision_author.person, None)
        self.assertEqual(rev3.revision_author.person, None)

        self.runDaily()

        # Only the validated email address associated with a Person
        # causes a linkage.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(rev1.revision_author.person, person1)
        self.assertEqual(rev2.revision_author.person, None)
        self.assertEqual(rev3.revision_author.person, None)

        # Validating an email address creates a linkage.
        person2.validateAndEnsurePreferredEmail(person2.guessedemails[0])
        self.assertEqual(rev2.revision_author.person, None)

        self.runDaily()
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(rev2.revision_author.person, person2)

        # Creating a person for an existing account creates a linkage.
        person3 = account3.createPerson(PersonCreationRationale.UNKNOWN)
        self.assertEqual(rev3.revision_author.person, None)

        self.runDaily()
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(rev3.revision_author.person, person3)

    def test_HWSubmissionEmailLinker(self):
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        sub1 = self.factory.makeHWSubmission(
            emailaddress='author-1@Example.Org')
        sub2 = self.factory.makeHWSubmission(
            emailaddress='author-2@Example.Org')
        sub3 = self.factory.makeHWSubmission(
            emailaddress='author-3@Example.Org')

        person1 = self.factory.makePerson(email='Author-1@example.org')
        person2 = self.factory.makePerson(
            email='Author-2@example.org',
            email_address_status=EmailAddressStatus.NEW)
        account3 = self.factory.makeAccount(
            'Author 3', 'Author-3@example.org')

        self.assertEqual(sub1.owner, None)
        self.assertEqual(sub2.owner, None)
        self.assertEqual(sub3.owner, None)

        self.runDaily()

        # Only the validated email address associated with a Person
        # causes a linkage.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(sub1.owner, person1)
        self.assertEqual(sub2.owner, None)
        self.assertEqual(sub3.owner, None)

        # Validating an email address creates a linkage.
        person2.validateAndEnsurePreferredEmail(person2.guessedemails[0])
        self.assertEqual(sub2.owner, None)

        self.runDaily()
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(sub2.owner, person2)

        # Creating a person for an existing account creates a linkage.
        person3 = account3.createPerson(PersonCreationRationale.UNKNOWN)
        self.assertEqual(sub3.owner, None)

        self.runDaily()
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(sub3.owner, person3)

    def test_PersonPruner(self):
        personset = getUtility(IPersonSet)
        # Switch the DB user because the garbo_daily user isn't allowed to
        # create person entries.
        LaunchpadZopelessLayer.switchDbUser('testadmin')

        # Create two new person entries, both not linked to anything. One of
        # them will have the present day as its date created, and so will not
        # be deleted, whereas the other will have a creation date far in the
        # past, so it will be deleted.
        self.factory.makePerson(name='test-unlinked-person-new')
        person_old = self.factory.makePerson(name='test-unlinked-person-old')
        removeSecurityProxy(person_old).datecreated = datetime(
            2008, 01, 01, tzinfo=UTC)

        # Normally, the garbage collector will do nothing because the
        # PersonPruner is experimental
        self.runDaily()
        self.assertIsNot(
            personset.getByName('test-unlinked-person-new'), None)
        self.assertIsNot(
            personset.getByName('test-unlinked-person-old'), None)

        # When we run the garbage collector with experimental jobs turned
        # on, the old unlinked Person is removed.
        self.runDaily(test_args=['--experimental'])
        self.assertIsNot(
            personset.getByName('test-unlinked-person-new'), None)
        self.assertIs(personset.getByName('test-unlinked-person-old'), None)

    def test_BugNotificationPruner(self):
        # Create some sample data
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        notification = BugNotification(
            messageID=1,
            bugID=1,
            is_comment=True,
            date_emailed=None)
        BugNotificationRecipient(
            bug_notification=notification,
            personID=1,
            reason_header='Whatever',
            reason_body='Whatever')
        # We don't create an entry exactly 30 days old to avoid
        # races in the test.
        for delta in range(-45, -14, 2):
            message = Message(rfc822msgid=str(delta))
            notification = BugNotification(
                message=message,
                bugID=1,
                is_comment=True,
                date_emailed=UTC_NOW + SQL("interval '%d days'" % delta))
            BugNotificationRecipient(
                bug_notification=notification,
                personID=1,
                reason_header='Whatever',
                reason_body='Whatever')

        store = IMasterStore(BugNotification)

        # Ensure we are at a known starting point.
        num_unsent = store.find(
            BugNotification,
            BugNotification.date_emailed == None).count()
        num_old = store.find(
            BugNotification,
            BugNotification.date_emailed < THIRTY_DAYS_AGO).count()
        num_new = store.find(
            BugNotification,
            BugNotification.date_emailed > THIRTY_DAYS_AGO).count()

        self.assertEqual(num_unsent, 1)
        self.assertEqual(num_old, 8)
        self.assertEqual(num_new, 8)

        # Run the garbage collector.
        self.runDaily()

        # We should have 9 BugNotifications left.
        self.assertEqual(
            store.find(
                BugNotification,
                BugNotification.date_emailed == None).count(),
            num_unsent)
        self.assertEqual(
            store.find(
                BugNotification,
                BugNotification.date_emailed > THIRTY_DAYS_AGO).count(),
            num_new)
        self.assertEqual(
            store.find(
                BugNotification,
                BugNotification.date_emailed < THIRTY_DAYS_AGO).count(),
            0)

    def _test_AnswerContactPruner(self, status, interval, expected_count=0):
        # Garbo should remove answer contacts for accounts with given 'status'
        # which was set more than 'interval' days ago.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        store = IMasterStore(AnswerContact)

        person = self.factory.makePerson()
        person.addLanguage(getUtility(ILanguageSet)['en'])
        question = self.factory.makeQuestion()
        with person_logged_in(question.owner):
            question.target.addAnswerContact(person, person)
        Store.of(question).flush()
        self.assertEqual(
            store.find(
                AnswerContact,
                AnswerContact.person == person.id).count(),
                1)

        account = person.account
        account.status = status
        # We flush because a trigger sets the date_status_set and we need to
        # modify it ourselves.
        Store.of(account).flush()
        if interval is not None:
            account.date_status_set = interval

        self.runDaily()

        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(
            store.find(
                AnswerContact,
                AnswerContact.person == person.id).count(),
                expected_count)

    def test_AnswerContactPruner_deactivated_accounts(self):
        # Answer contacts with an account deactivated at least one day ago
        # should be pruned.
        self._test_AnswerContactPruner(AccountStatus.DEACTIVATED, ONE_DAY_AGO)

    def test_AnswerContactPruner_suspended_accounts(self):
        # Answer contacts with an account suspended at least seven days ago
        # should be pruned.
        self._test_AnswerContactPruner(
            AccountStatus.SUSPENDED, SEVEN_DAYS_AGO)

    def test_AnswerContactPruner_doesnt_prune_recently_changed_accounts(self):
        # Answer contacts which are suspended or deactivated inside the
        # minimum time interval are not pruned.
        self._test_AnswerContactPruner(
            AccountStatus.DEACTIVATED, None, expected_count=1)
        self._test_AnswerContactPruner(
            AccountStatus.SUSPENDED, ONE_DAY_AGO, expected_count=1)

    def test_BranchJobPruner(self):
        # Garbo should remove jobs completed over 30 days ago.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        store = IMasterStore(Job)

        db_branch = self.factory.makeAnyBranch()
        db_branch.branch_format = BranchFormat.BZR_BRANCH_5
        db_branch.repository_format = RepositoryFormat.BZR_KNIT_1
        Store.of(db_branch).flush()
        branch_job = BranchUpgradeJob.create(
            db_branch, self.factory.makePerson())
        branch_job.job.date_finished = THIRTY_DAYS_AGO

        self.assertEqual(
            store.find(
                BranchJob,
                BranchJob.branch == db_branch.id).count(),
                1)

        self.runDaily()

        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(
            store.find(
                BranchJob,
                BranchJob.branch == db_branch.id).count(),
                0)

    def test_BranchJobPruner_doesnt_prune_recent_jobs(self):
        # Check to make sure the garbo doesn't remove jobs that aren't more
        # than thirty days old.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        store = IMasterStore(Job)

        db_branch = self.factory.makeAnyBranch(
            branch_format=BranchFormat.BZR_BRANCH_5,
            repository_format=RepositoryFormat.BZR_KNIT_1)

        branch_job = BranchUpgradeJob.create(
            db_branch, self.factory.makePerson())
        branch_job.job.date_finished = THIRTY_DAYS_AGO

        db_branch2 = self.factory.makeAnyBranch(
            branch_format=BranchFormat.BZR_BRANCH_5,
            repository_format=RepositoryFormat.BZR_KNIT_1)
        BranchUpgradeJob.create(db_branch2, self.factory.makePerson())

        self.runDaily()

        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(store.find(BranchJob).count(), 1)

    def test_ObsoleteBugAttachmentPruner(self):
        # Bug attachments without a LibraryFileContent record are removed.

        LaunchpadZopelessLayer.switchDbUser('testadmin')
        bug = self.factory.makeBug()
        attachment = self.factory.makeBugAttachment(bug=bug)
        transaction.commit()

        # Bug attachments that have a LibraryFileContent record are
        # not deleted.
        self.assertIsNot(attachment.libraryfile.content, None)
        self.runDaily()
        self.assertEqual(bug.attachments.count(), 1)

        # But once we delete the LfC record, the attachment is deleted
        # in the next daily garbo run.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        removeSecurityProxy(attachment.libraryfile).content = None
        transaction.commit()
        self.runDaily()
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.assertEqual(bug.attachments.count(), 0)

    def test_TimeLimitedTokenPruner(self):
        # Ensure there are no tokens
        store = sqlbase.session_store()
        map(store.remove, store.find(TimeLimitedToken))
        store.flush()
        self.assertEqual(0, len(list(store.find(TimeLimitedToken,
            path="sample path"))))
        # One to clean and one to keep
        store.add(TimeLimitedToken(path="sample path", token="foo",
            created=datetime(2008, 01, 01, tzinfo=UTC)))
        store.add(TimeLimitedToken(path="sample path", token="bar")),
        store.commit()
        self.assertEqual(2, len(list(store.find(TimeLimitedToken,
            path="sample path"))))
        self.runDaily()
        self.assertEqual(0, len(list(store.find(TimeLimitedToken,
            path="sample path", token="foo"))))
        self.assertEqual(1, len(list(store.find(TimeLimitedToken,
            path="sample path", token="bar"))))

    def test_CacheSuggestivePOTemplates(self):
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        template = self.factory.makePOTemplate()
        self.runDaily()

        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        count, = store.execute("""
            SELECT count(*)
            FROM SuggestivePOTemplate
            WHERE potemplate = %s
            """ % sqlbase.quote(template.id)).get_one()

        self.assertEqual(1, count)

    def test_BugSummaryJournalRollup(self):
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

        # Generate a load of entries in BugSummaryJournal.
        store.execute("UPDATE BugTask SET status=42")

        # We only need a few to test.
        num_rows = store.execute(
            "SELECT COUNT(*) FROM BugSummaryJournal").get_one()[0]
        self.assertThat(num_rows, GreaterThan(10))

        self.runFrequently()

        # We just care that the rows have been removed. The bugsummary
        # tests confirm that the rollup stored method is working correctly.
        num_rows = store.execute(
            "SELECT COUNT(*) FROM BugSummaryJournal").get_one()[0]
        self.assertThat(num_rows, Equals(0))

    def test_UnusedPOTMsgSetPruner_removes_obsolete_message_sets(self):
        # UnusedPOTMsgSetPruner removes any POTMsgSet that are
        # participating in a POTemplate only as obsolete messages.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        pofile = self.factory.makePOFile()
        translation_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile)
        translation_message.potmsgset.setSequence(
            pofile.potemplate, 0)
        transaction.commit()
        store = IMasterStore(POTMsgSet)
        obsolete_msgsets = store.find(
            POTMsgSet,
            TranslationTemplateItem.potmsgset == POTMsgSet.id,
            TranslationTemplateItem.sequence == 0)
        self.assertNotEqual(0, obsolete_msgsets.count())
        self.runDaily()
        self.assertEqual(0, obsolete_msgsets.count())

    def test_UnusedPOTMsgSetPruner_removes_unreferenced_message_sets(self):
        # If a POTMsgSet is not referenced by any templates the
        # UnusedPOTMsgSetPruner will remove it.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        potmsgset = self.factory.makePOTMsgSet()
        # Cheekily drop any references to the POTMsgSet we just created.
        store = IMasterStore(POTMsgSet)
        store.execute(
            "DELETE FROM TranslationTemplateItem WHERE potmsgset = %s"
            % potmsgset.id)
        transaction.commit()
        unreferenced_msgsets = store.find(
            POTMsgSet,
            Not(In(
                POTMsgSet.id,
                SQL("SELECT potmsgset FROM TranslationTemplateItem"))))
        self.assertNotEqual(0, unreferenced_msgsets.count())
        self.runDaily()
        self.assertEqual(0, unreferenced_msgsets.count())

    def test_SourcePackagePublishingHistorySPNPopulator(self):
        # If SPPHs do not have sourcepackagename set, the populator will set
        # it.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        spph = self.factory.makeSourcePackagePublishingHistory()
        spn = spph.sourcepackagename
        spph.sourcepackagenameID = None
        transaction.commit()
        self.assertIs(None, spph.sourcepackagename)
        self.runHourly()
        self.assertEqual(spn, spph.sourcepackagename)

    def test_BinaryPackagePublishingHistoryBPNPopulator(self):
        # If BPPHs do not have binarypackagename set, the populator will set
        # it.
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        bpn = bpph.binarypackagename
        bpph.binarypackagenameID = None
        transaction.commit()
        self.assertIs(None, bpph.binarypackagename)
        self.runHourly()
        self.assertEqual(bpn, bpph.binarypackagename)
