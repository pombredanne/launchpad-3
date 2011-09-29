# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database garbage collection."""

__metaclass__ = type
__all__ = [
    'DailyDatabaseGarbageCollector',
    'HourlyDatabaseGarbageCollector',
    ]

from datetime import (
    datetime,
    timedelta,
    )
import logging
import multiprocessing
import os
import threading
import time

from contrib.glock import (
    GlobalLock,
    LockAlreadyAcquired,
    )
from psycopg2 import IntegrityError
import pytz
from storm.expr import In
from storm.locals import (
    Max,
    Min,
    SQL,
    )
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database import postgresql
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    cursor,
    session_store,
    sqlvalues,
    )
from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.database.librarian import TimeLimitedToken
from canonical.launchpad.database.oauth import OAuthNonce
from canonical.launchpad.database.openidconsumer import OpenIDConsumerNonce
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.utilities.looptuner import TunableLoop
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from lp.answers.model.answercontact import AnswerContact
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    BugTaskStatusSearch,
    )
from lp.bugs.model.bug import Bug
from lp.bugs.model.bugattachment import BugAttachment
from lp.bugs.model.bugnotification import BugNotification
from lp.bugs.model.bugtask import BugTask
from lp.bugs.model.bugwatch import BugWatchActivity
from lp.bugs.scripts.checkwatches.scheduler import (
    BugWatchScheduler,
    MAX_SAMPLE_SIZE,
    )
from lp.code.interfaces.revision import IRevisionSet
from lp.code.model.codeimportevent import CodeImportEvent
from lp.code.model.codeimportresult import CodeImportResult
from lp.code.model.revision import (
    RevisionAuthor,
    RevisionCache,
    )
from lp.hardwaredb.model.hwdb import HWSubmission
from lp.registry.model.person import Person
from lp.services.job.model.job import Job
from lp.services.log.logger import PrefixFilter
from lp.services.propertycache import cachedproperty
from lp.services.scripts.base import (
    LaunchpadCronScript,
    LOCK_PATH,
    SilentLaunchpadScriptFailure,
    )
from lp.services.session.model import SessionData
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.model.potmsgset import POTMsgSet
from lp.translations.model.potranslation import POTranslation
from lp.translations.model.translationmessage import TranslationMessage
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )


ONE_DAY_IN_SECONDS = 24 * 60 * 60


class BulkPruner(TunableLoop):
    """A abstract ITunableLoop base class for simple pruners.

    This is designed for the case where calculating the list of items
    is expensive, and this list may be huge. For this use case, it
    is impractical to calculate a batch of ids to remove each
    iteration.

    One approach is using a temporary table, populating it
    with the set of items to remove at the start. However, this
    approach can perform badly as you either need to prune the
    temporary table as you go, or using OFFSET to skip to the next
    batch to remove which gets slower as we progress further through
    the list.

    Instead, this implementation declares a CURSOR that can be used
    across multiple transactions, allowing us to calculate the set
    of items to remove just once and iterate over it, avoiding the
    seek-to-batch issues with a temporary table and OFFSET yet
    deleting batches of rows in separate transactions.
    """

    # The Storm database class for the table we are removing records
    # from. Must be overridden.
    target_table_class = None

    # The column name in target_table we use as the key. The type must
    # match that returned by the ids_to_prune_query and the
    # target_table_key_type. May be overridden.
    target_table_key = 'id'

    # SQL type of the target_table_key. May be overridden.
    target_table_key_type = 'id integer'

    # An SQL query returning a list of ids to remove from target_table.
    # The query must return a single column named 'id' and should not
    # contain duplicates. Must be overridden.
    ids_to_prune_query = None

    # See `TunableLoop`. May be overridden.
    maximum_chunk_size = 10000

    def getStore(self):
        """The master Store for the table we are pruning.

        May be overridden.
        """
        return IMasterStore(self.target_table_class)

    _unique_counter = 0

    def __init__(self, log, abort_time=None):
        super(BulkPruner, self).__init__(log, abort_time)

        self.store = self.getStore()
        self.target_table_name = self.target_table_class.__storm_table__

        self._unique_counter += 1
        self.cursor_name = (
            'bulkprunerid_%s_%d'
            % (self.__class__.__name__, self._unique_counter)).lower()

        # Open the cursor.
        self.store.execute(
            "DECLARE %s NO SCROLL CURSOR WITH HOLD FOR %s"
            % (self.cursor_name, self.ids_to_prune_query))

    _num_removed = None

    def isDone(self):
        """See `ITunableLoop`."""
        return self._num_removed == 0

    def __call__(self, chunk_size):
        """See `ITunableLoop`."""
        result = self.store.execute("""
            DELETE FROM %s
            WHERE (%s) IN (
                SELECT * FROM
                cursor_fetch('%s', %d) AS f(%s))
            """
            % (
                self.target_table_name, self.target_table_key,
                self.cursor_name, chunk_size, self.target_table_key_type))
        self._num_removed = result.rowcount
        transaction.commit()

    def cleanUp(self):
        """See `ITunableLoop`."""
        self.store.execute("CLOSE %s" % self.cursor_name)


