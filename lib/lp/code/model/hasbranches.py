# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Mixin classes to implement methods for IHas<code related bits>."""

__metaclass__ = type
__all__ = [
    'HasBranchesMixin',
    'HasMergeProposalsMixin',
    ]


from lp.code.enums import BranchMergeProposalStatus
from lp.code.interfaces.branch import DEFAULT_BRANCH_STATUS_IN_LISTING
from lp.code.interfaces.branchcollection import IBranchCollection


class HasBranchesMixin:
    """A mixin implementation for `IHasBranches`."""

    def getBranches(self, status=None, visible_by_user=None):
        """See `IHasBranches`."""
        if status is None:
            status = DEFAULT_BRANCH_STATUS_IN_LISTING

        collection = IBranchCollection(self).visibleByUser(visible_by_user)
        collection = collection.withLifecycleStatus(*status)
        return collection.getBranches()


class HasMergeProposalsMixin:
    """A mixin implementation class for `IHasMergeProposals`."""

    def getMergeProposals(self, status=None, visible_by_user=None):
        """See `IHasMergeProposals`."""
        if not status:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS)

        collection = IBranchCollection(self).visibleByUser(visible_by_user)
        return collection.getMergeProposals(status)
