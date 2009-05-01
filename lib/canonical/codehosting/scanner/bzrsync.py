#!/usr/bin/python
# Copyright 2004-2009 Canonical Ltd.  All rights reserved.

"""Import version control metadata from a Bazaar branch into the database."""

__metaclass__ = type

__all__ = [
    "BzrSync",
    ]

import logging

import pytz

# This non-standard import is necessary to hook up the event system.
import zope.component.event
from zope.component import getUtility, provideHandler
from zope.event import notify

from bzrlib.branch import BzrBranchFormat4
from bzrlib.revision import NULL_REVISION
from bzrlib.repofmt.weaverepo import (
    RepositoryFormat4, RepositoryFormat5, RepositoryFormat6)
from bzrlib import urlutils

from lazr.uri import URI

from canonical.codehosting import iter_list_chunks
from canonical.codehosting.puller.worker import BranchMirrorer, BranchPolicy
from canonical.codehosting.scanner import buglinks, events
from canonical.codehosting.scanner.email import BranchMailer
from canonical.codehosting.scanner.mergedetection import (
    BranchMergeDetectionHandler)
from canonical.config import config
from lp.code.interfaces.branch import (
    BranchFormat, BranchLifecycleStatus, ControlFormat, RepositoryFormat)
from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.interfaces.branchjob import (
    IRevisionsAddedJobSource, IRosettaUploadJobSource)
from lp.code.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES)
from lp.code.interfaces.branchrevision import IBranchRevisionSet
from lp.code.interfaces.revision import IRevisionSet

UTC = pytz.timezone('UTC')


class InvalidStackedBranchURL(Exception):
    """Raised when we try to scan a branch stacked on an invalid URL."""


class WarehouseBranchPolicy(BranchPolicy):

    def checkOneURL(self, url):
        """See `BranchOpener.checkOneURL`.

        If the URLs we are mirroring from are anything but a
        lp-mirrored:///~user/project/branch URLs, we don't want to scan them.
        Opening branches on remote systems takes too long, and we want all of
        our local access to be channelled through this transport.
        """
        uri = URI(url)
        if uri.scheme != 'lp-mirrored':
            raise InvalidStackedBranchURL(url)

    def transformFallbackLocation(self, branch, url):
        """See `BranchPolicy.transformFallbackLocation`.

        We're happy to open stacked branches in the usual manner, but want to
        go on checking the URLs of any branches we then open.
        """
        return urlutils.join(branch.base, url), True


