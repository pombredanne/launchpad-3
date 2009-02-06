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
# Query to collect all obsolete potemplates into a table
CollectObsoletePOTemplatesSQL = """
    DROP TABLE IF EXISTS obsolete_pots;
    CREATE TEMP TABLE obsolete_pots
    AS SELECT potemplate.id AS id
    FROM potemplate
        JOIN distroseries ON potemplate.distroseries = distroseries.id
    WHERE distroseries.distribution = 1
          AND distroseries.releasestatus = 6;
    CREATE UNIQUE INDEX obsolete_pots_idx ON obsolete_pots (id);
    ANALYZE obsolete_pots"""

# Query to collect all obsolete pofiles into a table
CollectObsoletePOFilesSQL = """
    DROP TABLE IF EXISTS obsolete_pofiles;
    CREATE TEMP TABLE obsolete_pofiles
    AS SELECT pofile.id AS id
    FROM pofile
        JOIN obsolete_pots ON pofile.potemplate = obsolete_pots.id;
    CREATE UNIQUE INDEX obsolete_pofiles_idx ON obsolete_pofiles (id);
    ANALYZE obsolete_pofiles"""

# Query to collect all obsolete translationmessages into a table
CollectObsoleteTranslationmessagesSQL = """
    DROP TABLE IF EXISTS obsolete_tms;
    CREATE TEMP TABLE obsolete_tms
    AS SELECT translationmessage.id AS id
    FROM translationmessage
        JOIN obsolete_pofiles ON translationmessage.pofile = obsolete_pofiles.id;
    CREATE UNIQUE INDEX obsolete_tms_idx ON obsolete_tms (id);
    ANALYZE obsolete_tms"""

# Query to count all rows in a table
CountRowsSQL = """
    SELECT count(*) FROM %s"""

# Query Delete obsolete pofiletranslators
DeleteObsoletePofiletranslatorsSQL = """
    DELETE FROM pofiletranslator
    WHERE pofile IN ( 
        SELECT id
        FROM obsolete_pofiles
        )"""

# Query Delete obsolete translationtemplateitems
DeleteObsoleteTranslationTemplateItemsSQL = """
    DELETE FROM translationtemplateitem
    WHERE potemplate IN ( 
        SELECT id
        FROM obsolete_pots
        )"""

# Query delete obsolete translation messages in batches of batch_size
DeleteObsoleteTranslationmessagesSQL = """
    DELETE FROM translationmessage
    WHERE id IN ( 
        SELECT id
        FROM obsolete_tms
        LIMIT %d OFFSET %d
        )"""

# Query delete obsolete pofiles
DeleteObsoletePofilesSQL = """
    DELETE FROM pofile
    WHERE id IN (
        SELECT id
        FROM obsolete_pofiles
        )"""

# Query delete obsolete potmsgsets
DeleteObsoletePOTMsgSetSQL = """
    DELETE FROM potmsgset
    WHERE potemplate IN (
        SELECT id
        FROM obsolete_pots
        )"""

# Query delete obsolete potemplates
DeleteObsoletePOTemplatesSQL = """
    DELETE FROM potemplate
    WHERE id IN (
        SELECT id
        FROM obsolete_pots
        )"""


def commit_transaction(transaction, logger, throttle=0.0, dry_run=False):
    """Commit ongoing transaction, start a new one.

    Pauses process execution to give the database slave a chance
    to keep up."""
    logger.debug("Commit point.")
    if transaction is None:
        return

    if not dry_run:
        transaction.commit()
        transaction.begin()

    time.sleep(float(throttle))


class DeletionLoopRunner(object):
    implements(ITunableLoop)

    def __init__(self, transaction, logger, store, size,
                 throttle=0.0, dry_run=False):
        """Initialize the loop."""
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
        query = DeleteObsoleteTranslationmessagesSQL % (chunk_size,
                                                        self._iterations_done)
        result = self._store.execute(query)
        self._logger.info(
            " * Removed another %d TranslationMessages (%d of %d)." % (
                result.row_count(),
                self._iterations_done + result.row_count(), 
                self._iteration_end))
        self._iterations_done += chunk_size
        commit_transaction(self._txn, self._logger, throttle=self._throttle,
                           dry_run=self._dry_run)
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
        if self.options.dry_run:
            self.logger.info("Dry run.  Not making any changes.")

        self.logger.debug(
            "Removing translations of obsolete Ubuntu versions")

        self._commit_count = 0

        # Working on the writable master store
        store = getUtility(IStoreSelector).get(AUTH_STORE, MASTER_FLAVOR)
        self._store = store

        # Create temporary tables
        store.execute(CollectObsoletePOTemplatesSQL)
        store.execute(CollectObsoletePOFilesSQL)
        store.execute(CollectObsoleteTranslationmessagesSQL)
        self._do_commit()

        num_tms = self._count_rows("obsolete_tms")
        self.logger.info(
            "Removing %d TranslationMessage rows." % num_tms)
        # Delete these first because they reference Translationmessage
        # and POFiles
        num_pofiletranslators = store.execute(
            DeleteObsoletePofiletranslatorsSQL).row_count()
        self._do_commit()

        # Delete the translation messages in batches because the deletion
        # is a long-running operation.
        loop = DeletionLoopRunner(self.txn, self.logger, store, num_tms,
                                  throttle=float(self.options.throttle),
                                  dry_run=self.options.dry_run)
        LoopTuner(loop, self.options.loop_time).run()
        self._commit_count += loop.getTotalCommits()

        # Delete these now because they reference POTemplates and POTMsgSets
        num_templateitems = store.execute(
            DeleteObsoleteTranslationTemplateItemsSQL).row_count()
        self.logger.info(
            "Removed %d TranslationTemplateItem rows." % num_templateitems)
        self._do_commit()

        # XXX Danilo: we have to pause here for a bit to allow the transaction
        # to catch up; if we don't do that, POTMsgSet removal might still fail.

        # Delete the remaining data
        num_potmsgsets = store.execute(DeleteObsoletePOTMsgSetSQL).row_count()
        self.logger.info(
            "Removed %d POTMsgSet rows." % num_potmsgsets)
        self._do_commit()

        num_pofiles = store.execute(DeleteObsoletePofilesSQL).row_count()
        self.logger.info(
            "Removed %d POFile rows." % num_pofiles)
        self._do_commit()

        num_pots = store.execute(DeleteObsoletePOTemplatesSQL).row_count()
        self.logger.info(
            "Removed %d POTemplate rows." % num_pots)
        self._do_commit()

        if self.options.dry_run:
            self.txn.abort()

        self.logger.info("Done.")
        self.logger.info("Deletion statistics:")
        self.logger.info("Pofiletranslators:   %d" % num_pofiletranslators)
        self.logger.info("Translationmessages: %d" % num_tms)
        self.logger.info("Trans.TemplateItems: %d" % num_templateitems)
        self.logger.info("POFiles:             %d" % num_pofiles)
        self.logger.info("POTMsgSets:          %d" % num_potmsgsets)
        self.logger.info("POTemplates:         %d" % num_pots)
        self.logger.info("Commit points:       %d" % self._commit_count)

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