class POTranslationPruner(BulkPruner):
    """Remove unlinked POTranslation entries.

    XXX bug=723596 StuartBishop: This job only needs to run once per month.
    """
    target_table_class = POTranslation
    ids_to_prune_query = """
        SELECT POTranslation.id AS id FROM POTranslation
        EXCEPT (
            SELECT msgstr0 FROM TranslationMessage
                WHERE msgstr0 IS NOT NULL

            UNION ALL SELECT msgstr1 FROM TranslationMessage
                WHERE msgstr1 IS NOT NULL

            UNION ALL SELECT msgstr2 FROM TranslationMessage
                WHERE msgstr2 IS NOT NULL

            UNION ALL SELECT msgstr3 FROM TranslationMessage
                WHERE msgstr3 IS NOT NULL

            UNION ALL SELECT msgstr4 FROM TranslationMessage
                WHERE msgstr4 IS NOT NULL

            UNION ALL SELECT msgstr5 FROM TranslationMessage
                WHERE msgstr5 IS NOT NULL
            )
        """


class SessionPruner(BulkPruner):
    """Base class for session removal."""

    target_table_class = SessionData
    target_table_key = 'client_id'
    target_table_key_type = 'id text'


class AntiqueSessionPruner(SessionPruner):
    """Remove sessions not accessed for 60 days"""

    ids_to_prune_query = """
        SELECT client_id AS id FROM SessionData
        WHERE last_accessed < CURRENT_TIMESTAMP - CAST('60 days' AS interval)
        """


class UnusedSessionPruner(SessionPruner):
    """Remove sessions older than 1 day with no authentication credentials."""

    ids_to_prune_query = """
        SELECT client_id AS id FROM SessionData
        WHERE
            last_accessed < CURRENT_TIMESTAMP - CAST('1 day' AS interval)
            AND client_id NOT IN (
                SELECT client_id
                FROM SessionPkgData
                WHERE
                    product_id = 'launchpad.authenticateduser'
                    AND key='logintime')
        """


class DuplicateSessionPruner(SessionPruner):
    """Remove all but the most recent 6 authenticated sessions for a user.

    We sometimes see users with dozens or thousands of authenticated
    sessions. To limit exposure to replay attacks, we remove all but
    the most recent 6 of them for a given user.
    """

    ids_to_prune_query = """
        SELECT client_id AS id
        FROM (
            SELECT
                sessiondata.client_id,
                last_accessed,
                rank() OVER pickle AS rank
            FROM SessionData, SessionPkgData
            WHERE
                SessionData.client_id = SessionPkgData.client_id
                AND product_id = 'launchpad.authenticateduser'
                AND key='accountid'
            WINDOW pickle AS (PARTITION BY pickle ORDER BY last_accessed DESC)
            ) AS whatever
        WHERE
            rank > 6
            AND last_accessed < CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - CAST('1 hour' AS interval)
        """


class OAuthNoncePruner(BulkPruner):
    """An ITunableLoop to prune old OAuthNonce records.

    We remove all OAuthNonce records older than 1 day.
    """
    target_table_key = 'access_token, request_timestamp, nonce'
    target_table_key_type = (
        'access_token integer, request_timestamp timestamp without time zone,'
        ' nonce text')
    target_table_class = OAuthNonce
    ids_to_prune_query = """
        SELECT access_token, request_timestamp, nonce FROM OAuthNonce
        WHERE request_timestamp
            < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - CAST('1 day' AS interval)
        """


class BugSummaryJournalRollup(TunableLoop):
    """Rollup BugSummaryJournal rows into BugSummary."""
    maximum_chunk_size = 5000

    def __init__(self, log, abort_time=None):
        super(BugSummaryJournalRollup, self).__init__(log, abort_time)
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    def isDone(self):
        has_more = self.store.execute(
            "SELECT EXISTS (SELECT TRUE FROM BugSummaryJournal LIMIT 1)"
            ).get_one()[0]
        return not has_more

    def __call__(self, chunk_size):
        chunk_size = int(chunk_size + 0.5)
        self.store.execute(
            "SELECT bugsummary_rollup_journal(%s)", (chunk_size,),
            noresult=True)
        self.store.commit()


class OpenIDConsumerNoncePruner(TunableLoop):
    """An ITunableLoop to prune old OpenIDConsumerNonce records.

    We remove all OpenIDConsumerNonce records older than 1 day.
    """
    maximum_chunk_size = 6 * 60 * 60  # 6 hours in seconds.

    def __init__(self, log, abort_time=None):
        super(OpenIDConsumerNoncePruner, self).__init__(log, abort_time)
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        self.earliest_timestamp = self.store.find(
            Min(OpenIDConsumerNonce.timestamp)).one()
        utc_now = int(time.mktime(time.gmtime()))
        self.earliest_wanted_timestamp = utc_now - ONE_DAY_IN_SECONDS

    def isDone(self):
        return (
            self.earliest_timestamp is None
            or self.earliest_timestamp >= self.earliest_wanted_timestamp)

    def __call__(self, chunk_size):
        self.earliest_timestamp = min(
            self.earliest_wanted_timestamp,
            self.earliest_timestamp + chunk_size)

        self.log.debug(
            "Removing OpenIDConsumerNonce rows older than %s"
            % self.earliest_timestamp)

        self.store.find(
            OpenIDConsumerNonce,
            OpenIDConsumerNonce.timestamp < self.earliest_timestamp).remove()
        transaction.commit()


class OpenIDConsumerAssociationPruner(TunableLoop):
    minimum_chunk_size = 3500
    maximum_chunk_size = 50000

    table_name = 'OpenIDConsumerAssociation'

    _num_removed = None

    def __init__(self, log, abort_time=None):
        super(OpenIDConsumerAssociationPruner, self).__init__(log, abort_time)
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    def __call__(self, chunksize):
        result = self.store.execute("""
            DELETE FROM %s
            WHERE (server_url, handle) IN (
                SELECT server_url, handle FROM %s
                WHERE issued + lifetime <
                    EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
                LIMIT %d
                )
            """ % (self.table_name, self.table_name, int(chunksize)))
        self._num_removed = result.rowcount
        transaction.commit()

    def isDone(self):
        return self._num_removed == 0


