# Copyright 2008 Canonical Ltd.  All rights reserved.

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
    IBranchMergeProposal, IBranchMergeProposalGetter,
    IBranchMergeProposalListingBatchNavigator)
from canonical.launchpad.interfaces.codereviewcomment import (
    CodeReviewVote)
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import TableBatchNavigator
from canonical.lazr import decorates


class BranchMergeProposalListingItem:
    """A branch merge proposal that knows summary values for comments."""

    decorates(IBranchMergeProposal, 'context')

    def __init__(self, branch_merge_proposal, comment_count,
                 disapprove_count, approve_count, abstain_count):
        self.context = branch_merge_proposal
        self.comment_count = comment_count
        self.disapprove_count = disapprove_count
        self.approve_count = approve_count
        self.abstain_count = abstain_count

    @property
    def vote_summary(self):
        """A short summary of the votes."""
        # If there are no comments, there can be no votes.
        if self.comment_count == 0:
            return "no votes (no comments)"

        votes = []
        if self.disapprove_count:
            votes.append("Disapprove: %s" % self.disapprove_count)
        if self.approve_count:
            votes.append("Approve: %s" % self.approve_count)
        if self.abstain_count:
            votes.append("Abstain: %s" % self.abstain_count)
        if len(votes) == 0:
            votes.append("no votes")

        return "%s (Comments: %s)" % (', '.join(votes), self.comment_count)


class BranchMergeProposalListingBatchNavigator(TableBatchNavigator):
    """Batch up the branch listings."""
    implements(IBranchMergeProposalListingBatchNavigator)

    def __init__(self, view):
        TableBatchNavigator.__init__(
            self, view.getVisibleProposalsForUser(), view.request,
            columns_to_show=view.extra_columns,
            size=config.launchpad.branchlisting_batch_size)
        self.view = view

    @cachedproperty
    def _proposals_for_current_batch(self):
        return list(self.currentBatch())

    @cachedproperty
    def _vote_summaries(self):
        """A dict of proposals to counts of votes and comments."""
        utility = getUtility(IBranchMergeProposalGetter)
        return utility.getVoteSummariesForProposals(
            self._proposals_for_current_batch)

    def _createItem(self, proposal):
        """Create the listing item for the proposal."""
        summary = self._vote_summaries[proposal]
        return BranchMergeProposalListingItem(
            proposal,
            summary['comment_count'],
            summary.get(CodeReviewVote.DISAPPROVE, 0),
            summary.get(CodeReviewVote.APPROVE, 0),
            summary.get(CodeReviewVote.ABSTAIN, 0))

    @property
    def proposals(self):
        """Return a list of BranchListingItems."""
        proposals = self._proposals_for_current_batch
        return [self._createItem(proposal) for proposal in proposals]

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
        """Branch merge proposals that are visible by the logged in user."""
        return getUtility(IBranchMergeProposalGetter).getProposalsForContext(
            self.context, self._queue_status, self.user)

    @cachedproperty
    def proposal_count(self):
        """Return the number of proposals that will be returned."""
        return self.getVisibleProposalsForUser().count()
