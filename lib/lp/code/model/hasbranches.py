# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Mixin classes to implement methods for IHas<code related bits>."""

__metaclass__ = type
__all__ = [
    'HasBranchesMixin',
    'HasMergeProposalsMixin',
    ]


from lp.code.enums import BranchMergeProposalStatus
from lp.code.interfaces.branch import DEFAULT_BRANCH_STATUS_IN_LISTING


class NeedsBranchCollection:
    """Base class for the Has<bits>Mixin classes to get the collection."""

    def getBranchCollection(self):
        """Return the appropriate branch collection."""
        raise NotImplementedError(NeedsBranchCollection.getBranchCollection)


class HasBranchesMixin(NeedsBranchCollection):
    """Implementation for getBranches as defined by IHasBranches."""

    def getBranches(self, status=None, visible_by_user=None):
        """See `IHasBranches`."""
        if status is None:
            status = DEFAULT_BRANCH_STATUS_IN_LISTING

        collection = self.getBranchCollection().visibleByUser(visible_by_user)
        collection = collection.withLifecycleStatus(*status)
        return collection.getBranches()


class HasMergeProposalsMixin(NeedsBranchCollection):
    """Implementation for getMergeProposals as defined by IHasMergeProposals.
    """

    def getMergeProposals(self, status=None, visible_by_user=None):
        """See `IHasMergeProposals`."""
        if not status:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS)

        collection = self.getBranchCollection().visibleByUser(visible_by_user)
        return collection.getMergeProposals(status)