class RevisionCachePruner(TunableLoop):
    """A tunable loop to remove old revisions from the cache."""

    maximum_chunk_size = 100

    def isDone(self):
        """We are done when there are no old revisions to delete."""
        epoch = datetime.now(pytz.UTC) - timedelta(days=30)
        store = IMasterStore(RevisionCache)
        results = store.find(
            RevisionCache, RevisionCache.revision_date < epoch)
        return results.count() == 0

    def __call__(self, chunk_size):
        """Delegate to the `IRevisionSet` implementation."""
        getUtility(IRevisionSet).pruneRevisionCache(chunk_size)
        transaction.commit()


class CodeImportEventPruner(BulkPruner):
    """Prune `CodeImportEvent`s that are more than a month old.

    Events that happened more than 30 days ago are really of no
    interest to us.
    """
    target_table_class = CodeImportEvent
    ids_to_prune_query = """
        SELECT id FROM CodeImportEvent
        WHERE date_created < CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            - CAST('30 days' AS interval)
        """


class CodeImportResultPruner(BulkPruner):
    """A TunableLoop to prune unwanted CodeImportResult rows.

    Removes CodeImportResult rows if they are older than 30 days
    and they are not one of the most recent results for that
    CodeImport.
    """
    target_table_class = CodeImportResult
    ids_to_prune_query = """
        SELECT id FROM (
            SELECT id, date_created, rank() OVER w AS rank
            FROM CodeImportResult
            WINDOW w AS (PARTITION BY code_import ORDER BY date_created DESC)
            ) AS whatever
        WHERE
            rank > %s
            AND date_created < CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - CAST('30 days' AS interval)
            """ % sqlvalues(config.codeimport.consecutive_failure_limit - 1)


class RevisionAuthorEmailLinker(TunableLoop):
    """A TunableLoop that links `RevisionAuthor` objects to `Person` objects.

    `EmailAddress` objects are looked up for `RevisionAuthor` objects
    that have not yet been linked to a `Person`.  If the
    `EmailAddress` is linked to a person, then the `RevisionAuthor` is
    linked to the same.
    """

    maximum_chunk_size = 1000

    def __init__(self, log, abort_time=None):
        super(RevisionAuthorEmailLinker, self).__init__(log, abort_time)
        self.author_store = IMasterStore(RevisionAuthor)
        self.email_store = IMasterStore(EmailAddress)

        (self.min_author_id,
         self.max_author_id) = self.author_store.find(
            (Min(RevisionAuthor.id), Max(RevisionAuthor.id))).one()

        self.next_author_id = self.min_author_id

    def isDone(self):
        return (self.min_author_id is None or
                self.next_author_id > self.max_author_id)

    def __call__(self, chunk_size):
        result = self.author_store.find(
            RevisionAuthor,
            RevisionAuthor.id >= self.next_author_id,
            RevisionAuthor.personID == None,
            RevisionAuthor.email != None)
        result.order_by(RevisionAuthor.id)
        authors = list(result[:chunk_size])

        # No more authors found.
        if len(authors) == 0:
            self.next_author_id = self.max_author_id + 1
            transaction.commit()
            return

        emails = dict(self.email_store.find(
            (EmailAddress.email.lower(), EmailAddress.personID),
            EmailAddress.email.lower().is_in(
                    [author.email.lower() for author in authors]),
            EmailAddress.status.is_in([EmailAddressStatus.PREFERRED,
                                       EmailAddressStatus.VALIDATED]),
            EmailAddress.personID != None))

        if emails:
            for author in authors:
                personID = emails.get(author.email.lower())
                if personID is None:
                    continue
                author.personID = personID

        self.next_author_id = authors[-1].id + 1
        transaction.commit()


class HWSubmissionEmailLinker(TunableLoop):
    """A TunableLoop that links `HWSubmission` objects to `Person` objects.

    `EmailAddress` objects are looked up for `HWSubmission` objects
    that have not yet been linked to a `Person`.  If the
    `EmailAddress` is linked to a person, then the `HWSubmission` is
    linked to the same.
    """
    maximum_chunk_size = 50000

    def __init__(self, log, abort_time=None):
        super(HWSubmissionEmailLinker, self).__init__(log, abort_time)
        self.submission_store = IMasterStore(HWSubmission)
        self.submission_store.execute(
            "DROP TABLE IF EXISTS NewlyMatchedSubmission")
        # The join with the Person table is to avoid any replication
        # lag issues - EmailAddress.person might reference a Person
        # that does not yet exist.
        self.submission_store.execute("""
            CREATE TEMPORARY TABLE NewlyMatchedSubmission AS
            SELECT
                HWSubmission.id AS submission,
                EmailAddress.person AS owner
            FROM HWSubmission, EmailAddress, Person
            WHERE HWSubmission.owner IS NULL
                AND EmailAddress.person = Person.id
                AND EmailAddress.status IN %s
                AND lower(HWSubmission.raw_emailaddress)
                    = lower(EmailAddress.email)
            """ % sqlvalues(
                [EmailAddressStatus.VALIDATED, EmailAddressStatus.PREFERRED]),
            noresult=True)
        self.submission_store.execute("""
            CREATE INDEX newlymatchsubmission__submission__idx
            ON NewlyMatchedSubmission(submission)
            """, noresult=True)
        self.matched_submission_count = self.submission_store.execute("""
            SELECT COUNT(*) FROM NewlyMatchedSubmission
            """).get_one()[0]
        self.offset = 0

    def isDone(self):
        return self.offset >= self.matched_submission_count

    def __call__(self, chunk_size):
        self.submission_store.execute("""
            UPDATE HWSubmission
            SET owner=NewlyMatchedSubmission.owner
            FROM (
                SELECT submission, owner
                FROM NewlyMatchedSubmission
                ORDER BY submission
                OFFSET %d
                LIMIT %d
                ) AS NewlyMatchedSubmission
            WHERE HWSubmission.id = NewlyMatchedSubmission.submission
            """ % (self.offset, chunk_size), noresult=True)
        self.offset += chunk_size
        transaction.commit()


