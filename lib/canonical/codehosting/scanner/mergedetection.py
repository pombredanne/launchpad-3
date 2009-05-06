# Copyright 2009 Canonical Ltd.  All rights reserved.

"""The way the branch scanner handles merges."""

__metaclass__ = type
__all__ = [
    'auto_merge_branches',
    'auto_merge_proposals',
    ]

from bzrlib.revision import NULL_REVISION

from zope.component import adapter, getUtility

from canonical.codehosting.scanner import events

from lp.code.interfaces.branch import BranchLifecycleStatus
from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES)


def is_series_branch(branch):
    """Is 'branch' associated with a series?"""
    # XXX: JonathanLange 2009-05-07 spec=package-branches: This assumes that
    # we only care about whether a branch is a product series. What about poor
    # old distroseries?
    return branch.associatedProductSeries().count() > 0


def is_development_focus(branch):
    """Is 'branch' the development focus?"""
    # XXX: JonathanLange 2009-05-07 spec=package-branches: What if the branch
    # is the development focus of a source package?
    dev_focus = branch.product.development_focus
    return branch == dev_focus.branch


def mark_branch_merged(logger, branch):
    """Mark 'branch' as merged."""
    # If the branch is a series branch, then don't change the
    # lifecycle status of it at all.
    if is_series_branch(branch):
        return
    # In other cases, we now want to update the lifecycle status of the
    # source branch to merged.
    logger.info("%s now Merged.", branch.bzr_identity)
    branch.lifecycle_status = BranchLifecycleStatus.MERGED


def merge_detected(logger, source, target, proposal=None):
    """Handle the merge of source into target."""
    # If the target branch is not the development focus, then don't update
    # the status of the source branch.
    logger.info(
        'Merge detected: %s => %s',
        source.bzr_identity, target.bzr_identity)
    if proposal is None:
        # If there's no explicit merge proposal, only change the branch's
        # status when it has been merged into the development focus.
        if is_development_focus(target):
            mark_branch_merged(logger, source)
    else:
        proposal.markAsMerged()
        # If there is an explicit merge proposal, change the branch's
        # status when it's been merged into a development focus or any
        # other series branch.
        if is_series_branch(proposal.target_branch):
            mark_branch_merged(logger, proposal.source_branch)


@adapter(events.ScanCompleted)
def auto_merge_branches(scan_completed):
    """Detect branches that have been merged.

    We only check branches that have been merged into the branch that is being
    scanned as we already have the ancestry handy. It is much more work to
    determine which other branches this branch has been merged into.
    """
    db_branch = scan_completed.db_branch
    bzr_ancestry = scan_completed.bzr_ancestry
    logger = scan_completed.logger

    # XXX: JonathanLange 2009-05-05 spec=package-branches: Yet another thing
    # that assumes that product is None implies junk.
    #
    # Only do this for non-junk branches.
    if db_branch.product is None:
        return
    # Get all the active branches for the product, and if the
    # last_scanned_revision is in the ancestry, then mark it as merged.
    branches = getUtility(IAllBranches).inTarget(db_branch.target)
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
        elif branch == db_branch:
            # No point merging into ourselves.
            pass
        elif db_branch.last_scanned_id == last_scanned:
            # If the tip revisions are the same, then it is the same
            # branch, not one merged into the other.
            pass
        elif last_scanned in bzr_ancestry:
            merge_detected(logger, branch, db_branch)


@adapter(events.ScanCompleted)
def auto_merge_proposals(scan_completed):
    """Detect merged proposals."""
    db_branch = scan_completed.db_branch
    bzr_ancestry = scan_completed.bzr_ancestry
    logger = scan_completed.logger

    # Check landing candidates in non-terminal states to see if their tip
    # is in our ancestry. If it is, set the state of the proposal to
    # 'merged'.
    #
    # At this stage we are not going to worry about the revno
    # which introduced the change, that will either be set through the web
    # ui by a person, or by PQM once it is integrated.
    for proposal in db_branch.landing_candidates:
        if proposal.source_branch.last_scanned_id in bzr_ancestry:
            merge_detected(
                logger, proposal.source_branch, db_branch, proposal)

    # Now check the landing targets.
    final_states = BRANCH_MERGE_PROPOSAL_FINAL_STATES
    tip_rev_id = db_branch.last_scanned_id
    for proposal in db_branch.landing_targets:
        if proposal.queue_status not in final_states:
            # If there is a branch revision record for target branch with
            # the tip_rev_id of the source branch, then it is merged.
            branch_revision = proposal.target_branch.getBranchRevision(
                revision_id=tip_rev_id)
            if branch_revision is not None:
                merge_detected(
                    logger, db_branch, proposal.target_branch, proposal)
