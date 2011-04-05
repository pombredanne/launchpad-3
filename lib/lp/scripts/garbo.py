# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
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
from fixtures import TempDir
import logging
import multiprocessing
import os
import signal
import subprocess
import threading
import time

from psycopg2 import IntegrityError
import pytz
from storm.expr import LeftJoin
from storm.locals import (
    And,
    Count,
    Max,
    Min,
    SQL,
    )
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database import postgresql
from canonical.database.sqlbase import (
    cursor,
    session_store,
    sqlvalues,
    )
from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.database.librarian import (
    LibraryFileAlias,
    TimeLimitedToken,
    )
from canonical.launchpad.database.oauth import OAuthNonce
from canonical.launchpad.database.openidconsumer import OpenIDConsumerNonce
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.utilities.looptuner import TunableLoop
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from canonical.librarian.utils import copy_and_close
from lp.archiveuploader.dscfile import findFile
from lp.archiveuploader.nascentuploadfile import UploadError
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.model.bug import Bug
from lp.bugs.model.bugattachment import BugAttachment
from lp.bugs.model.bugnotification import BugNotification
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
from lp.services.memcache.interfaces import IMemcacheClient
from lp.services.scripts.base import (
    LaunchpadCronScript,
    SilentLaunchpadScriptFailure,
    )
from lp.services.session.model import SessionData
from lp.soyuz.model.files import SourcePackageReleaseFile
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.model.potranslation import POTranslation


ONE_DAY_IN_SECONDS = 24*60*60


def subprocess_setup():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


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
    target_table_key_type = 'integer'

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
            WHERE %s IN (
                SELECT id FROM
                cursor_fetch('%s', %d) AS f(id %s))
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
            SELECT potranslation FROM POComment

            UNION ALL SELECT msgstr0 FROM TranslationMessage
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
    target_table_key_type = 'text'


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
    target_table_class = OAuthNonce
    ids_to_prune_query = """
        SELECT id FROM OAuthNonce
        WHERE request_timestamp
            < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - CAST('1 day' AS interval)
        """


class OpenIDConsumerNoncePruner(TunableLoop):
    """An ITunableLoop to prune old OpenIDConsumerNonce records.

    We remove all OpenIDConsumerNonce records older than 1 day.
    """
    maximum_chunk_size = 6*60*60 # 6 hours in seconds.

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
            self.max_offset = -1 # Trigger isDone() now.
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

    maximum_chunk_size = 1000

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
        # We multiply chunk_size by 1000 for the sake of doing updates
        # quickly.
        chunk_size = int(chunk_size * 1000)

        transaction.begin()
        outdated_bugs = self._outdated_bugs[:chunk_size]
        self.log.debug("Updating heat for %s bugs" % outdated_bugs.count())
        outdated_bugs.set(
            heat=SQL('calculate_bug_heat(Bug.id)'),
            heat_last_updated=datetime.now(pytz.utc))

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

    maximum_chunk_size = 24*60*60 # 24 hours in seconds.

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


