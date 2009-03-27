# Copyright 2009 Canonical Ltd.  All rights reserved.

"""The way the branch scanner handles merges."""

__metaclass__ = type
__all__ = [
    'BranchMergeDetectionHandler',
    ]

import logging

from canonical.launchpad.interfaces.branch import BranchLifecycleStatus


class BranchMergeDetectionHandler:
    """Handle merge detection events."""

    def __init__(self, logger=None):
        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

    def _markSourceBranchMerged(self, source):
        # If the source branch is a series branch, then don't change the
        # lifecycle status of it at all.
        if source.associatedProductSeries().count() > 0:
            return
        # In other cases, we now want to update the lifecycle status of the
        # source branch to merged.
        self.logger.info("%s now Merged.", source.bzr_identity)
        source.lifecycle_status = BranchLifecycleStatus.MERGED

    def mergeProposalMerge(self, proposal):
        """Handle a detected merge of a proposal."""
        # XXX: JonathanLange 2009-03-09: This should be combined with
        # mergeOfTwoBranches -- the events are the same and should be handled
        # similarly.
        self.logger.info(
            'Merge detected: %s => %s',
            proposal.source_branch.bzr_identity,
            proposal.target_branch.bzr_identity)
        proposal.markAsMerged()
        # Don't update the source branch unless the target branch is a series
        # branch.
        if proposal.target_branch.associatedProductSeries().count() == 0:
            return
        self._markSourceBranchMerged(proposal.source_branch)

    def mergeOfTwoBranches(self, source, target, proposal=None):
        """Handle the merge of source into target."""
        # If the target branch is not the development focus, then don't update
        # the status of the source branch.
        self.logger.info(
            'Merge detected: %s => %s',
            source.bzr_identity, target.bzr_identity)
        dev_focus = target.product.development_focus
        if target != dev_focus.user_branch:
            return
        if proposal is not None:
            proposal.markAsMerged()
        self._markSourceBranchMerged(source)
