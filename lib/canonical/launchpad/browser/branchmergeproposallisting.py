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
from lazr.delegates import delegates


class BranchMergeProposalListingItem:
    """A branch merge proposal that knows summary values for comments."""

    delegates(IBranchMergeProposal, 'context')

    def __init__(self, branch_merge_proposal, summary, proposal_reviewer):
        self.context = branch_merge_proposal
        self.summary = summary
        self.proposal_reviewer = proposal_reviewer

    @property
    def vote_summary(self):
        """A short summary of the votes."""
        votes = []
        # XXX: rockstar - 9 Oct 2009 - HTML in python is bad. See bug #281063.
        for vote in CodeReviewVote.items:
            vote_count = self.summary.get(vote, 0)
            if vote_count > 0:
                votes.append('<span class="vote%s">%s:&nbsp;%s</span>' % (
                        vote.name, vote.title, vote_count))

        comment_count = self.summary['comment_count']
        if comment_count > 0:
            votes.append("Comments:&nbsp;%s" % comment_count)

        if len(votes) == 0:
            votes.append('<em>None</em>')

        return ', '.join(votes)

    @property
    def reviewer_vote(self):
        """A vote from the specified reviewer."""
        review = self.context.getUsersVoteReference(self.proposal_reviewer)
        if not review.comment:
            return '<em>None</em>'
        return 'Vote goes here!'



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
        return BranchMergeProposalListingItem(proposal, summary,
            proposal_reviewer=self.view.getUserFromContext())

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

    def getUserFromContext(self):
        """Get the relevant user from the context."""
        return None

    def getVisibleProposalsForUser(self):
        """Branch merge proposals that are visible by the logged in user."""
        return getUtility(IBranchMergeProposalGetter).getProposalsForContext(
            self.context, self._queue_status, self.user)

    @cachedproperty
    def proposal_count(self):
        """Return the number of proposals that will be returned."""
        return self.getVisibleProposalsForUser().count()