class PopulateSPRChangelogs(TunableLoop):
    maximum_chunk_size = 1

    def __init__(self, log, abort_time=None):
        super(PopulateSPRChangelogs, self).__init__(log, abort_time)
        value = getUtility(IMemcacheClient).get('populate-spr-changelogs')
        if not value:
            self.start_at = 0
        else:
            self.start_at = value
        self.finish_at = self.getCandidateSPRs(0).last()

    def getCandidateSPRs(self, start_at):
        return IMasterStore(SourcePackageRelease).using(
            SourcePackageRelease,
            # Find any SPRFs that have expired (LFA.content IS NULL).
            LeftJoin(
                SourcePackageReleaseFile,
                SourcePackageReleaseFile.sourcepackagereleaseID ==
                    SourcePackageRelease.id),
            LeftJoin(
                LibraryFileAlias,
                And(LibraryFileAlias.id ==
                    SourcePackageReleaseFile.libraryfileID,
                    LibraryFileAlias.content == None)),
            # And exclude any SPRs that have any expired SPRFs.
            ).find(
                SourcePackageRelease.id,
                SourcePackageRelease.id >= start_at,
                SourcePackageRelease.changelog == None,
            ).group_by(SourcePackageRelease.id).having(
                Count(LibraryFileAlias) == 0
            ).order_by(SourcePackageRelease.id)

    def isDone(self):
        return self.start_at > self.finish_at

    def __call__(self, chunk_size):
        for sprid in self.getCandidateSPRs(self.start_at)[:chunk_size]:
            spr = SourcePackageRelease.get(sprid)
            with TempDir() as tmp_dir:
                dsc_file = None

                # Grab the files from the librarian into a temporary
                # directory.
                try:
                    for sprf in spr.files:
                        dest = os.path.join(
                            tmp_dir.path, sprf.libraryfile.filename)
                        dest_file = open(dest, 'w')
                        sprf.libraryfile.open()
                        copy_and_close(sprf.libraryfile, dest_file)
                        if dest.endswith('.dsc'):
                            dsc_file = dest
                except LookupError:
                    self.log.warning(
                        'SPR %d (%s %s) has missing library files.' % (
                            spr.id, spr.name, spr.version))
                    continue

                if dsc_file is None:
                    self.log.warning(
                        'SPR %d (%s %s) has no DSC.' % (
                            spr.id, spr.name, spr.version))
                    continue

                # Extract the source package. Throw away stdout/stderr
                # -- we only really care about the return code.
                fnull = open('/dev/null', 'w')
                ret = subprocess.call(
                    ['dpkg-source', '-x', dsc_file, os.path.join(
                        tmp_dir.path, 'extracted')],
                        stdout=fnull, stderr=fnull,
                        preexec_fn=subprocess_setup)
                fnull.close()
                if ret != 0:
                    self.log.warning(
                        'SPR %d (%s %s) failed to unpack: returned %d' % (
                            spr.id, spr.name, spr.version, ret))
                    continue

                # We have an extracted source package. Let's get the
                # changelog. findFile ensures that it's not too huge, and
                # not a symlink.
                try:
                    changelog_path = findFile(
                        tmp_dir.path, 'debian/changelog')
                except UploadError, e:
                    changelog_path = None
                    self.log.warning(
                        'SPR %d (%s %s) changelog could not be '
                        'imported: %s' % (
                            spr.id, spr.name, spr.version, e))
                if changelog_path:
                    # The LFA should be restricted only if there aren't any
                    # public publications.
                    restricted = not any(
                        not a.private for a in spr.published_archives)
                    spr.changelog = getUtility(ILibraryFileAliasSet).create(
                        'changelog',
                        os.stat(changelog_path).st_size,
                        open(changelog_path, "r"),
                        "text/x-debian-source-changelog",
                        restricted=restricted)
                    self.log.info('SPR %d (%s %s) changelog imported.' % (
                        spr.id, spr.name, spr.version))
                else:
                    self.log.warning('SPR %d (%s %s) had no changelog.' % (
                        spr.id, spr.name, spr.version))

        self.start_at = spr.id + 1
        result = getUtility(IMemcacheClient).set(
            'populate-spr-changelogs', self.start_at)
        if not result:
            self.log.warning('Failed to set start_at in memcache.')
        transaction.commit()


