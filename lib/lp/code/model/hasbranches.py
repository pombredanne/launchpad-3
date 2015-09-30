# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Mixin classes to implement methods for IHas<code related bits>."""

__metaclass__ = type
__all__ = [
    'HasBranchesMixin',
    'HasCodeImportsMixin',
    'HasMergeProposalsMixin',
    'HasRequestedReviewsMixin',
    ]

from functools import partial

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.enums import BranchMergeProposalStatus
from lp.code.interfaces.branch import DEFAULT_BRANCH_STATUS_IN_LISTING
from lp.code.interfaces.branchcollection import (
    IAllBranches,
    IBranchCollection,
    )
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.gitcollection import (
    IAllGitRepositories,
    IGitCollection,
    )
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.services.database.decoratedresultset import DecoratedResultSet


class HasBranchesMixin:
    """A mixin implementation for `IHasBranches`."""

    def getBranches(self, status=None, visible_by_user=None,
                    modified_since=None, eager_load=False):
        """See `IHasBranches`."""
        if status is None:
            status = DEFAULT_BRANCH_STATUS_IN_LISTING

        collection = IBranchCollection(self).visibleByUser(visible_by_user)
        collection = collection.withLifecycleStatus(*status)
        if modified_since is not None:
            collection = collection.modifiedSince(modified_since)
        return collection.getBranches(eager_load=eager_load)


class HasMergeProposalsMixin:
    """A mixin implementation class for `IHasMergeProposals`."""

    def getMergeProposals(self, status=None, visible_by_user=None,
                          eager_load=False):
        """See `IHasMergeProposals`."""
        # Circular import.
        from lp.code.model.branchmergeproposal import BranchMergeProposal

        if not status:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS)

        def _getProposals(interface):
            collection = removeSecurityProxy(interface(self))
            collection = collection.visibleByUser(visible_by_user)
            return collection.getMergeProposals(status, eager_load=False)

        # SourcePackage Bazaar branches are an abberation which was not
        # replicated for Git, so SourcePackage does not support Git.
        if ISourcePackage.providedBy(self):
            proposals = _getProposals(IBranchCollection)
        else:
            proposals = _getProposals(IBranchCollection).union(
                _getProposals(IGitCollection))
        if not eager_load:
            return proposals
        else:
            loader = partial(
                BranchMergeProposal.preloadDataForBMPs, user=visible_by_user)
            return DecoratedResultSet(proposals, pre_iter_hook=loader)


class HasRequestedReviewsMixin:
    """A mixin implementation class for `IHasRequestedReviews`."""

    def getRequestedReviews(self, status=None, visible_by_user=None):
        """See `IHasRequestedReviews`."""
        if not status:
            status = (BranchMergeProposalStatus.NEEDS_REVIEW,)

        visible_branches = getUtility(IAllBranches).visibleByUser(
            visible_by_user)
        return visible_branches.getMergeProposalsForReviewer(self, status)

    def getOwnedAndRequestedReviews(self, status=None, visible_by_user=None,
                                    project=None, eager_load=False):
        """See `IHasRequestedReviews`."""
        # Circular import.
        from lp.code.model.branchmergeproposal import BranchMergeProposal

        if not status:
            status = (BranchMergeProposalStatus.NEEDS_REVIEW,)

        def _getProposals(collection):
            collection = collection.visibleByUser(visible_by_user)
            return collection.getMergeProposalsForPerson(
                self, status, eager_load=False)

        bzr_collection = removeSecurityProxy(getUtility(IAllBranches))
        git_collection = removeSecurityProxy(getUtility(IAllGitRepositories))
        if project is not None:
            bzr_collection = bzr_collection.inProduct(project)
            git_collection = git_collection.inProject(project)
        proposals = _getProposals(bzr_collection).union(
            _getProposals(git_collection))
        if not eager_load:
            return proposals
        else:
            loader = partial(
                BranchMergeProposal.preloadDataForBMPs, user=visible_by_user)
            return DecoratedResultSet(proposals, pre_iter_hook=loader)


class HasCodeImportsMixin:

    def newCodeImport(self, registrant=None, branch_name=None,
            rcs_type=None, url=None, cvs_root=None, cvs_module=None,
            owner=None):
        """See `IHasCodeImports`."""
        return IBranchTarget(self).newCodeImport(registrant, branch_name,
                rcs_type, url=url, cvs_root=cvs_root, cvs_module=cvs_module,
                owner=owner)