class PersonPruner(TunableLoop):

    maximum_chunk_size = 1000

    def __init__(self, log, abort_time=None):
        super(PersonPruner, self).__init__(log, abort_time)
        self.offset = 1
        self.store = IMasterStore(Person)
        self.log.debug("Creating LinkedPeople temporary table.")
        self.store.execute(
            "CREATE TEMPORARY TABLE LinkedPeople(person integer primary key)")
        # Prefill with Person entries created after our OpenID provider
        # started creating personless accounts on signup.
        self.log.debug(
            "Populating LinkedPeople with post-OpenID created Person.")
        self.store.execute("""
            INSERT INTO LinkedPeople
            SELECT id FROM Person
            WHERE datecreated > '2009-04-01'
            """)
        transaction.commit()
        for (from_table, from_column, to_table, to_column, uflag, dflag) in (
                postgresql.listReferences(cursor(), 'person', 'id')):
            # Skip things that don't link to Person.id or that link to it from
            # TeamParticipation or EmailAddress, as all Person entries will be
            # linked to from these tables.  Similarly, PersonSettings can
            # simply be deleted if it exists, because it has a 1 (or 0) to 1
            # relationship with Person.
            if (to_table != 'person' or to_column != 'id'
                or from_table in ('teamparticipation', 'emailaddress',
                                  'personsettings')):
                continue
            self.log.debug(
                "Populating LinkedPeople from %s.%s"
                % (from_table, from_column))
            self.store.execute("""
                INSERT INTO LinkedPeople
                SELECT DISTINCT %(from_column)s AS person
                FROM %(from_table)s
                WHERE %(from_column)s IS NOT NULL
                EXCEPT ALL
                SELECT person FROM LinkedPeople
                """ % dict(from_table=from_table, from_column=from_column))
            transaction.commit()

        self.log.debug("Creating UnlinkedPeople temporary table.")
        self.store.execute("""
            CREATE TEMPORARY TABLE UnlinkedPeople(
                id serial primary key, person integer);
            """)
        self.log.debug("Populating UnlinkedPeople.")
        self.store.execute("""
            INSERT INTO UnlinkedPeople (person) (
                SELECT id AS person FROM Person
                WHERE teamowner IS NULL
                EXCEPT ALL
                SELECT person FROM LinkedPeople);
            """)
        transaction.commit()
        self.log.debug("Indexing UnlinkedPeople.")
        self.store.execute("""
            CREATE UNIQUE INDEX unlinkedpeople__person__idx ON
                UnlinkedPeople(person);
            """)
        self.log.debug("Analyzing UnlinkedPeople.")
        self.store.execute("""
            ANALYZE UnlinkedPeople;
            """)
        self.log.debug("Counting UnlinkedPeople.")
        self.max_offset = self.store.execute(
            "SELECT MAX(id) FROM UnlinkedPeople").get_one()[0]
        if self.max_offset is None:
            self.max_offset = -1  # Trigger isDone() now.
            self.log.debug("No Person records to remove.")
        else:
            self.log.info("%d Person records to remove." % self.max_offset)
        # Don't keep any locks open - we might block.
        transaction.commit()

    def isDone(self):
        return self.offset > self.max_offset

    def __call__(self, chunk_size):
        subquery = """
            SELECT person FROM UnlinkedPeople
            WHERE id BETWEEN %d AND %d
            """ % (self.offset, self.offset + chunk_size - 1)
        people_ids = ",".join(
            str(item[0]) for item in self.store.execute(subquery).get_all())
        self.offset += chunk_size
        try:
            # This would be dangerous if we were deleting a
            # team, so join with Person to ensure it isn't one
            # even in the rare case a person is converted to
            # a team during this run.
            self.store.execute("""
                DELETE FROM TeamParticipation
                USING Person
                WHERE TeamParticipation.person = Person.id
                    AND Person.teamowner IS NULL
                    AND Person.id IN (%s)
                """ % people_ids)
            self.store.execute("""
                UPDATE EmailAddress SET person=NULL
                WHERE person IN (%s)
                """ % people_ids)
            # This cascade deletes any PersonSettings records.
            self.store.execute("""
                DELETE FROM Person
                WHERE id IN (%s)
                """ % people_ids)
            transaction.commit()
            self.log.debug(
                "Deleted the following unlinked people: %s" % people_ids)
        except IntegrityError:
            # This case happens when a Person is linked to something
            # during the run. It is unlikely to occur, so just ignore
            # it again. Everything will clear up next run.
            transaction.abort()
            self.log.warning(
                "Failed to delete %d Person records. Left for next time."
                % chunk_size)