class BaseDatabaseGarbageCollector(LaunchpadCronScript):
    """Abstract base class to run a collection of TunableLoops."""
    script_name = None # Script name for locking and database user. Override.
    tunable_loops = None # Collection of TunableLoops. Override.
    continue_on_failure = False # If True, an exception in a tunable loop
                                # does not cause the script to abort.

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
            dest="abort_script", default=None, action="store", type="float",
            metavar="SECS", help="Abort script after SECS seconds.")
        self.parser.add_option("--abort-task",
            dest="abort_task", default=None, action="store", type="float",
            metavar="SECS", help="Abort a task if it runs over SECS seconds.")
        self.parser.add_option("--threads",
            dest="threads", default=multiprocessing.cpu_count(),
            action="store", type="int", metavar='NUM',
            help="Run NUM tasks in parallel [Default %d]."
            % multiprocessing.cpu_count())

    def main(self):
        start_time = time.time()

        # Stores the number of failed tasks.
        self.failure_count = 0

        if self.options.experimental:
            tunable_loops = list(
                self.tunable_loops + self.experimental_tunable_loops)
        else:
            tunable_loops = list(self.tunable_loops)

        a_very_long_time = 31536000 # 1 year
        abort_task = self.options.abort_task or a_very_long_time
        abort_script = self.options.abort_script or a_very_long_time

        def worker():
            self.logger.debug(
                "Worker thread %s running.", threading.currentThread().name)
            self.login()
            while True:
                try:
                    tunable_loop_class = tunable_loops.pop(0)
                except IndexError:
                    break

                if start_time + abort_script - time.time() <= 0:
                    # Exit silently. We warn later.
                    self.logger.debug(
                        "Worker thread %s detected script timeout.",
                        threading.currentThread().name)
                    break

                loop_name = tunable_loop_class.__name__

                # Configure logging for this loop to use a prefix. Log
                # output from multiple threads will be interleaved, and
                # this lets us tell log output from different tasks
                # apart.
                loop_logger = logging.getLogger('garbo.' + loop_name)
                loop_logger.addFilter(PrefixFilter(loop_name))

                loop_logger.info("Running %s", loop_name)


                abort_time = min(
                    abort_task,
                    abort_script + start_time - time.time())

                tunable_loop = tunable_loop_class(
                    abort_time=abort_time, log=loop_logger)

                if self._maximum_chunk_size is not None:
                    tunable_loop.maximum_chunk_size = self._maximum_chunk_size

                try:
                    tunable_loop.run()
                    loop_logger.debug("%s completed sucessfully.", loop_name)
                except Exception:
                    loop_logger.exception("Unhandled exception")
                    self.failure_count += 1
                finally:
                    transaction.abort()

        threads = set()
        for count in range(0, self.options.threads):
            thread = threading.Thread(
                target=worker,name='Worker-%d' % (count+1,))
            thread.start()
            threads.add(thread)

        # Block until all the worker threads have completed. We block
        # until the script timeout is hit, plus 60 seconds. We wait the
        # extra time because the loops are supposed to shut themselves
        # down when the script timeout is hit, and the extra time is to
        # give them a chance to clean up.
        for thread in threads:
            time_to_go = min(
                abort_task,
                start_time + abort_script - time.time()) + 60
            if time_to_go > 0:
                thread.join(time_to_go)
            else:
                break

        # If the script ran out of time, warn.
        if start_time + abort_script - time.time() < 0:
            self.logger.warn(
                "Script aborted after %d seconds.", abort_script)

        if self.failure_count:
            raise SilentLaunchpadScriptFailure(self.failure_count)


class HourlyDatabaseGarbageCollector(BaseDatabaseGarbageCollector):
    script_name = 'garbo-hourly'
    tunable_loops = [
        OAuthNoncePruner,
        OpenIDConsumerNoncePruner,
        OpenIDConsumerAssociationPruner,
        RevisionCachePruner,
        BugHeatUpdater,
        BugWatchScheduler,
        AntiqueSessionPruner,
        UnusedSessionPruner,
        DuplicateSessionPruner,
        PopulateSPRChangelogs,
        ]
    experimental_tunable_loops = []

    def add_my_options(self):
        super(HourlyDatabaseGarbageCollector, self).add_my_options()
        # By default, abort any tunable loop taking more than 15 minutes.
        self.parser.set_defaults(abort_task=900)
        # And abort the script if it takes more than 55 minutes.
        self.parser.set_defaults(abort_script=55*60)


class DailyDatabaseGarbageCollector(BaseDatabaseGarbageCollector):
    script_name = 'garbo-daily'
    tunable_loops = [
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
        ]
    experimental_tunable_loops = [
        PersonPruner,
        ]

    def add_my_options(self):
        super(DailyDatabaseGarbageCollector, self).add_my_options()
        # Abort script after 24 hours by default.
        self.parser.set_defaults(abort_script=86400)
