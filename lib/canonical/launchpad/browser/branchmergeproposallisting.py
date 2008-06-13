# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Base class view for branch merge proposal listings."""

__metaclass__ = type

__all__ = [
    'BranchMergeProposalListingView',
    ]


from storm.store import Store
from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.database.sqlbase import quote
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
        votes = []
        if self.disapprove_count:
            votes.append("Disapprove: %s" % self.disapprove_count)
        if self.approve_count:
            votes.append("Approve: %s" % self.approve_count)
        if self.abstain_count:
            votes.append("Abstain: %s" % self.abstain_count)
        if len(votes) == 0:
            votes.append("no votes")

        if self.comment_count:
            comments = "(Comments: %s)" % self.comment_count
        else:
            comments = "(no comments)"

        return "%s %s" % (', '.join(votes), comments)


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

    @cachedproperty
    def _proposal_comments(self):
        """A dict of proposal id to number of comments."""
        result = {}
        proposals = self._proposals_for_current_batch
        if len(proposals) != 0:
            store = Store.of(proposals[0])
            query = """
                SELECT bmp.id, count(crm.*)
                FROM BranchMergeProposal bmp, CodeReviewMessage crm
                WHERE bmp.id IN %s
                  AND bmp.id = crm.branch_merge_proposal
                GROUP BY bmp.id
                """ % quote([p.id for p in proposals])
            for proposal_id, count in store.execute(query):
                result[proposal_id] = count
        return result

    @cachedproperty
    def _proposal_votes(self):
        """A dict of proposal id to votes."""
        result = {}
        proposals = self._proposals_for_current_batch
        if len(proposals) != 0:
            store = Store.of(proposals[0])
            query = """
                SELECT bmp.id, crm.vote, count(crv.*)
                FROM BranchMergeProposal bmp, CodeReviewVote crv,
                     CodeReviewMessage crm
                WHERE bmp.id IN %s
                  AND bmp.id = crv.branch_merge_proposal
                  AND crv.vote_message = crm.id
                GROUP BY bmp.id, crm.vote
                """ % quote([p.id for p in proposals])
            for proposal_id, vote_value, count in store.execute(query):
                vote = CodeReviewVote.items[vote_value]
                result.setdefault(proposal_id, {})[vote] = count
        return result

    def _createItem(self, proposal):
        """Create the listing item for the proposal."""
        votes = self._proposal_votes.get(proposal.id, {})
        return BranchMergeProposalListingItem(
            proposal,
            self._proposal_comments.get(proposal.id, 0),
            votes.get(CodeReviewVote.DISAPPROVE, 0),
            votes.get(CodeReviewVote.APPROVE, 0),
            votes.get(CodeReviewVote.ABSTAIN, 0))

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
