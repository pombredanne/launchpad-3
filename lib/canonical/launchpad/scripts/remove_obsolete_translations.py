# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['RemoveObsoleteTranslations']

from zope.component import getUtility
from zope.interface import implements

from canonical.database.sqlbase import quote

from canonical.launchpad.interfaces import DistroSeriesStatus
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.looptuner import ITunableLoop

from lp.services.scripts.base import LaunchpadScript
from canonical.launchpad.utilities.looptuner import DBLoopTuner
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


remove_order = list(reversed(collect_order))


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
        ORDER BY id
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
    """Generic loop tuner for removal of obsolete translations data."""
    implements(ITunableLoop)

    def __init__(self, table_entry, transaction, logger, store,
                 dry_run=False):
        """Initialize the loop."""
        size = table_entry['total']
        self.table = table_entry['table']
        self.removal_sql = deletion_query % table_entry

        self._txn = transaction
        self._logger = logger
        self._store = store
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


class TranslationsStatusChecker:
    """Check if translations data is consistent after removal."""
    check_methods = {
        'productseries_potemplates' : 'collectProductSeriesStats',
        'other_distroseries_potemplates' : 'collectOtherDistroSeriesStats',
        'potemplate_potmsgsets' : 'collectPOTemplatePOTMsgSetStats',
        'potemplate_pofiles' : 'collectPOTemplatePOFileStats',
        'pofile_pofiletranslators' : 'collectPOFileTranslatorStats',
        'translationimportqueue_size' : 'getTranslationImportQueueSize',
        }

    def __init__(self, store, logger):
        self.store = store
        self.logger = logger
        self.problems = 0
        for attribute in self.check_methods:
            method = getattr(self, self.check_methods[attribute])
            self.logger.debug("Collecting %s..." % attribute)
            setattr(self, attribute, method())

    def postCheck(self):
        self.checkObsoletePOTemplates()

        for attribute in self.check_methods:
            self.genericCheck(attribute)

        if self.problems > 0:
            self.logger.info("%d problems found." % self.problems)
        else:
            self.logger.info("All checks passed.")

    def genericCheck(self, attribute_name):
        method = getattr(self, self.check_methods[attribute_name])
        new_stats = method()
        old_stats = getattr(self, attribute_name)
        if old_stats != new_stats:
            if not isinstance(old_stats, int):
                old_stats = len(old_stats)
                new_stats = len(new_stats)
            self.logger.warn(
                "Mismatch in %s (was %d long, now %d)." % (
                    attribute_name, old_stats, new_stats))
            self.problems += 1

    def checkObsoletePOTemplates(self):
        query = """SELECT COUNT(POTemplate.id) FROM POTemplate
                   JOIN DistroSeries
                     ON POTemplate.distroseries=DistroSeries.id
                   WHERE DistroSeries.releasestatus=%s AND
                         DistroSeries.distribution=%s""" % (
            quote(DistroSeriesStatus.OBSOLETE),
            quote(getUtility(ILaunchpadCelebrities).ubuntu))
        result = self.store.execute(query)
        count = result.get_one()
        if int(count[0]) != 0:
            self.logger.warn("\tObsolete POTemplates remaining: %s." % count)
            self.problems += 1

    def collectProductSeriesStats(self):
        query = """SELECT ProductSeries.id, COUNT(POTemplate.id)
                     FROM ProductSeries
                     JOIN POTemplate
                       ON POTemplate.productseries=ProductSeries.id
                     GROUP BY ProductSeries.id
                     ORDER BY ProductSeries.id"""
        result = self.store.execute(query)
        return result.get_all()

    def collectOtherDistroSeriesStats(self):
        query = """SELECT DistroSeries.id, COUNT(POTemplate.id)
                     FROM DistroSeries
                     JOIN POTemplate
                       ON POTemplate.distroseries=DistroSeries.id
                     WHERE DistroSeries.releasestatus != %s
                     GROUP BY DistroSeries.id
                     ORDER BY DistroSeries.id""" % quote(
            DistroSeriesStatus.OBSOLETE)
        result = self.store.execute(query)
        return result.get_all()

    def collectPOTemplatePOFileStats(self):
        query = """SELECT POTemplate.id, COUNT(POFile.id)
                     FROM POTemplate
                     LEFT OUTER JOIN DistroSeries
                       ON POTemplate.distroseries=DistroSeries.id
                     JOIN POFile
                       ON POFile.potemplate=POTemplate.id
                     WHERE (distroseries IS NOT NULL AND
                            DistroSeries.releasestatus != %s) OR
                           productseries IS NOT NULL
                     GROUP BY POTemplate.id
                     ORDER BY POTemplate.id""" % quote(
            DistroSeriesStatus.OBSOLETE)
        result = self.store.execute(query)
        return result.get_all()

    def collectPOTemplatePOTMsgSetStats(self):
        query = """SELECT POTemplate.id, COUNT(POTMsgSet.id)
                     FROM POTemplate
                     LEFT OUTER JOIN DistroSeries
                       ON POTemplate.distroseries=DistroSeries.id
                     JOIN POTMsgSet
                       ON POTMsgSet.potemplate=POTemplate.id
                     WHERE (distroseries IS NOT NULL AND
                            DistroSeries.releasestatus != %s) OR
                           productseries IS NOT NULL
                     GROUP BY POTemplate.id
                     ORDER BY POTemplate.id""" % quote(
            DistroSeriesStatus.OBSOLETE)
        result = self.store.execute(query)
        return result.get_all()

    def collectPOFileTranslatorStats(self):
        query = """SELECT POFile.id, COUNT(POFileTranslator.id)
                     FROM POFile
                     JOIN POTemplate
                       ON POFile.potemplate=POTemplate.id
                     LEFT OUTER JOIN DistroSeries
                       ON POTemplate.distroseries=DistroSeries.id
                     JOIN POFileTranslator
                       ON POFileTranslator.pofile=POFile.id
                     WHERE (distroseries IS NOT NULL AND
                            DistroSeries.releasestatus != %s) OR
                           productseries IS NOT NULL
                     GROUP BY POFile.id
                     ORDER BY POFile.id""" % quote(
            DistroSeriesStatus.OBSOLETE)
        result = self.store.execute(query)
        return result.get_all()

    def getTranslationImportQueueSize(self):
        query = """SELECT count(id) FROM TranslationImportQueueEntry"""
        result = self.store.execute(query)
        return int(result.get_one()[0])