class BzrSync:
    """Import version control metadata from a Bazaar branch into the database.
    """

    def __init__(self, trans_manager, branch, logger=None):
        self.trans_manager = trans_manager
        self.email_from = config.canonical.noreply_from_address

        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

        self.db_branch = branch
        provideHandler(buglinks.got_new_revision)
        self._branch_mailer = BranchMailer(self.trans_manager, self.db_branch)
        self._merge_handler = BranchMergeDetectionHandler(self.logger)

    def syncBranchAndClose(self, bzr_branch=None):
        """Synchronize the database with a Bazaar branch, handling locking.
        """
        if bzr_branch is None:
            bzr_branch = BranchMirrorer(WarehouseBranchPolicy()).open(
                self.db_branch.warehouse_url)
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
        self.trans_manager.begin()
        self.setFormats(bzr_branch)
        db_ancestry, db_history, db_branch_revision_map = (
            self.retrieveDatabaseAncestry())
        notify(
            events.DatabaseBranchLoaded(
                self.db_branch, bzr_branch, db_ancestry, db_history,
                db_branch_revision_map))
        initial_scan = (len(db_history) == 0)
        self._branch_mailer.initializeEmailQueue(initial_scan)

        (added_ancestry, branchrevisions_to_delete,
            branchrevisions_to_insert) = self.planDatabaseChanges(
            bzr_ancestry, bzr_history, db_ancestry, db_history,
            db_branch_revision_map)
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
                self.syncOneRevision(revision, branchrevisions_to_insert)
        self.deleteBranchRevisions(branchrevisions_to_delete)
        self.insertBranchRevisions(bzr_branch, branchrevisions_to_insert)

        # Generate emails for the revisions in the revision_history
        # for the branch.
        if self.db_branch.last_scanned_id is not None:
            # XXX: Event
            job = getUtility(IRevisionsAddedJobSource).create(
                self.db_branch, self.db_branch.last_scanned_id,
                bzr_branch.last_revision(),
                config.canonical.noreply_from_address)

        self.trans_manager.commit()

        # XXX: Event
        self._branch_mailer.sendRevisionNotificationEmails(bzr_history)
        # The Branch table is modified by other systems, including the web UI,
        # so we need to update it in a short transaction to avoid causing
        # timeouts in the webapp. This opens a small race window where the
        # revision data is updated in the database, but the Branch table has
        # not been updated. Since this has no ill-effect, and can only err on
        # the pessimistic side (tell the user the data has not yet been
        # updated although it has), the race is acceptable.
        self.trans_manager.begin()
        self.updateBranchStatus(bzr_history)
        # XXX: Event
        self.autoMergeProposals(bzr_ancestry)
        self.autoMergeBranches(bzr_ancestry)
        self.trans_manager.commit()

    def autoMergeBranches(self, bzr_ancestry):
        """Detect branches that have been merged."""
        # We only check branches that have been merged into the branch that is
        # being scanned as we already have the ancestry handy.  It is much
        # more work to determine which other branches this branch has been
        # merged into.  At this stage the merge detection only checks other
        # branches merged into the scanned one.

        # Only do this for non-junk branches.
        if self.db_branch.product is None:
            return
        # Get all the active branches for the product, and if the
        # last_scanned_revision is in the ancestry, then mark it as merged.
        branches = getUtility(IAllBranches).inProduct(self.db_branch.product)
        branches = branches.withLifecycleStatus(
            BranchLifecycleStatus.DEVELOPMENT,
            BranchLifecycleStatus.EXPERIMENTAL,
            BranchLifecycleStatus.MATURE,
            BranchLifecycleStatus.ABANDONED).getBranches()
        for branch in branches:
            last_scanned = branch.last_scanned_id
            # If the branch doesn't have any revisions, not any point setting
            # anything.
            if last_scanned is None or last_scanned == NULL_REVISION:
                # Skip this branch.
                pass
            elif branch == self.db_branch:
                # No point merging into ourselves.
                pass
            elif self.db_branch.last_scanned_id == last_scanned:
                # If the tip revisions are the same, then it is the same
                # branch, not one merged into the other.
                pass
            elif last_scanned in bzr_ancestry:
                # XXX: EVENT
                self._merge_handler.mergeOfTwoBranches(
                    branch, self.db_branch)

    def autoMergeProposals(self, bzr_ancestry):
        """Detect merged proposals."""
        # Check landing candidates in non-terminal states to see if their tip
        # is in our ancestry. If it is, set the state of the proposal to
        # 'merged'.

        # At this stage we are not going to worry about the revno
        # which introduced the change, that will either be set through the web
        # ui by a person, of by PQM once it is integrated.
        for proposal in self.db_branch.landing_candidates:
            if proposal.source_branch.last_scanned_id in bzr_ancestry:
                self._merge_handler.mergeProposalMerge(proposal)

        # Now check the landing targets.
        final_states = BRANCH_MERGE_PROPOSAL_FINAL_STATES
        tip_rev_id = self.db_branch.last_scanned_id
        for proposal in self.db_branch.landing_targets:
            if proposal.queue_status not in final_states:
                # If there is a branch revision record for target branch with
                # the tip_rev_id of the source branch, then it is merged.
                branch_revision = proposal.target_branch.getBranchRevision(
                    revision_id=tip_rev_id)
                if branch_revision is not None:
                    # XXX: EVENT
                    self._merge_handler.mergeProposalMerge(proposal)

    def retrieveDatabaseAncestry(self):
        """Efficiently retrieve ancestry from the database."""
        self.logger.info("Retrieving ancestry from database.")
        db_ancestry, db_history, db_branch_revision_map = (
            self.db_branch.getScannerData())
        return db_ancestry, db_history, db_branch_revision_map

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

    def setFormats(self, bzr_branch):
        """Record the stored formats in the database object.

        The previous value is unconditionally overwritten.

        Note that the strings associated with the formats themselves are used,
        not the strings on disk.
        """
        def match_title(enum, title, default):
            for value in enum.items:
                if value.title == title:
                    return value
            else:
                return default

        # XXX: Aaron Bentley 2008-06-13
        # Bazaar does not provide a public API for learning about format
        # markers.  Fix this in Bazaar, then here.
        control_string = bzr_branch.bzrdir._format.get_format_string()
        if bzr_branch._format.__class__ is BzrBranchFormat4:
            branch_string = BranchFormat.BZR_BRANCH_4.title
        else:
            branch_string = bzr_branch._format.get_format_string()
        repository_format = bzr_branch.repository._format
        if repository_format.__class__ is RepositoryFormat6:
            repository_string = RepositoryFormat.BZR_REPOSITORY_6.title
        elif repository_format.__class__ is RepositoryFormat5:
            repository_string = RepositoryFormat.BZR_REPOSITORY_5.title
        elif repository_format.__class__ is RepositoryFormat4:
            repository_string = RepositoryFormat.BZR_REPOSITORY_4.title
        else:
            repository_string = repository_format.get_format_string()
        self.db_branch.control_format = match_title(
            ControlFormat, control_string, ControlFormat.UNRECOGNIZED)
        self.db_branch.branch_format = match_title(
            BranchFormat, branch_string, BranchFormat.UNRECOGNIZED)
        self.db_branch.repository_format = match_title(
            RepositoryFormat, repository_string,
            RepositoryFormat.UNRECOGNIZED)

    def planDatabaseChanges(self, bzr_ancestry, bzr_history, db_ancestry,
                            db_history, db_branch_revision_map):
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

        # XXX: Event
        self._branch_mailer.generateEmailForRemovedRevisions(removed_history)

        # Merged (non-history) revisions in the database and the bzr branch.
        old_merged = db_ancestry.difference(db_history)
        new_merged = bzr_ancestry.difference(bzr_history)

        # Revisions added or removed from the set of merged revisions.
        removed_merged = old_merged.difference(new_merged)
        added_merged = new_merged.difference(old_merged)

        # We must delete BranchRevision rows for all revisions which where
        # removed from the ancestry or whose sequence value has changed.
        branchrevisions_to_delete = set(
            db_branch_revision_map[revid]
            for revid in removed_merged.union(removed_history))

        # We must insert BranchRevision rows for all revisions which were
        # added to the ancestry or whose sequence value has changed.
        branchrevisions_to_insert = dict(
            self.getRevisions(
                bzr_history, added_merged.union(added_history)))

        return (added_ancestry, branchrevisions_to_delete,
                branchrevisions_to_insert)

    def getBazaarRevisions(self, bzr_branch, revisions):
        """Like ``get_revisions(revisions)`` but filter out ghosts first.

        :param revisions: the set of Bazaar revision IDs to return bzrlib
            Revision objects for.
        """
        revisions = bzr_branch.repository.get_parent_map(revisions)
        return bzr_branch.repository.get_revisions(revisions.keys())

    def syncOneRevision(self, bzr_revision, branchrevisions_to_insert):
        """Import the revision with the given revision_id.

        :param bzr_revision: the revision to import
        :type bzr_revision: bzrlib.revision.Revision
        :param branchrevisions_to_insert: a dict of revision ids to integer
            revno.  (Non-mainline revisions will not be present).
        """
        revision_id = bzr_revision.revision_id
        revision_set = getUtility(IRevisionSet)
        # Revision not yet in the database. Load it.
        self.logger.debug("Inserting revision: %s", revision_id)
        db_revision = revision_set.newFromBazaarRevision(bzr_revision)
        notify(
            events.NewRevision(
                self.db_branch, None, db_revision, bzr_revision,
                branchrevisions_to_insert[revision_id]))

    def getRevisions(self, bzr_history, revision_subset):
        """Generate revision IDs that make up the branch's ancestry.

        Generate a sequence of (revision-id, sequence) pairs to be inserted
        into the branchrevision table.
        """
        for (index, revision_id) in enumerate(bzr_history):
            if revision_id in revision_subset:
                # sequence numbers start from 1
                yield revision_id, index + 1
        for revision_id in revision_subset.difference(set(bzr_history)):
            yield revision_id, None

    def deleteBranchRevisions(self, branchrevisions_to_delete):
        """Delete a batch of BranchRevision rows."""
        self.logger.info("Deleting %d branchrevision records.",
            len(branchrevisions_to_delete))
        branch_revision_set = getUtility(IBranchRevisionSet)
        for branchrevision in sorted(branchrevisions_to_delete):
            branch_revision_set.delete(branchrevision)

    def insertBranchRevisions(self, bzr_branch, branchrevisions_to_insert):
        """Insert a batch of BranchRevision rows."""
        self.logger.info("Inserting %d branchrevision records.",
            len(branchrevisions_to_insert))
        revision_set = getUtility(IRevisionSet)
        revid_seq_pairs = branchrevisions_to_insert.items()
        for revid_seq_pair_chunk in iter_list_chunks(revid_seq_pairs, 1000):
            self.db_branch.createBranchRevisionFromIDs(revid_seq_pair_chunk)

    def updateBranchStatus(self, bzr_history):
        """Update the branch-scanner status in the database Branch table."""
        # Record that the branch has been updated.
        if len(bzr_history) > 0:
            last_revision = bzr_history[-1]
            revision = getUtility(IRevisionSet).getByRevisionId(last_revision)
            if last_revision != self.db_branch.last_scanned_id:
                getUtility(IRosettaUploadJobSource).create(
                    self.db_branch, self.db_branch.last_scanned_id)
        else:
            revision = None

        revision_count = len(bzr_history)
        self.logger.info(
            "Updating branch scanner status: %s revs", revision_count)
        self.db_branch.updateScannedDetails(revision, revision_count)
