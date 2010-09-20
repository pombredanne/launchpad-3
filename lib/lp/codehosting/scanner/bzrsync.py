#!/usr/bin/python
#
# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Import version control metadata from a Bazaar branch into the database."""

__metaclass__ = type

__all__ = [
    "BzrSync",
    'schedule_diff_updates',
    'schedule_translation_templates_build',
    'schedule_translation_upload',
    ]

import logging

import pytz
import transaction
from zope.component import getUtility
from zope.event import notify

from canonical.config import config

from lp.code.interfaces.branchjob import IRosettaUploadJobSource
from lp.code.interfaces.revision import IRevisionSet
from lp.codehosting import iter_list_chunks
from lp.codehosting.scanner import events
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource,
    )


UTC = pytz.timezone('UTC')


class BzrSync:
    """Import version control metadata from a Bazaar branch into the database.
    """

    def __init__(self, branch, logger=None):
        self.db_branch = branch
        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

    def syncBranchAndClose(self, bzr_branch=None):
        """Synchronize the database with a Bazaar branch, handling locking.
        """
        if bzr_branch is None:
            bzr_branch = self.db_branch.getBzrBranch()
        bzr_branch.lock_read()
        try:
            self.syncBranch(bzr_branch)
        finally:
            bzr_branch.unlock()

    def syncBranch(self, bzr_branch):
        """Synchronize the database view of a branch with Bazaar data.

        `bzr_branch` must be read locked.

        Several tables must be updated:

        * Revision: there must be one Revision row for each revision in the
          branch ancestry. If the row for a revision that has just been added
          to the branch is already present, it must be checked for consistency.

        * BranchRevision: there must be one BrancheRevision row for each
          revision in the branch ancestry. If history revisions became merged
          revisions, the corresponding rows must be changed.

        * Branch: the branch-scanner status information must be updated when
          the sync is complete.
        """
        self.logger.info("Scanning branch: %s", self.db_branch.unique_name)
        self.logger.info("    from %s", bzr_branch.base)
        # Get the history and ancestry from the branch first, to fail early
        # if something is wrong with the branch.
        bzr_ancestry, bzr_history = self.retrieveBranchDetails(bzr_branch)
        # The BranchRevision, Revision and RevisionParent tables are only
        # written to by the branch-scanner, so they are not subject to
        # write-lock contention. Update them all in a single transaction to
        # improve the performance and allow garbage collection in the future.
        db_ancestry, db_history = self.retrieveDatabaseAncestry()

        (added_ancestry, branchrevisions_to_delete,
            revids_to_insert) = self.planDatabaseChanges(
            bzr_branch, bzr_ancestry, bzr_history, db_ancestry, db_history)
        added_ancestry.difference_update(
            getUtility(IRevisionSet).onlyPresent(added_ancestry))
        self.logger.info("Adding %s new revisions.", len(added_ancestry))
        for revids in iter_list_chunks(list(added_ancestry), 1000):
            revisions = self.getBazaarRevisions(bzr_branch, revids)
            for revision in revisions:
                # This would probably go much faster if we found some way to
                # bulk-load multiple revisions at once, but as this is only
                # executed for revisions new to Launchpad, it doesn't seem
                # worth it at this stage.
                self.syncOneRevision(
                    bzr_branch, revision, revids_to_insert)
        self.deleteBranchRevisions(branchrevisions_to_delete)
        self.insertBranchRevisions(bzr_branch, revids_to_insert)
        transaction.commit()
        # Synchronize the RevisionCache for this branch.
        getUtility(IRevisionSet).updateRevisionCacheForBranch(self.db_branch)
        transaction.commit()

        # Notify any listeners that the tip of the branch has changed, but
        # before we've actually updated the database branch.
        initial_scan = (len(db_history) == 0)
        notify(events.TipChanged(self.db_branch, bzr_branch, initial_scan))

        # The Branch table is modified by other systems, including the web UI,
        # so we need to update it in a short transaction to avoid causing
        # timeouts in the webapp. This opens a small race window where the
        # revision data is updated in the database, but the Branch table has
        # not been updated. Since this has no ill-effect, and can only err on
        # the pessimistic side (tell the user the data has not yet been
        # updated although it has), the race is acceptable.
        self.updateBranchStatus(bzr_history)
        notify(
            events.ScanCompleted(
                self.db_branch, bzr_branch, bzr_ancestry, self.logger))
        transaction.commit()

    def retrieveDatabaseAncestry(self):
        """Efficiently retrieve ancestry from the database."""
        self.logger.info("Retrieving ancestry from database.")
        db_ancestry, db_history = self.db_branch.getScannerData()
        return db_ancestry, db_history

    def retrieveBranchDetails(self, bzr_branch):
        """Retrieve ancestry from the the bzr branch on disk."""
        self.logger.info("Retrieving ancestry from bzrlib.")
        last_revision = bzr_branch.last_revision()
        # Make bzr_ancestry a set for consistency with db_ancestry.
        bzr_ancestry_ordered = (
            bzr_branch.repository.get_ancestry(last_revision))
        first_ancestor = bzr_ancestry_ordered.pop(0)
        assert first_ancestor is None, 'history horizons are not supported'
        bzr_ancestry = set(bzr_ancestry_ordered)
        bzr_history = bzr_branch.revision_history()
        return bzr_ancestry, bzr_history

    def planDatabaseChanges(self, bzr_branch, bzr_ancestry, bzr_history,
                            db_ancestry, db_history):
        """Plan database changes to synchronize with bzrlib data.

        Use the data retrieved by `retrieveDatabaseAncestry` and
        `retrieveBranchDetails` to plan the changes to apply to the database.
        """
        self.logger.info("Planning changes.")
        # Find the length of the common history.
        common_len = min(len(bzr_history), len(db_history))
        while common_len > 0:
            # The outer conditional improves efficiency. Without it, the
            # algorithm is O(history-size * change-size), which can be
            # excessive if a long branch is replaced by another long branch
            # with a distant (or no) common mainline parent. The inner
            # conditional is needed for correctness with branches where the
            # history does not follow the line of leftmost parents.
            if db_history[common_len - 1] == bzr_history[common_len - 1]:
                if db_history[:common_len] == bzr_history[:common_len]:
                    break
            common_len -= 1

        # Revisions added to the branch's ancestry.
        added_ancestry = bzr_ancestry.difference(db_ancestry)

        # Revision added or removed from the branch's history. These lists may
        # include revisions whose history position has merely changed.
        removed_history = db_history[common_len:]
        added_history = bzr_history[common_len:]

        notify(
            events.RevisionsRemoved(
                self.db_branch, bzr_branch, removed_history))

        # Merged (non-history) revisions in the database and the bzr branch.
        old_merged = db_ancestry.difference(db_history)
        new_merged = bzr_ancestry.difference(bzr_history)

        # Revisions added or removed from the set of merged revisions.
        removed_merged = old_merged.difference(new_merged)
        added_merged = new_merged.difference(old_merged)

        # We must delete BranchRevision rows for all revisions which where
        # removed from the ancestry or whose sequence value has changed.
        branchrevisions_to_delete = list(
            removed_merged.union(removed_history))

        # We must insert BranchRevision rows for all revisions which were
        # added to the ancestry or whose sequence value has changed.
        revids_to_insert = dict(
            self.getRevisions(
                bzr_history, added_merged.union(added_history)))

        return (added_ancestry, branchrevisions_to_delete,
                revids_to_insert)

    def getBazaarRevisions(self, bzr_branch, revisions):
        """Like ``get_revisions(revisions)`` but filter out ghosts first.

        :param revisions: the set of Bazaar revision IDs to return bzrlib
            Revision objects for.
        """
        revisions = bzr_branch.repository.get_parent_map(revisions)
        return bzr_branch.repository.get_revisions(revisions.keys())

    def syncOneRevision(self, bzr_branch, bzr_revision, revids_to_insert):
        """Import the revision with the given revision_id.

        :param bzr_branch: The Bazaar branch that's being scanned.
        :param bzr_revision: the revision to import
        :type bzr_revision: bzrlib.revision.Revision
        :param revids_to_insert: a dict of revision ids to integer
            revno. Non-mainline revisions will be mapped to None.
        """
        revision_id = bzr_revision.revision_id
        revision_set = getUtility(IRevisionSet)
        # Revision not yet in the database. Load it.
        self.logger.debug("Inserting revision: %s", revision_id)
        db_revision = revision_set.newFromBazaarRevision(bzr_revision)
        notify(
            events.NewRevision(
                self.db_branch, bzr_branch, db_revision, bzr_revision,
                revids_to_insert[revision_id]))

    def getRevisions(self, bzr_history, revision_subset):
        """Iterate over '(revid, revno)' pairs in a branch's ancestry.

        Generate a sequence of (revision-id, sequence) pairs to be inserted
        into the branchrevision table.
        """
        for (index, revision_id) in enumerate(bzr_history):
            if revision_id in revision_subset:
                # sequence numbers start from 1
                yield revision_id, index + 1
        for revision_id in revision_subset.difference(set(bzr_history)):
            yield revision_id, None

    def deleteBranchRevisions(self, revision_ids_to_delete):
        """Delete a batch of BranchRevision rows."""
        self.logger.info("Deleting %d branchrevision records.",
            len(revision_ids_to_delete))
        # Use a config value to work out how many to delete at a time.
        # Deleting more than one at a time is significantly more efficient
        # than doing one at a time, but the actual optimal count is a bit up
        # in the air.
        batch_size = config.branchscanner.branch_revision_delete_count
        while revision_ids_to_delete:
            batch = revision_ids_to_delete[:batch_size]
            revision_ids_to_delete[:batch_size] = []
            self.db_branch.removeBranchRevisions(batch)

    def insertBranchRevisions(self, bzr_branch, revids_to_insert):
        """Insert a batch of BranchRevision rows."""
        self.logger.info("Inserting %d branchrevision records.",
            len(revids_to_insert))
        revid_seq_pairs = revids_to_insert.items()
        for revid_seq_pair_chunk in iter_list_chunks(revid_seq_pairs, 1000):
            self.db_branch.createBranchRevisionFromIDs(revid_seq_pair_chunk)

    def updateBranchStatus(self, bzr_history):
        """Update the branch-scanner status in the database Branch table."""
        # Record that the branch has been updated.
        revision_count = len(bzr_history)
        if revision_count > 0:
            last_revision = bzr_history[-1]
            revision = getUtility(IRevisionSet).getByRevisionId(last_revision)
        else:
            revision = None
        self.logger.info(
            "Updating branch scanner status: %s revs", revision_count)
        self.db_branch.updateScannedDetails(revision, revision_count)


def schedule_translation_upload(tip_changed):
    getUtility(IRosettaUploadJobSource).create(
        tip_changed.db_branch, tip_changed.old_tip_revision_id)


def schedule_translation_templates_build(tip_changed):
    utility = getUtility(ITranslationTemplatesBuildJobSource)
    utility.scheduleTranslationTemplatesBuild(tip_changed.db_branch)


def schedule_diff_updates(tip_changed):
    tip_changed.db_branch.scheduleDiffUpdates()


def update_recipes(tip_changed):
    for recipe in tip_changed.db_branch.getRecipes():
        recipe.is_stale = True
