# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Base class view for branch merge proposal listings."""

__metaclass__ = type

__all__ = [
    'BranchMergeProposalListingView',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.interfaces.branchmergeproposal import (
    IBranchMergeProposalGetter, IBranchMergeProposalListingBatchNavigator)
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import TableBatchNavigator


class BranchMergeProposalListingBatchNavigator(TableBatchNavigator):
    """Batch up the branch listings."""
    implements(IBranchMergeProposalListingBatchNavigator)

    def __init__(self, view):
        TableBatchNavigator.__init__(
            self, view.getVisibleProposalsForUser(), view.request,
            columns_to_show=view.extra_columns,
            size=config.launchpad.branchlisting_batch_size)
        self.view = view
        self.column_count = 4 + len(view.extra_columns)

    @cachedproperty
    def _proposals_for_current_batch(self):
        return list(self.currentBatch())

    def proposals(self):
        """Return a list of BranchListingItems."""
        return self._proposals_for_current_batch

    @cachedproperty
    def multiple_pages(self):
        return self.batch.total() > self.batch.size

    @property
    def table_class(self):
        if self.multiple_pages:
            return "listing"
        else:
            return "listing sortable"


class BranchMergeProposalListingView(LaunchpadView):
    """A base class for views of branch merge proposal listings."""

    extra_columns = []
    _queue_status = None

    @property
    def proposals(self):
        """The batch navigator for the proposals."""
        return BranchMergeProposalListingBatchNavigator(self)

    def getVisibleProposalsForUser(self):
        """Called from the batch navigator."""
        return self._getProposals()

    def _getProposals(self):
        """Overridded by the derived classes."""
        return getUtility(IBranchMergeProposalGetter).getProposalsForContext(
            self.context, self._queue_status, self.user)

    @cachedproperty
    def proposal_count(self):
        """Return the number of proposals that will be returned."""
        return self._getProposals().count()
