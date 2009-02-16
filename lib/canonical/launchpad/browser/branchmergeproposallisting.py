# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base class view for branch merge proposal listings."""

__metaclass__ = type

__all__ = [
    'BranchMergeProposalListingItem',
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

    def __init__(self, branch_merge_proposal, summary, proposal_reviewer,
                 vote_references=None):
        self.context = branch_merge_proposal
        self.summary = summary
        self.proposal_reviewer = proposal_reviewer
        if vote_references is None:
            vote_references = []
        self.vote_references = vote_references

    @property
    def vote_summary_items(self):
        """A generator of votes.

        This is iterated over in TAL, and provides a items that are dict's for
        simple TAL traversal.

        The dicts contain the name and title of the enumerated vote type, the
        count of those votes and the reviewers whose latest review is of that
        type.
        """
        for vote in CodeReviewVote.items:
            vote_count = self.summary.get(vote, 0)
            if vote_count > 0:
                reviewers = []
                for ref in self.vote_references:
                    if ref.comment is not None and ref.comment.vote == vote:
                        reviewers.append(ref.reviewer.unique_displayname)
                yield {'name': vote.name, 'title': vote.title,
                       'count': vote_count,
                       'reviewers': ', '.join(sorted(reviewers))}

    @property
    def vote_type_count(self):
        """The number of vote types used on this proposal."""
        # The dict has one entry for comments and one for each type of vote.
        return len(self.summary) - 1

    @property
    def comment_count(self):
        """The number of comments (that aren't votes)."""
        return self.summary['comment_count']

    @property
    def has_no_activity(self):
        """True if no votes and no comments."""
        return self.comment_count == 0 and self.vote_count == 0

    @property
    def reviewer_vote(self):
        """A vote from the specified reviewer."""
        return self.context.getUsersVoteReference(self.proposal_reviewer)


class BranchMergeProposalListingBatchNavigator(TableBatchNavigator):
    """Batch up the branch listings."""
    implements(IBranchMergeProposalListingBatchNavigator)

    def __init__(self, view):
        TableBatchNavigator.__init__(
            self, view.getVisibleProposalsForUser(), view.request,
            columns_to_show=view.extra_columns,
            size=config.launchpad.branchlisting_batch_size)
        self.view = view
        # Add preview_diff to self.show_column dict if there are any diffs.
        for proposal in self.proposals:
            if proposal.preview_diff is not None:
                self.show_column['preview_diff'] = True

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

    @cachedproperty
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
