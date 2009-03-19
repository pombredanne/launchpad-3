# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base class view for branch merge proposal listings."""

__metaclass__ = type

__all__ = [
    'BranchMergeProposalListingItem',
    'BranchMergeProposalListingView',
    'PersonActiveReviewsView',
    'PersonApprovedMergesView',
    'ProductActiveReviewsView',
    'ProductApprovedMergesView',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus, IBranchMergeProposal,
    IBranchMergeProposalGetter, IBranchMergeProposalListingBatchNavigator)
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
        return self.comment_count == 0 and self.vote_type_count == 0

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


class PersonBMPListingView(BranchMergeProposalListingView):
    """Base class for the proposal listings that defines the user."""

    def getUserFromContext(self):
        """Get the relevant user from the context."""
        return self.context


class PersonActiveReviewsView(PersonBMPListingView):
    """Branch merge proposals that the person has submitted."""

    extra_columns = ['date_review_requested', 'vote_summary']
    _queue_status = [BranchMergeProposalStatus.NEEDS_REVIEW]

    @property
    def heading(self):
        return "Active code reviews for %s" % self.context.displayname

    @property
    def no_proposal_message(self):
        """Shown when there is no table to show."""
        return "%s has no active code reviews." % self.context.displayname


class PersonRequestedReviewsView(PersonBMPListingView):
    """Branch merge proposals for the person that are needing review."""

    extra_columns = ['date_review_requested', 'review',]
    _queue_status = [BranchMergeProposalStatus.CODE_APPROVED,
                     BranchMergeProposalStatus.NEEDS_REVIEW]

    @property
    def heading(self):
        return "Code reviews requested of %s" % self.context.displayname

    @property
    def no_proposal_message(self):
        """Shown when there is no table to show."""
        return "%s has no reviews pending." % self.context.displayname

    def getVisibleProposalsForUser(self):
        """Branch merge proposals that are visible by the logged in user."""
        return getUtility(IBranchMergeProposalGetter).getProposalsForReviewer(
            self.context, self._queue_status, self.user)


class PersonApprovedMergesView(PersonBMPListingView):
    """Branch merge proposals that have been approved for the person."""

    extra_columns = ['date_reviewed']
    _queue_status = [BranchMergeProposalStatus.CODE_APPROVED]

    @property
    def heading(self):
        return "Approved merges for %s" % self.context.displayname

    @property
    def no_proposal_message(self):
        """Shown when there is no table to show."""
        return "%s has no approved merges." % self.context.displayname


class ProductActiveReviewsView(BranchMergeProposalListingView):
    """Branch merge proposals for the product that are needing review."""

    show_diffs = False

    # The grouping classifications.
    TO_DO = 'to_do'
    ARE_DOING = 'are_doing'
    CAN_DO = 'can_do'
    MINE = 'mine'
    OTHER = 'other'

    def _getReviewGroup(self, proposal, votes):
        """Return one of MINE, TO_DO, CAN_DO, ARE_DOING, or OTHER.

        These groupings define the different tables that the user is able to
        see.

        If the source branch is owned by the user, or the proposal was
        registered by the user, then the group is MINE.

        If there is a pending vote reference for the logged in user, then the
        group is TO_DO as the user is expected to review.  If there is a vote
        reference where it is not pending, this means that the user has
        reviewed, so the group is ARE_DOING.  If there is a pending review
        requested of a team that the user is in, then the review becomes a
        CAN_DO.  All others are OTHER.
        """
        if (self.user is not None and
            (proposal.source_branch.owner == self.user or
             (self.user.inTeam(proposal.source_branch.owner) and
              proposal.registrant == self.user))):
            return self.MINE

        result = self.OTHER

        for vote in votes:
            if self.user is not None:
                if vote.reviewer == self.user:
                    if vote.comment is None:
                        return self.TO_DO
                    else:
                        return self.ARE_DOING
                # Since team reviews are always pending, and we've eliminated
                # the case where the reviewer is ther person, then if the user
                # is in the reviewer team, it is a can do.
                if self.user.inTeam(vote.reviewer):
                    result = self.CAN_DO
        return result

    def initialize(self):
        # Work out the review groups
        self.review_groups = {}
        getter = getUtility(IBranchMergeProposalGetter)
        proposals = list(getter.getProposalsForContext(
            self.context, [BranchMergeProposalStatus.NEEDS_REVIEW],
            self.user))
        all_votes = getter.getVotesForProposals(proposals)
        vote_summaries = getter.getVoteSummariesForProposals(proposals)
        for proposal in proposals:
            proposal_votes = all_votes[proposal]
            review_group = self._getReviewGroup(
                proposal, proposal_votes)
            self.review_groups.setdefault(review_group, []).append(
                BranchMergeProposalListingItem(
                    proposal, vote_summaries[proposal], None, proposal_votes))
            if proposal.preview_diff is not None:
                self.show_diffs = True
        self.proposal_count = len(proposals)

    @property
    def other_heading(self):
        """Return the heading to be used for the OTHER group.

        If there is no user, or there are no reviews in any user specific
        group, then don't show a heading for the OTHER group.
        """
        if self.user is None:
            return None
        personal_review_count = (
            len(self.review_groups.get(self.TO_DO, [])) +
            len(self.review_groups.get(self.CAN_DO, [])) +
            len(self.review_groups.get(self.MINE, [])) +
            len(self.review_groups.get(self.ARE_DOING, [])))
        if personal_review_count > 0:
            return _('Other reviews')
        else:
            return None

    @property
    def heading(self):
        return "Active code reviews for %s" % self.context.displayname

    @property
    def no_proposal_message(self):
        """Shown when there is no table to show."""
        return "%s has no active code reviews." % self.context.displayname


class ProductApprovedMergesView(BranchMergeProposalListingView):
    """Branch merge proposals for the product that have been approved."""

    extra_columns = ['date_reviewed']
    _queue_status = [BranchMergeProposalStatus.CODE_APPROVED]

    @property
    def heading(self):
        return "Approved merges for %s" % self.context.displayname

    @property
    def no_proposal_message(self):
        """Shown when there is no table to show."""
        return "%s has no approved merges." % self.context.displayname
