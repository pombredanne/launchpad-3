# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['RemoveObsoleteTranslations']

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, AUTH_STORE, MASTER_FLAVOR)

import time

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.utilities.looptuner import LoopTuner

# Define SQL queries here to avoid cluttering up the code.

# POTemplate
CollectObsoletePOTemplatesSQL = """
    DROP TABLE IF EXISTS obsolete_potemplate;
    CREATE TEMP TABLE obsolete_potemplate
    AS SELECT potemplate.id AS id
    FROM potemplate
        JOIN distroseries ON potemplate.distroseries = distroseries.id
    WHERE distroseries.distribution = 1
          AND distroseries.releasestatus = 6;
    CREATE UNIQUE INDEX obsolete_potemplate_idx ON obsolete_potemplate (id);
    ANALYZE obsolete_potemplate"""
DeleteObsoletePOTemplatesSQL = """
    DELETE FROM potemplate
    WHERE id IN (
        SELECT id
        FROM obsolete_potemplate
        LIMIT %d OFFSET %d
        )"""

# POFile
CollectObsoletePOFilesSQL = """
    DROP TABLE IF EXISTS obsolete_pofile;
    CREATE TEMP TABLE obsolete_pofile
    AS SELECT pofile.id AS id
    FROM pofile
        JOIN obsolete_potemplate ON pofile.potemplate = obsolete_potemplate.id;
    CREATE UNIQUE INDEX obsolete_pofile_idx ON obsolete_pofile (id);
    ANALYZE obsolete_pofile"""
DeleteObsoletePOFilesSQL = """
    DELETE FROM pofile
    WHERE id IN (
        SELECT id
        FROM obsolete_pofile
        LIMIT %d OFFSET %d
        )"""

# TranslationMessage
CollectObsoleteTranslationMessagesSQL = """
    DROP TABLE IF EXISTS obsolete_translationmessage;
    CREATE TEMP TABLE obsolete_translationmessage
    AS SELECT translationmessage.id AS id
    FROM translationmessage
        JOIN obsolete_pofile ON translationmessage.pofile = obsolete_pofile.id;
    CREATE UNIQUE INDEX obsolete_translationmessage_idx ON obsolete_translationmessage (id);
    ANALYZE obsolete_translationmessage"""
DeleteObsoleteTranslationMessagesSQL = """
    DELETE FROM translationmessage
    WHERE id IN (
        SELECT id
        FROM obsolete_translationmessage
        LIMIT %d OFFSET %d
        )"""

# TranslationTemplateItems
CollectObsoleteTranslationTemplateItemsSQL = """
    DROP TABLE IF EXISTS obsolete_tti;
    CREATE TEMP TABLE obsolete_tti
    AS SELECT TranslationTemplateItem.id AS id
    FROM TranslationTemplateItem
        WHERE potemplate IN (
          SELECT id FROM obsolete_potemplate);
    CREATE UNIQUE INDEX obsolete_tti_idx ON obsolete_tti (id);
    ANALYZE obsolete_tti"""
DeleteObsoleteTranslationTemplateItemsSQL = """
    DELETE FROM translationtemplateitem
    WHERE id IN (
        SELECT id
        FROM obsolete_tti
        LIMIT %d OFFSET %d
        )"""

# POTMsgSet
CollectObsoletePOTMsgSetsSQL = """
    DROP TABLE IF EXISTS obsolete_potmsgset;
    CREATE TEMP TABLE obsolete_potmsgset
    AS SELECT POTMsgSet.id AS id
    FROM POTMsgSet
        WHERE potemplate IN (
          SELECT id FROM obsolete_potemplate);
    CREATE UNIQUE INDEX obsolete_potmsgset_idx ON obsolete_potmsgset (id);
    ANALYZE obsolete_potmsgset"""
DeleteObsoletePOTMsgSetsSQL = """
    DELETE FROM potmsgset
    WHERE id IN (
        SELECT id
        FROM obsolete_potmsgset
        LIMIT %d OFFSET %d
        )"""

# POFileTranslator
CollectObsoletePOFileTranslatorsSQL = """
    DROP TABLE IF EXISTS obsolete_pofiletranslator;
    CREATE TEMP TABLE obsolete_pofiletranslator
    AS SELECT POFileTranslator.id AS id
    FROM POFileTranslator
        WHERE pofile IN (
          SELECT id FROM obsolete_pofile);
    CREATE UNIQUE INDEX obsolete_pofiletranslator_idx ON obsolete_pofiletranslator (id);
    ANALYZE obsolete_pofiletranslator"""
DeleteObsoletePOFileTranslatorsSQL = """
    DELETE FROM pofiletranslator
    WHERE id IN (
        SELECT id
        FROM obsolete_pofiletranslator
        LIMIT %d OFFSET %d
        )"""

collect_order = [
    'POTemplate',
    'POFile',
    'POFileTranslator',
    'POTMsgSet',
    'TranslationTemplateItem',
    'TranslationMessage',
    ]

remove_order = [
    'POFileTranslator',
    'TranslationMessage',
    'TranslationTemplateItem',
    'POTMsgSet',
    'POFile',
    'POTemplate',
    ]

