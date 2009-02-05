# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['RemoveObsoleteTranslations']

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, AUTH_STORE, MASTER_FLAVOR)

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.utilities import LoopTuner

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

class DeletionLoopRunner(object):
    implements(ITunableLoop)

    def __init__(self, store, size, commitmethod):
        """Initialize the loop."""
        self._store = store
        self._do_commit = commitmethod
        self._iteration_end = size
        self._iterations_done = 0

    def isDone(self):
        """See ITunableLoop."""
        return self._iterations_done >= self._iteration_end

    def __call__(self, chunk_size):
        """See ITunableLoop."""
        self._store.execute(
            DeleteObsoleteTranslationmessagesSQL % (chunk_size,
                                                    self._iterations_done))
        self._iterations_done += chunk_size
        self._do_commit()


class RemoveObsoleteTranslations(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option(
            '-d', '--dry-run', action="store_true", dest='dry_run',
            default=False, help="Don't really make any database changes.")

        self.parser.add_option(
            '-l', '--loop-timing', dest='loop_time',
            default=5, help="Time in seconds for the loop to run and to sleep.")

    def main(self):
        if self.options.dry_run:
            self.logger.info("Dry run.  Not making any changes.")

        self.logger.debug(
            "Removing translations of obsolete Ubuntu versions")

        self._commit_count = 0

        # Working on the writable master store
        store = getUtility(IStoreSelector).get(AUTH_STORE, MASTER_FLAVOR)

        # Create temporary tables
        store.execute(CollectObsoletePOTemplatesSQL)
        store.execute(CollectObsoletePOFilesSQL)
        store.execute(CollectObsoleteTranslationmessagesSQL)
        self._do_commit()
        num_pots = self._count_rows("obsolete_pots")
        num_pofiles = self._count_rows("obsolete_pofiles")
        num_tms = self._count_rows("obsolete_tms")

        # Delete these first because they reference Translationmessage
        # and POFiles
        restult = store.execute(DeleteObsoletePofiletranslatorsSQL)
        # XXX Not sure how to get a count of deleted rows. This assumes
        # that the statement just returns it.
        num_pofiletranslators = result.get_one()
        self._do_commit()

        # Delete the translation messages in batches because the deletion
        # is a long-running operation.
        LoopTuner(DeletionLoopRunner(store, num_tms, self._do_commit),
                  self.options.loop_time).run()

        # Delete the remaining data
        restult = store.execute(DeleteObsoletePOTMsgSetSQL)
        # XXX Not sure how to get a count of deleted rows. This assumes
        # that the statement just returns it.
        num_potmsgsets = result.get_one()
        self._do_commit()
        store.execute(DeleteObsoletePofilesSQL)
        store.execute(DeleteObsoletePOTemplatesSQL)
        self._do_commit()

        self.logger.info("Done.")
        self.logger.info("Deletion statistics:")
        self.logger.info("Pofiletranslators:   %d" % num_pofiletranslators)
        self.logger.info("Translationmessages: %d" % num_tms)
        self.logger.info("POFiles:             %d" % num_pofiles)
        self.logger.info("POTMsgSets:          %d" % num_potmsgsets)
        self.logger.info("POTemplates:         %d" % num_pots)
        self.logger.info("Commit points:       %d" % self._commit_count)

    def _count_rows(self, tablename):
        """Helper to count all rows in a table."""
        result = self._store.execute(
            CountRowsSQL % tablename).one()
        return result[0]

    def _do_commit(self):
        """Commit ongoing transaction, start a new one.

        Pauses process execution to give the database slave a chance
        to keep up."""
        self.logger.debug("Commit point.")
        self._commit_count += 1

        if self.txn is None:
            return

        if self.options.dry_run:
            self.txn.abort()
        else:
            self.txn.commit()

        time.sleep(self.options.loop_time)
        self.txn.begin()

