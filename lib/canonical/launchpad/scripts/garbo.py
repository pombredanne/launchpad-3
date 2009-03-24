# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database garbage collection."""

__metaclass__ = type
__all__ = ['DailyDatabaseGarbageCollector', 'HourlyDatabaseGarbageCollector']

import transaction
from zope.component import getUtility
from zope.interface import implements
from storm.locals import SQL

from canonical.launchpad.database.codeimportresult import CodeImportResult
from canonical.launchpad.database.oauth import OAuthNonce
from canonical.launchpad.interfaces import IMasterStore
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.utilities.looptuner import LoopTuner
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


ONE_DAY_IN_SECONDS = 24*60*60


class TunableLoop:
    implements(ITunableLoop)

    goal_seconds = 4
    minimum_chunk_size = 1
    maximum_chunk_size = None # Override
    cooldown_time = 0

    def run(self):
        assert self.maximum_chunk_size is not None, "Did not override."
        LoopTuner(
            self, self.goal_seconds,
            minimum_chunk_size = self.minimum_chunk_size,
            maximum_chunk_size = self.maximum_chunk_size,
            cooldown_time = self.cooldown_time).run()


class OAuthNoncePruner(TunableLoop):
    """An ITunableLoop to prune old OAuthNonce records.

    We remove all OAuthNonce records older than 1 day.
    """
    maximum_chunk_size = 6*60*60 # 6 hours in seconds.

    def __init__(self):
        self.store = IMasterStore(OAuthNonce)
        self.oldest_age = self.store.execute("""
            SELECT COALESCE(EXTRACT(EPOCH FROM
                CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - MIN(request_timestamp)), 0)
            FROM OAuthNonce
            """).get_one()[0]

    def isDone(self):
        return self.oldest_age <= ONE_DAY_IN_SECONDS

    def __call__(self, chunk_size):
        self.oldest_age = max(ONE_DAY_IN_SECONDS, self.oldest_age - chunk_size)

        self.store.find(
            OAuthNonce,
            OAuthNonce.request_timestamp < SQL(
                "CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '%d seconds'"
                % self.oldest_age)).remove()
        transaction.commit()


class OpenIDNoncePruner(TunableLoop):
    """An ITunableLoop to prune old OpenIDNonce records.

    We remove all OpenIDNonce records older than 1 day.
    """
    maximum_chunk_size = 6*60*60 # 6 hours in seconds.

    def __init__(self):
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        self.oldest_age = self.store.execute("""
            SELECT COALESCE(
                EXTRACT(EPOCH FROM CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                - MIN(timestamp), 0)
            FROM OpenIDNonce
            """).get_one()[0]

    def isDone(self):
        return self.oldest_age <= ONE_DAY_IN_SECONDS

    def __call__(self, chunk_size):
        self.oldest_age = max(ONE_DAY_IN_SECONDS, self.oldest_age - chunk_size)
        self.store.execute("""
            DELETE FROM OpenIDNonce
            WHERE timestamp < CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - interval '%d seconds'
            """ % self.oldest_age)
        transaction.commit()


class CodeImportResultPruner(TunableLoop):
    """A TunableLoop to prune unwanted CodeImportResult rows.

    Removes CodeImportResult rows if they are older than 30 days
    and they are not one of the 4 most recent results for that
    CodeImport.
    """
    maximum_chunk_size = 100
    def __init__(self):
        self.store = IMasterStore(CodeImportResult)
        self.min_code_import, self.max_code_import = self.store.execute("""
            SELECT
                coalesce(min(code_import),0),
                coalesce(max(code_import),-1)
            FROM CodeImportResult
            """).get_one()
        self.next_code_import_id = self.min_code_import

    def isDone(self):
        return self.next_code_import_id > self.max_code_import

    def __call__(self, chunk_size):
        self.store.execute("""
            DELETE FROM CodeImportResult
            WHERE
                CodeImportResult.date_created
                    < CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                        - interval '30 days'
                AND CodeImportResult.code_import >= %d
                AND CodeImportResult.code_import < %d + %d
                AND CodeImportResult.id NOT IN (
                    SELECT LatestResult.id
                    FROM CodeImportResult AS LatestResult
                    WHERE
                        LatestResult.code_import
                            = CodeImportResult.code_import
                    ORDER BY LatestResult.id DESC
                    LIMIT 4)
            """ % sqlvalues(
                self.code_import_id, self.code_import_id, chunk_size))
        self.code_import_id += chunk_size
        transaction.commit()


class BaseDatabaseGarbageCollector(LaunchpadCronScript):
    """Abstract base class to run a collection of TunableLoops."""
    script_name = None # Script name for locking and database user. Override.
    tunable_loops = None # Collection of TunableLoops. Override.

    def __init__(self, test_args=None):
        super(BaseDatabaseGarbageCollector, self).__init__(
            self.script_name, dbuser=self.script_name, test_args=test_args)

    def main(self):
        for tunable_loop in self.tunable_loops:
            self.logger.info("Running %s" % tunable_loop.__name__)
            tunable_loop().run()


class HourlyDatabaseGarbageCollector(BaseDatabaseGarbageCollector):
    script_name = 'garbo-hourly'
    tunable_loops = [
        OAuthNoncePruner,
        OpenIDNoncePruner,
        ]

class DailyDatabaseGarbageCollector(BaseDatabaseGarbageCollector):
    script_name = 'garbo-daily'
    tunable_loops = [
        CodeImportResultPruner,
        ]