# Query to count all rows in a table
CountRowsSQL = """
    SELECT count(*) FROM %s"""


RemovalTypes = {
    'TranslationMessage' :
        { 'table' : 'TranslationMessage',
          'temporary_table' : 'obsolete_translationmessage',
          'removal_sql' : DeleteObsoleteTranslationMessagesSQL,
          'collection_sql' : CollectObsoleteTranslationMessagesSQL,
          },
    'TranslationTemplateItem' :
        { 'table' : 'TranslationTemplateItem',
          'temporary_table' : 'obsolete_tti',
          'removal_sql' : DeleteObsoleteTranslationTemplateItemsSQL,
          'collection_sql' : CollectObsoleteTranslationTemplateItemsSQL,
          },
    'POTMsgSet' :
        { 'table' : 'POTMsgSet',
          'temporary_table' : 'obsolete_potmsgset',
          'removal_sql' : DeleteObsoletePOTMsgSetsSQL,
          'collection_sql' : CollectObsoletePOTMsgSetsSQL,
          },
    'POFileTranslator' :
        { 'table' : 'POFileTranslator',
          'temporary_table' : 'obsolete_pofiletranslator',
          'removal_sql' : DeleteObsoletePOFileTranslatorsSQL,
          'collection_sql' : CollectObsoletePOFileTranslatorsSQL,
          },
    'POFile' :
        { 'table' : 'POFile',
          'temporary_table' : 'obsolete_pofile',
          'removal_sql' : DeleteObsoletePOFilesSQL,
          'collection_sql' : CollectObsoletePOFilesSQL,
          },
    'POTemplate' :
        { 'table' : 'POTemplate',
          'temporary_table' : 'obsolete_potemplate',
          'removal_sql' : DeleteObsoletePOTemplatesSQL,
          'collection_sql' : CollectObsoletePOTemplatesSQL,
          },
    }

def commit_transaction(transaction, logger, throttle=0.0, dry_run=False):
    """Commit ongoing transaction, start a new one.

    Pauses process execution to give the database slave a chance
    to keep up."""
    if transaction is None:
        return

    if not dry_run:
        transaction.commit()
        transaction.begin()

    if throttle:
        time.sleep(float(throttle))


class DeletionLoopRunner(object):
    implements(ITunableLoop)

    def __init__(self, type, transaction, logger, store, size,
                 throttle=0.0, dry_run=False):
        """Initialize the loop."""
        self.type = None
        entry = RemovalTypes[type]
        self.table = type
        self.removal_sql = entry['removal_sql']
        self.obsolete_table = entry['temporary_table']

        self._txn = transaction
        self._logger = logger
        self._store = store
        self._throttle = throttle
        self._dry_run = dry_run
        self._iteration_end = size
        self._iterations_done = 0
        self._commit_count = 0

    def isDone(self):
        """See ITunableLoop."""
        return self._iterations_done >= self._iteration_end

    def __call__(self, chunk_size):
        """See ITunableLoop."""
        query = self.removal_sql % (chunk_size, self._iterations_done)
        result = self._store.execute(query)
        self._logger.debug(
            " * Removed another %d %ss (%d of %d)." % (
                result.row_count(),
                self.table,
                self._iterations_done + result.row_count(),
                self._iteration_end))
        self._iterations_done += result.row_count()
        commit_transaction(self._txn, self._logger,dry_run=self._dry_run)
        self._commit_count += 1

        #result = self._store.execute("SELECT * FROM %s WHERE "
        #                             "  id IN (SELECT id FROM %s)" % (self.table, self.obsolete_table))
        #remaining = result.row_count()
        #if remaining:
        #    self._logger.info(
        #        "Still %d remaining %ss" % (remaining, self.table))

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
        if self.options.dry_run:
            self.logger.info("Dry run.  Not making any changes.")

        self.logger.debug(
            "Removing translations of obsolete Ubuntu versions")

        self._commit_count = 0

        # Working on the writable master store
        store = getUtility(IStoreSelector).get(AUTH_STORE, MASTER_FLAVOR)
        self._store = store

        for table in collect_order:
            collect = store.execute(RemovalTypes[table]['collection_sql'])
            count = self._count_rows(RemovalTypes[table]['temporary_table'])
            RemovalTypes[table]['total'] = count
        self._do_commit()

        for table in remove_order:
            entry = RemovalTypes[table]
            self.logger.info(
                "Removing %d %s rows." % (entry['total'], table))
            loop = DeletionLoopRunner(
                table, self.txn, self.logger, store, entry['total'],
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
                    table, RemovalTypes[table]['total']))

    def _count_rows(self, tablename):
        """Helper to count all rows in a table."""
        result = self._store.execute(
            CountRowsSQL % tablename).get_one()
        return result[0]

    def _do_commit(self):
        """Commit ongoing transaction, start a new one.

        Pauses process execution to give the database slave a chance
        to keep up."""
        commit_transaction(self.txn, self.logger,
                           throttle=float(self.options.throttle),
                           dry_run=self.options.dry_run)
        self._commit_count += 1
