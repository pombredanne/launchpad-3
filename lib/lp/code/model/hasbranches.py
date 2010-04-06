# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Mixin classes to implement methods for IHas<code related bits>."""

__metaclass__ = type
__all__ = [
    'HasBranchesMixin',
    'HasMergeProposalsMixin',
    'HasRequestedReviewsMixin',
    ]

from zope.component import getUtility

from lp.code.enums import BranchMergeProposalStatus
from lp.code.interfaces.branch import DEFAULT_BRANCH_STATUS_IN_LISTING
from lp.code.interfaces.branchcollection import (
    IAllBranches, IBranchCollection)


class HasBranchesMixin:
    """A mixin implementation for `IHasBranches`."""

    def getBranches(self, status=None, visible_by_user=None,
                    modified_since=None):
        """See `IHasBranches`."""
        if status is None:
            status = DEFAULT_BRANCH_STATUS_IN_LISTING

        collection = IBranchCollection(self).visibleByUser(visible_by_user)
        collection = collection.withLifecycleStatus(*status)
        if modified_since is not None:
            collection = collection.modifiedSince(modified_since)
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


class HasRequestedReviewsMixin:
    """A mixin implementation class for `IHasRequestedReviews`."""

    def getRequestedReviews(self, status=None, visible_by_user=None):
        """See `IHasRequestedReviews`."""
        if not status:
            status = (BranchMergeProposalStatus.NEEDS_REVIEW,)

        visible_branches = getUtility(IAllBranches).visibleByUser(
            visible_by_user)
        proposals = visible_branches.getMergeProposalsForReviewer(self, status)
        return proposals