class BugNotificationPruner(BulkPruner):
    """Prune `BugNotificationRecipient` records no longer of interest.

    We discard all rows older than 30 days that have been sent. We
    keep 30 days worth or records to help diagnose email delivery issues.
    """
    target_table_class = BugNotification
    ids_to_prune_query = """
        SELECT BugNotification.id FROM BugNotification
        WHERE date_emailed < CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            - CAST('30 days' AS interval)
        """


class AnswerContactPruner(BulkPruner):
    """Remove old answer contacts which are no longer required.

    Remove a person as an answer contact if:
      their account has been deactivated for more than one day, or
      suspended for more than one week.
    """
    target_table_class = AnswerContact
    ids_to_prune_query = """
        SELECT DISTINCT AnswerContact.id
        FROM AnswerContact, Person, Account
        WHERE
            AnswerContact.person = Person.id
            AND Person.account = Account.id
            AND (
                (Account.date_status_set <
                CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - CAST('1 day' AS interval)
                AND Account.status = %s)
                OR
                (Account.date_status_set <
                CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - CAST('7 days' AS interval)
                AND Account.status = %s)
            )
        """ % (AccountStatus.DEACTIVATED.value, AccountStatus.SUSPENDED.value)


class BranchJobPruner(BulkPruner):
    """Prune `BranchJob`s that are in a final state and more than a month old.

    When a BranchJob is completed, it gets set to a final state.  These jobs
    should be pruned from the database after a month.
    """
    target_table_class = Job
    ids_to_prune_query = """
        SELECT DISTINCT Job.id
        FROM Job, BranchJob
        WHERE
            Job.id = BranchJob.job
            AND Job.date_finished < CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - CAST('30 days' AS interval)
        """


class BugHeatUpdater(TunableLoop):
    """A `TunableLoop` for bug heat calculations."""

    maximum_chunk_size = 5000

    def __init__(self, log, abort_time=None, max_heat_age=None):
        super(BugHeatUpdater, self).__init__(log, abort_time)
        self.transaction = transaction
        self.total_processed = 0
        self.is_done = False
        self.offset = 0
        if max_heat_age is None:
            max_heat_age = config.calculate_bug_heat.max_heat_age
        self.max_heat_age = max_heat_age

        self.store = IMasterStore(Bug)

    @property
    def _outdated_bugs(self):
        outdated_bugs = getUtility(IBugSet).getBugsWithOutdatedHeat(
            self.max_heat_age)
        # We remove the security proxy so that we can access the set()
        # method of the result set.
        return removeSecurityProxy(outdated_bugs)

    def isDone(self):
        """See `ITunableLoop`."""
        # When the main loop has no more Bugs to process it sets
        # offset to None. Until then, it always has a numerical
        # value.
        return self._outdated_bugs.is_empty()

    def __call__(self, chunk_size):
        """Retrieve a batch of Bugs and update their heat.

        See `ITunableLoop`.
        """
        chunk_size = int(chunk_size + 0.5)
        outdated_bugs = self._outdated_bugs[:chunk_size]
        # We don't use outdated_bugs.set() here to work around
        # Storm Bug #820290.
        outdated_bug_ids = [bug.id for bug in outdated_bugs]
        self.log.debug("Updating heat for %s bugs", len(outdated_bug_ids))
        IMasterStore(Bug).find(
            Bug, Bug.id.is_in(outdated_bug_ids)).set(
                heat=SQL('calculate_bug_heat(Bug.id)'),
                heat_last_updated=UTC_NOW)
        transaction.commit()


class BugTaskIncompleteMigrator(TunableLoop):
    """Migrate BugTaskStatus 'INCOMPLETE' to a concrete WITH/WITHOUT value."""

    maximum_chunk_size = 20000
    minimum_chunk_size = 100

    def __init__(self, log, abort_time=None, max_heat_age=None):
        super(BugTaskIncompleteMigrator, self).__init__(log, abort_time)
        self.transaction = transaction
        self.total_processed = 0
        self.is_done = False
        self.offset = 0
        self.store = IMasterStore(BugTask)
        self.query = self.store.find((BugTask, Bug),
            BugTask._status==BugTaskStatus.INCOMPLETE,
            BugTask.bugID==Bug.id)

    def isDone(self):
        """See `ITunableLoop`."""
        return self.query.is_empty()

    def __call__(self, chunk_size):
        """See `ITunableLoop`."""
        transaction.begin()
        tasks = list(self.query[:chunk_size])
        for (task, bug) in tasks:
            if (bug.date_last_message is None or
                task.date_incomplete > bug.date_last_message):
                task._status = BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE
            else:
                task._status = BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE
        self.log.debug("Updated status on %d tasks" % len(tasks))
        transaction.commit()


class BugWatchActivityPruner(BulkPruner):
    """A TunableLoop to prune BugWatchActivity entries."""
    target_table_class = BugWatchActivity
    # For each bug_watch, remove all but the most recent MAX_SAMPLE_SIZE
    # entries.
    ids_to_prune_query = """
        SELECT id FROM (
            SELECT id, rank() OVER w AS rank
            FROM BugWatchActivity
            WINDOW w AS (PARTITION BY bug_watch ORDER BY id DESC)
            ) AS whatever
        WHERE rank > %s
        """ % sqlvalues(MAX_SAMPLE_SIZE)