class RemoveObsoleteTranslations(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option(
            '-d', '--dry-run', action="store_true", dest='dry_run',
            default=False, help="Don't really make any database changes.")

        self.parser.add_option(
            '-l', '--loop-timing', dest='loop_time',
            default=5, help="Time in seconds for the loop to run.")

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

        checker = TranslationsStatusChecker(store, self.logger)
        for table in collect_order:
            entry = removal_traits[table]
            collect_sql = entry.get('collection_sql', collection_query)
            collect = store.execute(collect_sql % entry)
            count = self._count_rows(entry['temporary_table'])
            entry['total'] = count
        self._do_commit()

        for table in remove_order:
            entry = removal_traits[table]
            self.logger.info(
                "Removing %d %s rows." % (entry['total'], table))
            loop = DeletionLoopRunner(
                entry, self.txn, self.logger, store,
                dry_run=self.options.dry_run)
            DBLoopTuner(loop, self.options.loop_time, log=self.logger).run()
            self._commit_count += loop.getTotalCommits()

        self.logger.info("Done with %d commits." % self._commit_count)
        self.logger.info("Statistics:")
        for table in remove_order:
            self.logger.info("\t%-30s: %d removed" % (
                    table, removal_traits[table]['total']))

        self.logger.info("Checks:")
        checker.postCheck()

        if self.options.dry_run:
            self.txn.abort()

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
