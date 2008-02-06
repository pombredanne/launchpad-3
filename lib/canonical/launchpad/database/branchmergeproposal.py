# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database class for branch merge prosals."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposal',
    ]

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol

from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.launchpad.database.branchrevision import BranchRevision
from canonical.launchpad.interfaces import (
    BadStateTransition,
    BRANCH_MERGE_PROPOSAL_FINAL_STATES,
    BranchMergeProposalStatus, IBranchMergeProposal,
    ILaunchpadCelebrities,
    UserNotBranchReviewer)


class BranchMergeProposal(SQLBase):
    """A relationship between a person and a branch."""

    implements(IBranchMergeProposal)

    _table = 'BranchMergeProposal'
    _defaultOrder = ['-date_created', 'id']

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', notNull=True)

    source_branch = ForeignKey(
        dbName='source_branch', foreignKey='Branch', notNull=True)

    target_branch = ForeignKey(
        dbName='target_branch', foreignKey='Branch', notNull=True)

    dependent_branch = ForeignKey(
        dbName='dependent_branch', foreignKey='Branch', notNull=False)

    whiteboard = StringCol(default=None)

    queue_status = EnumCol(
        enum=BranchMergeProposalStatus, notNull=True,
        default=BranchMergeProposalStatus.WORK_IN_PROGRESS)

    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person', notNull=False,
        default=None)
    reviewed_revision_id = StringCol(default=None)

    date_merged = UtcDateTimeCol(default=None)
    merged_revno = IntCol(default=None)

    merge_reporter = ForeignKey(
        dbName='merge_reporter', foreignKey='Person', notNull=False,
        default=None)

    superceded_proposal = ForeignKey(
        dbName='superceded_proposal', foreignKey='BranchMergeProposal',
        notNull=False, default=None)

    @property
    def superceded_by(self):
        return BranchMergeProposal.selectOneBy(
            superceded_proposal=self)

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_review_requested = UtcDateTimeCol(notNull=False, default=None)
    date_reviewed = UtcDateTimeCol(notNull=False, default=None)

    def _transitionState(self, next_state, invalid_states=None):
        """Update the queue_status of the proposal.

        Raise an error if the proposal is in a final state.
        """
        if invalid_states is None:
            invalid_states = BRANCH_MERGE_PROPOSAL_FINAL_STATES
        if self.queue_status in invalid_states:
            raise BadStateTransition(
                'Invalid state transition for merge proposal: %s -> %s'
                % (self.queue_status.title, next_state.title))
        # Transition to the same state occur in two particular
        # situations:
        #  * stale posts
        #  * approving a later revision
        # In both these cases, there is no real reason to disallow
        # transitioning to the same state.
        self.queue_status = next_state

    def setAsWorkInProgress(self):
        """See `IBranchMergeProposal`."""
        self._transitionState(BranchMergeProposalStatus.WORK_IN_PROGRESS)
        self.date_review_requested = None

    def requestReview(self):
        """See `IBranchMergeProposal`."""
        self._transitionState(BranchMergeProposalStatus.NEEDS_REVIEW)
        self.date_review_requested = UTC_NOW

    def isPersonValidReviewer(self, reviewer):
        """See `IBranchMergeProposal`."""
        if reviewer is None:
            return False
        # We trust Launchpad admins.
        lp_admins = getUtility(ILaunchpadCelebrities).admin
        return (reviewer.inTeam(self.target_branch.code_reviewer) or
                reviewer.inTeam(lp_admins))

    def isMergable(self):
        """See `IBranchMergeProposal`."""
        # As long as the source branch has not been merged, rejected
        # or superceded, then it is valid to be merged.
        return (self.queue_status not in
                BRANCH_MERGE_PROPOSAL_FINAL_STATES)

    def _reviewProposal(self, reviewer, next_state, revision_id):
        """Set the proposal to one of the two review statuses."""
        # Check the reviewer can review the code for the target branch.
        if not self.isPersonValidReviewer(reviewer):
            raise UserNotBranchReviewer
        # Check the current state of the proposal.
        self._transitionState(next_state)
        # Record the reviewer
        self.reviewer = reviewer
        self.date_reviewed = UTC_NOW
        # Record the reviewed revision id
        self.reviewed_revision_id = revision_id

    def approveBranch(self, reviewer, revision_id):
        """See `IBranchMergeProposal`."""
        self._reviewProposal(
            reviewer, BranchMergeProposalStatus.CODE_APPROVED, revision_id)

    def rejectBranch(self, reviewer, revision_id):
        """See `IBranchMergeProposal`."""
        self._reviewProposal(
            reviewer, BranchMergeProposalStatus.REJECTED, revision_id)

    def mergeFailed(self, merger):
        """See `IBranchMergeProposal`."""
        self._transitionState(BranchMergeProposalStatus.MERGE_FAILED)
        self.merger = merger

    def markAsMerged(self, merged_revno=None, date_merged=None,
                     merge_reporter=None):
        """See `IBranchMergeProposal`."""
        self._transitionState(BranchMergeProposalStatus.MERGED)
        self.merged_revno = merged_revno
        self.merge_reporter = merge_reporter

        if merged_revno is not None:
            branch_revision = BranchRevision.selectOneBy(
                branch=self.target_branch, sequence=merged_revno)
            if branch_revision is not None:
                date_merged = branch_revision.revision.revision_date

        if date_merged is None:
            date_merged = UTC_NOW
        self.date_merged = date_merged

    def resubmit(self, registrant):
        """See `IBranchMergeProposal`."""
        # You can transition from REJECTED to SUPERCEDED, but
        # not from MERGED or SUPERCEDED.
        self._transitionState(
            BranchMergeProposalStatus.SUPERCEDED,
            invalid_states=[BranchMergeProposalStatus.MERGED,
                            BranchMergeProposalStatus.SUPERCEDED])
        self.syncUpdate()
        proposal = self.source_branch.addLandingTarget(
            registrant=registrant,
            target_branch=self.target_branch,
            dependent_branch=self.dependent_branch,
            whiteboard=self.whiteboard)
        proposal.superceded_proposal = self
        return proposal

    def deleteProposal(self):
        """See `IBranchMergeProposal`."""
        # Delete this proposal, but keep the superceded chain linked.
        if self.superceded_by is not None:
            self.superceded_by.superceded_proposal = self.superceded_proposal
            self.superceded_by.syncUpdate()
        self.destroySelf()

    def getUnlandedSourceBranchRevisions(self):
        """See `IBranchMergeProposal`."""
        return BranchRevision.select('''
            BranchRevision.branch = %s AND
            BranchRevision.sequence IS NOT NULL AND
            BranchRevision.revision NOT IN (
              SELECT revision FROM BranchRevision
              WHERE branch = %s)
            ''' % sqlvalues(self.source_branch, self.target_branch),
            prejoins=['revision'], orderBy='-sequence')