class ObsoleteBugAttachmentPruner(BulkPruner):
    """Delete bug attachments without a LibraryFileContent record.

    Our database schema allows LibraryFileAlias records that have no
    corresponding LibraryFileContent records.

    This class deletes bug attachments that reference such "content free"
    and thus completely useless LFA records.
    """
    target_table_class = BugAttachment
    ids_to_prune_query = """
        SELECT BugAttachment.id
        FROM BugAttachment, LibraryFileAlias
        WHERE
            BugAttachment.libraryfile = LibraryFileAlias.id
            AND LibraryFileAlias.content IS NULL
        """


class OldTimeLimitedTokenDeleter(TunableLoop):
    """Delete expired url access tokens from the session DB."""

    maximum_chunk_size = 24 * 60 * 60  # 24 hours in seconds.

    def __init__(self, log, abort_time=None):
        super(OldTimeLimitedTokenDeleter, self).__init__(log, abort_time)
        self.store = session_store()
        self._update_oldest()

    def _update_oldest(self):
        self.oldest_age = self.store.execute("""
            SELECT COALESCE(EXTRACT(EPOCH FROM
                CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - MIN(created)), 0)
            FROM TimeLimitedToken
            """).get_one()[0]

    def isDone(self):
        return self.oldest_age <= ONE_DAY_IN_SECONDS

    def __call__(self, chunk_size):
        self.oldest_age = max(
            ONE_DAY_IN_SECONDS, self.oldest_age - chunk_size)

        self.log.debug(
            "Removed TimeLimitedToken rows older than %d seconds"
            % self.oldest_age)
        self.store.find(
            TimeLimitedToken,
            TimeLimitedToken.created < SQL(
                "CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '%d seconds'"
                % ONE_DAY_IN_SECONDS)).remove()
        transaction.commit()
        self._update_oldest()


class SuggestiveTemplatesCacheUpdater(TunableLoop):
    """Refresh the SuggestivePOTemplate cache.

    This isn't really a TunableLoop.  It just pretends to be one to fit
    in with the garbo crowd.
    """
    maximum_chunk_size = 1

    done = False

    def isDone(self):
        """See `TunableLoop`."""
        return self.done

    def __call__(self, chunk_size):
        """See `TunableLoop`."""
        utility = getUtility(IPOTemplateSet)
        utility.wipeSuggestivePOTemplatesCache()
        utility.populateSuggestivePOTemplatesCache()
        transaction.commit()
        self.done = True


class UnusedPOTMsgSetPruner(TunableLoop):
    """Cleans up unused POTMsgSets."""

    done = False
    offset = 0
    maximum_chunk_size = 50000

    def isDone(self):
        """See `TunableLoop`."""
        return self.offset >= len(self.msgset_ids_to_remove)

    @cachedproperty
    def msgset_ids_to_remove(self):
        """Return the IDs of the POTMsgSets to remove."""
        query = """
            -- Get all POTMsgSet IDs which are obsolete (sequence == 0)
            -- and are not used (sequence != 0) in any other template.
            SELECT POTMsgSet
              FROM TranslationTemplateItem tti
              WHERE sequence=0 AND
              NOT EXISTS(
                SELECT id
                  FROM TranslationTemplateItem
                  WHERE potmsgset = tti.potmsgset AND sequence != 0)
            UNION
            -- Get all POTMsgSet IDs which are not referenced
            -- by any of the templates (they must have TTI rows for that).
            (SELECT POTMsgSet.id
               FROM POTMsgSet
               LEFT OUTER JOIN TranslationTemplateItem
                 ON TranslationTemplateItem.potmsgset = POTMsgSet.id
               WHERE
                 TranslationTemplateItem.potmsgset IS NULL);
            """
        store = IMasterStore(POTMsgSet)
        results = store.execute(query)
        ids_to_remove = [id for (id,) in results.get_all()]
        return ids_to_remove

    def __call__(self, chunk_size):
        """See `TunableLoop`."""
        # We cast chunk_size to an int to avoid issues with slicing
        # (DBLoopTuner passes in a float).
        chunk_size = int(chunk_size)
        msgset_ids_to_remove = (
            self.msgset_ids_to_remove[self.offset:][:chunk_size])
        # Remove related TranslationTemplateItems.
        store = IMasterStore(POTMsgSet)
        related_ttis = store.find(
            TranslationTemplateItem,
            In(TranslationTemplateItem.potmsgsetID, msgset_ids_to_remove))
        related_ttis.remove()
        # Remove related TranslationMessages.
        related_translation_messages = store.find(
            TranslationMessage,
            In(TranslationMessage.potmsgsetID, msgset_ids_to_remove))
        related_translation_messages.remove()
        store.find(
            POTMsgSet, In(POTMsgSet.id, msgset_ids_to_remove)).remove()
        self.offset = self.offset + chunk_size
        transaction.commit()


# XXX: StevenK 2011-09-14 bug=849683: This can be removed when done.
class SourcePackagePublishingHistorySPNPopulator(TunableLoop):
    """Populate the new sourcepackagename column of SPPH."""

    done = False
    maximum_chunk_size = 5000

    def findSPPHs(self):
        return IMasterStore(SourcePackagePublishingHistory).find(
            SourcePackagePublishingHistory,
            SourcePackagePublishingHistory.sourcepackagename == None
            ).order_by(SourcePackagePublishingHistory.id)

    def isDone(self):
        """See `TunableLoop`."""
        return self.done

    def __call__(self, chunk_size):
        """See `TunableLoop`."""
        spphs = self.findSPPHs()[:chunk_size]
        for spph in spphs:
            spph.sourcepackagename = (
                spph.sourcepackagerelease.sourcepackagename)
        transaction.commit()
        self.done = self.findSPPHs().is_empty()


