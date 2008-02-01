# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database class for branch merge prosals."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposal',
    ]

from email.Utils import make_msgid

from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol

from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.launchpad.database.branchrevision import BranchRevision
from canonical.launchpad.database.codereviewmessage import CodeReviewMessage
from canonical.launchpad.database.codereviewsubscription import (
    CodeReviewSubscription,
    )
from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.interfaces import (
    BadStateTransition, BranchMergeProposalStatus, IBranchMergeProposal,
    UserNotBranchReviewer)


class BranchMergeProposal(SQLBase):
    """A relationship between a person and a branch."""

    implements(IBranchMergeProposal)

    _table = 'BranchMergeProposal'
    _defaultOrder = ['-date_created']

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

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_review_requested = UtcDateTimeCol(notNull=False, default=None)
    date_reviewed = UtcDateTimeCol(notNull=False, default=None)

    conversation = ForeignKey(
        dbName='conversation', foreignKey='CodeReviewMessage', notNull=False,
        default=None)

    def setAsWorkInProgress(self):
        """See `IBranchMergeProposal`."""
        if self.queue_status == BranchMergeProposalStatus.MERGED:
            raise BadStateTransition('Merged proposals cannot change state.')
        self.queue_status = BranchMergeProposalStatus.WORK_IN_PROGRESS
        self.date_review_requested = None

    def requestReview(self):
        """See `IBranchMergeProposal`."""
        if self.queue_status == BranchMergeProposalStatus.MERGED:
            raise BadStateTransition('Merged proposals cannot change state.')
        self.queue_status = BranchMergeProposalStatus.NEEDS_REVIEW
        self.date_review_requested = UTC_NOW

    def isPersonValidReviewer(self, reviewer):
        """See `IBranchMergeProposal`."""
        if reviewer is None:
            return False
        return reviewer.inTeam(self.target_branch.code_reviewer)

    def isReviewable(self):
        """See `IBranchMergeProposal`."""
        # As long as the source branch has not been merged, it is valid
        # to review it.
        return self.queue_status != BranchMergeProposalStatus.MERGED

    def _reviewProposal(self, reviewer, next_state, revision_id):
        """Set the proposal to one of the two review statuses."""
        # Check the reviewer can review the code for the target branch.
        if not self.isPersonValidReviewer(reviewer):
            raise UserNotBranchReviewer
        # Check the current state of the proposal.
        if not self.isReviewable():
            raise BadStateTransition(
                'Invalid state transition for merge proposal: %s -> %s'
                % (self.queue_state.title, next_state.title))
        self.queue_status = next_state
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
        self.queue_status = BranchMergeProposalStatus.MERGE_FAILED
        self.merger = merger

    def markAsMerged(self, merged_revno=None, date_merged=None,
                     merge_reporter=None):
        """See `IBranchMergeProposal`."""
        self.queue_status = BranchMergeProposalStatus.MERGED
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

    def createMessage(self, owner, subject, content=None, vote=None,
                      parent=None):
        """See IBranchMergeProposal.createMessage"""
        assert owner is not None, 'Merge proposal messages need a sender'
        parent_message = None
        if parent is None:
            if self.conversation is not None:
                parent_message = self.conversation.message
        else:
            assert parent.branch_merge_proposal == self, \
                    'Replies must use the same merge proposal as their parent'
            parent_message = parent.message
        msgid = make_msgid('codereview')
        msg = Message(parent=parent_message, owner=owner,
                      rfc822msgid=msgid, subject=subject)
        chunk = MessageChunk(message=msg, content=content, sequence=1)
        crmsg = CodeReviewMessage(
            branch_merge_proposal=self, message=msg, vote=vote)
        if self.conversation is None:
            self.conversation = crmsg
        return crmsg

    def createSubscription(self, subscriber, registrant=None):
        if registrant is None:
            registrant = subscriber
        return CodeReviewSubscription(
            branch_merge_proposal=self, person=subscriber,
            registrant=registrant)
