# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['RemoveObsoleteTranslations']

import time

from zope.component import getUtility
from zope.interface import implements

from canonical.database.sqlbase import quote

from canonical.launchpad.interfaces import DistroSeriesStatus
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.looptuner import ITunableLoop

from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.utilities.looptuner import LoopTuner
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


collect_order = [
    'POTemplate',
    'POFile',
    'TranslationImportQueueEntry',
    'POTMsgSet',
    'TranslationTemplateItem',
    'TranslationMessage',
    'POFileTranslator',
    ]


remove_order = collect_order[:]
remove_order.reverse()


collection_query = """
    DROP TABLE IF EXISTS %(temporary_table)s;
    CREATE TEMP TABLE %(temporary_table)s
        AS SELECT %(table)s.id AS id
        FROM %(table)s
        JOIN %(join_table)s ON %(table)s.%(join_column)s = %(join_table)s.id;
    CREATE UNIQUE INDEX %(temporary_table)s_idx ON %(temporary_table)s (id);
    ANALYZE %(temporary_table)s"""


# POTemplate
collect_obsolete_potemplates_query = """
    DROP TABLE IF EXISTS %(temporary_table)s;
    CREATE TEMP TABLE %(temporary_table)s
    AS SELECT %(table)s.id AS id
    FROM %(table)s
        JOIN %(join_table)s ON %(table)s.%(join_column)s = %(join_table)s.id
    WHERE distroseries.distribution = %(distribution)s
          AND distroseries.releasestatus = %(releasestatus)s;
    CREATE UNIQUE INDEX %(temporary_table)s_idx ON %(temporary_table)s (id);
    ANALYZE %(temporary_table)s"""


# Query to remove subset of entries based on a temporary table.
deletion_query = """
    DELETE FROM %(table)s
    WHERE id IN (
        SELECT id
        FROM %(temporary_table)s
        LIMIT %%d OFFSET %%d
        )"""


def commit_transaction(transaction, logger, dry_run=False):
    """Commit ongoing transaction, start a new one.

    Pauses process execution to give the database slave a chance
    to keep up.
    """
    if transaction is None:
        return

    if not dry_run:
        transaction.commit()
        transaction.begin()


class DeletionLoopRunner(object):
    """Generic loop tuner for removal of obsolete translations."""
    implements(ITunableLoop)

    def __init__(self, table_entry, transaction, logger, store,
                 throttle=0.0, dry_run=False):
        """Initialize the loop."""
        size = table_entry['total']
        self.table = table_entry['table']
        self.removal_sql = deletion_query % table_entry

        self._txn = transaction
        self._logger = logger
        self._store = store
        self._throttle = throttle
        self._dry_run = dry_run
        self._iteration_end = size
        self._iterations_done = 0
        self._commit_count = 0

    def isDone(self):
        """See `ITunableLoop`."""
        return self._iterations_done >= self._iteration_end

    def __call__(self, chunk_size):
        """See `ITunableLoop`."""
        chunk_size = int(chunk_size)
        query = self.removal_sql % (chunk_size, self._iterations_done)
        result = self._store.execute(query)
        self._logger.debug(
            " * Removed another %d %ss (%d of %d)." % (
                result._raw_cursor.rowcount,
                self.table,
                self._iterations_done + result._raw_cursor.rowcount,
                self._iteration_end))
        self._iterations_done += result._raw_cursor.rowcount
        commit_transaction(self._txn, self._logger, dry_run=self._dry_run)
        self._commit_count += 1

    def getTotalCommits(self):
        return self._commit_count


class RemoveObsoleteTranslations(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option(
            '-d', '--dry-run', action="store_true", dest='dry_run',
            default=False, help="Don't really make any database changes.")

        self.parser.add_option(
            '-l', '--loop-timing', dest='loop_time',
            default=5, help="Time in seconds for the loop to run.")

        self.parser.add_option(
            '-t', '--throttle', dest='throttle',
            default=5, help="Time in seconds to sleep between commits.")

    def main(self):
        removal_traits = {
            'TranslationMessage' :
                { 'table' : 'TranslationMessage',
                  'temporary_table' : 'obsolete_translationmessage',
                  'join_table' : 'obsolete_pofile',
                  'join_column' : 'pofile',
                  },
            'TranslationTemplateItem' :
                { 'table' : 'TranslationTemplateItem',
                  'temporary_table' : 'obsolete_tti',
                  'join_table' : 'obsolete_potemplate',
                  'join_column' : 'potemplate',
                  },
            'POTMsgSet' :
                { 'table' : 'POTMsgSet',
                  'temporary_table' : 'obsolete_potmsgset',
                  'join_table' : 'obsolete_potemplate',
                  'join_column' : 'potemplate',
                  },
            'POFileTranslator' :
                { 'table' : 'POFileTranslator',
                  'temporary_table' : 'obsolete_pofiletranslator',
                  'join_table' : 'obsolete_pofile',
                  'join_column' : 'pofile',
                  },
            'POFile' :
                { 'table' : 'POFile',
                  'temporary_table' : 'obsolete_pofile',
                  'join_table' : 'obsolete_potemplate',
                  'join_column' : 'potemplate',
                  },
            'TranslationImportQueueEntry' :
                { 'table' : 'TranslationImportQueueEntry',
                  'temporary_table' : 'obsolete_queueentries',
                  'join_table' : 'obsolete_potemplate',
                  'join_column' : 'potemplate',
                  },
            'POTemplate' :
                { 'table' : 'POTemplate',
                  'temporary_table' : 'obsolete_potemplate',
                  'join_table' : 'distroseries',
                  'join_column' : 'distroseries',
                  'distribution' :
                    quote(getUtility(ILaunchpadCelebrities).ubuntu),
                  'releasestatus' : quote(DistroSeriesStatus.OBSOLETE),
                  'collection_sql' : collect_obsolete_potemplates_query,
                  },
            }

        if self.options.dry_run:
            self.logger.info("Dry run.  Not making any changes.")

        self.logger.debug(
            "Removing translations of obsolete Ubuntu versions")

        self._commit_count = 0

        # Working on the writable master store
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        self._store = store

        for table in collect_order:
            entry = removal_traits[table]
            if entry.has_key('collection_sql'):
                collect = store.execute(entry['collection_sql'] % entry)
            else:
                collect = store.execute(collection_query % entry)
            count = self._count_rows(entry['temporary_table'])
            entry['total'] = count
        self._do_commit()

        for table in remove_order:
            entry = removal_traits[table]
            self.logger.info(
                "Removing %d %s rows." % (entry['total'], table))
            loop = DeletionLoopRunner(
                entry, self.txn, self.logger, store,
                throttle=float(self.options.throttle),
                dry_run=self.options.dry_run)
            LoopTuner(loop, self.options.loop_time).run(
                sleep_between_commits=float(self.options.throttle))
            self._commit_count += loop.getTotalCommits()

        if self.options.dry_run:
            self.txn.abort()

        self.logger.info("Done with %d commits." % self._commit_count)
        self.logger.info("Statistics:")
        for table in remove_order:
            self.logger.info("\t%-30s: %d removed" % (
                    table, removal_traits[table]['total']))

    def _count_rows(self, tablename):
        """Helper to count all rows in a table."""
        count_query = "SELECT count(*) FROM %s"
        result = self._store.execute(
            count_query % tablename).get_one()
        return result[0]

    def _do_commit(self):
        """Commit ongoing transaction, start a new one.

        Pauses process execution to give the database slave a chance
        to keep up.
        """
        commit_transaction(self.txn, self.logger,
                           dry_run=self.options.dry_run)
        self._commit_count += 1