# XXX: StevenK 2011-09-14 bug=849683: This can be removed when done.
class BinaryPackagePublishingHistoryBPNPopulator(TunableLoop):
    """Populate the new binarypackagename column of BPPH."""

    done = False
    maximum_chunk_size = 5000

    def findBPPHs(self):
        return IMasterStore(BinaryPackagePublishingHistory).find(
            BinaryPackagePublishingHistory,
            BinaryPackagePublishingHistory.binarypackagename == None
            ).order_by(BinaryPackagePublishingHistory.id)

    def isDone(self):
        """See `TunableLoop`."""
        return self.done

    def __call__(self, chunk_size):
        """See `TunableLoop`."""
        bpphs = self.findBPPHs()[:chunk_size]
        for bpph in bpphs:
            bpph.binarypackagename = (
                bpph.binarypackagerelease.binarypackagename)
        transaction.commit()
        self.done = self.findBPPHs().is_empty()


class BaseDatabaseGarbageCollector(LaunchpadCronScript):
    """Abstract base class to run a collection of TunableLoops."""
    script_name = None  # Script name for locking and database user. Override.
    tunable_loops = None  # Collection of TunableLoops. Override.
    continue_on_failure = False  # If True, an exception in a tunable loop
                                 # does not cause the script to abort.

    # Default run time of the script in seconds. Override.
    default_abort_script_time = None

    # _maximum_chunk_size is used to override the defined
    # maximum_chunk_size to allow our tests to ensure multiple calls to
    # __call__ are required without creating huge amounts of test data.
    _maximum_chunk_size = None

    def __init__(self, test_args=None):
        super(BaseDatabaseGarbageCollector, self).__init__(
            self.script_name,
            dbuser=self.script_name.replace('-', '_'),
            test_args=test_args)

    def add_my_options(self):

        self.parser.add_option("-x", "--experimental", dest="experimental",
            default=False, action="store_true",
            help="Run experimental jobs. Normally this is just for staging.")
        self.parser.add_option("--abort-script",
            dest="abort_script", default=self.default_abort_script_time,
            action="store", type="float", metavar="SECS",
            help="Abort script after SECS seconds [Default %d]."
            % self.default_abort_script_time)
        self.parser.add_option("--abort-task",
            dest="abort_task", default=None, action="store", type="float",
            metavar="SECS", help="Abort a task if it runs over SECS seconds "
                "[Default (threads * abort_script / tasks)].")
        self.parser.add_option("--threads",
            dest="threads", default=multiprocessing.cpu_count(),
            action="store", type="int", metavar='NUM',
            help="Run NUM tasks in parallel [Default %d]."
            % multiprocessing.cpu_count())

    def main(self):
        self.start_time = time.time()

        # Stores the number of failed tasks.
        self.failure_count = 0

        # Copy the list so we can safely consume it.
        tunable_loops = list(self.tunable_loops)
        if self.options.experimental:
            tunable_loops.extend(self.experimental_tunable_loops)

        threads = set()
        for count in range(0, self.options.threads):
            thread = threading.Thread(
                target=self.run_tasks_in_thread,
                name='Worker-%d' % (count + 1,),
                args=(tunable_loops,))
            thread.start()
            threads.add(thread)

        # Block until all the worker threads have completed. We block
        # until the script timeout is hit, plus 60 seconds. We wait the
        # extra time because the loops are supposed to shut themselves
        # down when the script timeout is hit, and the extra time is to
        # give them a chance to clean up.
        for thread in threads:
            time_to_go = self.get_remaining_script_time() + 60
            if time_to_go > 0:
                thread.join(time_to_go)
            else:
                break

        # If the script ran out of time, warn.
        if self.get_remaining_script_time() < 0:
            self.logger.warn(
                "Script aborted after %d seconds.", self.script_timeout)

        if tunable_loops:
            self.logger.warn("%d tasks did not run.", len(tunable_loops))

        if self.failure_count:
            self.logger.error("%d tasks failed.", self.failure_count)
            raise SilentLaunchpadScriptFailure(self.failure_count)

    def get_remaining_script_time(self):
        return self.start_time + self.script_timeout - time.time()

    @property
    def script_timeout(self):
        a_very_long_time = 31536000  # 1 year
        return self.options.abort_script or a_very_long_time

    def get_loop_logger(self, loop_name):
        """Retrieve a logger for use by a particular task.

        The logger will be configured to add the loop_name as a
        prefix to all log messages, making interleaved output from
        multiple threads somewhat readable.
        """
        loop_logger = logging.getLogger('garbo.' + loop_name)
        for filter in loop_logger.filters:
            if isinstance(filter, PrefixFilter):
                return loop_logger  # Already have a PrefixFilter attached.
        loop_logger.addFilter(PrefixFilter(loop_name))
        return loop_logger

    def get_loop_abort_time(self, num_remaining_tasks):
        # How long until the task should abort.
        if self.options.abort_task is not None:
            # Task timeout specified on command line.
            abort_task = self.options.abort_task

        elif num_remaining_tasks <= self.options.threads:
            # We have a thread for every remaining task. Let
            # the task run until the script timeout.
            self.logger.debug2(
                "Task may run until script timeout.")
            abort_task = self.get_remaining_script_time()

        else:
            # Evenly distribute the remaining time to the
            # remaining tasks.
            abort_task = (
                self.options.threads
                * self.get_remaining_script_time() / num_remaining_tasks)

        return min(abort_task, self.get_remaining_script_time())

    def run_tasks_in_thread(self, tunable_loops):
        """Worker thread target to run tasks.

        Tasks are removed from tunable_loops and run one at a time,
        until all tasks that can be run have been run or the script
        has timed out.
        """
        self.logger.debug(
            "Worker thread %s running.", threading.currentThread().name)
        self.login()

        while True:
            # How long until the script should abort.
            if self.get_remaining_script_time() <= 0:
                # Exit silently. We warn later.
                self.logger.debug(
                    "Worker thread %s detected script timeout.",
                    threading.currentThread().name)
                break

            num_remaining_tasks = len(tunable_loops)
            if not num_remaining_tasks:
                break
            tunable_loop_class = tunable_loops.pop(0)

            loop_name = tunable_loop_class.__name__

            loop_logger = self.get_loop_logger(loop_name)

            # Aquire a lock for the task. Multiple garbo processes
            # might be running simultaneously.
            loop_lock_path = os.path.join(
                LOCK_PATH, 'launchpad-garbo-%s.lock' % loop_name)
            # No logger - too noisy, so report issues ourself.
            loop_lock = GlobalLock(loop_lock_path, logger=None)
            try:
                loop_lock.acquire()
                loop_logger.debug("Aquired lock %s.", loop_lock_path)
            except LockAlreadyAcquired:
                # If the lock cannot be acquired, but we have plenty
                # of time remaining, just put the task back to the
                # end of the queue.
                if self.get_remaining_script_time() > 60:
                    loop_logger.debug3(
                        "Unable to acquire lock %s. Running elsewhere?",
                        loop_lock_path)
                    time.sleep(0.3)  # Avoid spinning.
                    tunable_loops.append(tunable_loop_class)
                # Otherwise, emit a warning and skip the task.
                else:
                    loop_logger.warn(
                        "Unable to acquire lock %s. Running elsewhere?",
                        loop_lock_path)
                continue

            try:
                loop_logger.info("Running %s", loop_name)

                abort_time = self.get_loop_abort_time(num_remaining_tasks)
                loop_logger.debug2(
                    "Task will be terminated in %0.3f seconds",
                    abort_time)

                tunable_loop = tunable_loop_class(
                    abort_time=abort_time, log=loop_logger)

                # Allow the test suite to override the chunk size.
                if self._maximum_chunk_size is not None:
                    tunable_loop.maximum_chunk_size = (
                        self._maximum_chunk_size)

                try:
                    tunable_loop.run()
                    loop_logger.debug(
                        "%s completed sucessfully.", loop_name)
                except Exception:
                    loop_logger.exception("Unhandled exception")
                    self.failure_count += 1

            finally:
                loop_lock.release()
                loop_logger.debug("Released lock %s.", loop_lock_path)
                transaction.abort()


class FrequentDatabaseGarbageCollector(BaseDatabaseGarbageCollector):
    """Run every 5 minutes.

    This may become even more frequent in the future.

    Jobs with low overhead can go here to distribute work more evenly.
    """
    script_name = 'garbo-frequently'
    tunable_loops = [
        BugSummaryJournalRollup,
        OAuthNoncePruner,
        OpenIDConsumerNoncePruner,
        OpenIDConsumerAssociationPruner,
        AntiqueSessionPruner,
        ]
    experimental_tunable_loops = []

    # 5 minmutes minus 20 seconds for cleanup. This helps ensure the
    # script is fully terminated before the next scheduled hourly run
    # kicks in.
    default_abort_script_time = 60 * 5 - 20


class HourlyDatabaseGarbageCollector(BaseDatabaseGarbageCollector):
    """Run every hour.

    Jobs we want to run fairly often but have noticable overhead go here.
    """
    script_name = 'garbo-hourly'
    tunable_loops = [
        RevisionCachePruner,
        BugWatchScheduler,
        UnusedSessionPruner,
        DuplicateSessionPruner,
        BugHeatUpdater,
        SourcePackagePublishingHistorySPNPopulator,
        BinaryPackagePublishingHistoryBPNPopulator,
        BugTaskIncompleteMigrator,
        ]
    experimental_tunable_loops = []

    # 1 hour, minus 5 minutes for cleanup. This ensures the script is
    # fully terminated before the next scheduled hourly run kicks in.
    default_abort_script_time = 60 * 55


class DailyDatabaseGarbageCollector(BaseDatabaseGarbageCollector):
    """Run every day.

    Jobs that don't need to be run frequently.

    If there is low overhead, consider putting these tasks in more
    frequently invoked lists to distribute the work more evenly.
    """
    script_name = 'garbo-daily'
    tunable_loops = [
        AnswerContactPruner,
        BranchJobPruner,
        BugNotificationPruner,
        BugWatchActivityPruner,
        CodeImportEventPruner,
        CodeImportResultPruner,
        HWSubmissionEmailLinker,
        ObsoleteBugAttachmentPruner,
        OldTimeLimitedTokenDeleter,
        RevisionAuthorEmailLinker,
        SuggestiveTemplatesCacheUpdater,
        POTranslationPruner,
        UnusedPOTMsgSetPruner,
        ]
    experimental_tunable_loops = [
        PersonPruner,
        ]

    # 1 day, minus 30 minutes for cleanup. This ensures the script is
    # fully terminated before the next scheduled daily run kicks in.
    default_abort_script_time = 60 * 60 * 23.5
