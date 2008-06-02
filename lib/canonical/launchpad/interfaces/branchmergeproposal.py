# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""The interface for branch merge proposals."""

__metaclass__ = type
__all__ = [
    'BadStateTransition',
    'BranchMergeProposalStatus',
    'BRANCH_MERGE_PROPOSAL_FINAL_STATES',
    'InvalidBranchMergeProposal',
    'IBranchMergeProposal',
    'IBranchMergeProposalGetter',
    'UserNotBranchReviewer',
    'WrongBranchMergeProposal',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Int, List

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice, Summary, Whiteboard
from canonical.lazr import DBEnumeratedType, DBItem


class InvalidBranchMergeProposal(Exception):
    """Raised during the creation of a new branch merge proposal.

    The text of the exception is the rule violation.
    """


class UserNotBranchReviewer(Exception):
    """The user who attempted to review the merge proposal isn't a reviewer.

    A specific reviewer may be set on a branch.  If a specific reviewer
    isn't set then any user in the team of the owner of the branch is
    considered a reviewer.
    """


class BadStateTransition(Exception):
    """The user requested a state transition that is not possible."""


class WrongBranchMergeProposal(Exception):
    """The message requested is not associated with this merge proposal."""


class BranchMergeProposalStatus(DBEnumeratedType):
    """Branch Merge Proposal Status

    The current state of a proposal to merge.
    """

    WORK_IN_PROGRESS = DBItem(1, """
        Work in progress

        The source branch is actively being worked on.
        """)

    NEEDS_REVIEW = DBItem(2, """
        Needs review

        A review of the changes has been requested.
        """)

    CODE_APPROVED = DBItem(3, """
        Code approved

        The changes have been approved for merging.
        """)

    REJECTED = DBItem(4, """
        Rejected

        The changes have been rejected and will not be merged in their
        current state.
        """)

    MERGED = DBItem(5, """
        Merged

        The changes from the source branch were merged into the target
        branch.
        """)

    MERGE_FAILED = DBItem(6, """
        Code failed to merge

        The changes from the source branch failed to merge into the
        target branch for some reason.
        """)

    QUEUED = DBItem(7, """
        Queued

        The changes from the source branch are queued to be merged into the
        target branch.
        """)

    SUPERSEDED = DBItem(10, """
        Superseded

        This proposal has been superseded by anther proposal to merge.
        """)


BRANCH_MERGE_PROPOSAL_FINAL_STATES = (
    BranchMergeProposalStatus.REJECTED,
    BranchMergeProposalStatus.MERGED,
    BranchMergeProposalStatus.SUPERSEDED,
    )


class IBranchMergeProposal(Interface):
    """Branch merge proposals show intent of landing one branch on another."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this question."))

    registrant = PublicPersonChoice(
        title=_('Person'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=True,
        description=_('The person who registered the landing target.'))

    source_branch = Choice(
        title=_('Source Branch'),
        vocabulary='BranchRestrictedOnProduct', required=True, readonly=True,
        description=_("The branch that has code to land."))

    target_branch = Choice(
        title=_('Target Branch'),
        vocabulary='BranchRestrictedOnProduct', required=True, readonly=True,
        description=_(
            "The branch that the source branch will be merged into."))

    dependent_branch = Choice(
        title=_('Dependent Branch'),
        vocabulary='BranchRestrictedOnProduct', required=False, readonly=True,
        description=_("The branch that the source branch branched from. "
                      "If this is the same as the target branch, then leave "
                      "this field blank."))

    whiteboard = Whiteboard(
        title=_('Whiteboard'), required=False,
        description=_('Notes about the merge.'))

    queue_status = Choice(
        title=_('Status'),
        vocabulary=BranchMergeProposalStatus, required=True, readonly=True,
        description=_("The current state of the proposal."))

    reviewer = Attribute(
        _("The person that accepted (or rejected) the code for merging."))
    reviewed_revision_id = Attribute(
        _("The revision id that has been approved by the reviewer."))


    commit_message = Summary(
        title=_("Commit Message"), required=False,
        description=_("The commit message that should be used when merging "
                      "the source branch."))

    queue_position = Int(
        title=_("Queue Position"), required=False, readonly=True,
        description=_("The position in the queue."))

    queuer = Choice(
        title=_('Queuer'), vocabulary='ValidPerson',
        required=False, readonly=True,
        description=_("The person that queued up the branch."))

    queued_revision_id = Attribute(
        _("The revision id that has been queued for landing."))

    merged_revno = Int(
        title=_("Merged Revision Number"), required=False,
        description=_("The revision number on the target branch which "
                      "contains the merge from the source branch."))

    date_merged = Datetime(
        title=_('Date Merged'), required=False,
        description=_("The date that the source branch was merged into the "
                      "target branch"))

    merge_reporter = Attribute(
        "The user that marked the branch as merged.")

    supersedes = Attribute(
        "The branch merge proposal that this one supersedes.")
    superseded_by = Attribute(
        "The branch merge proposal that supersedes this one.")

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    date_review_requested = Datetime(
        title=_('Date Review Requested'), required=False, readonly=True)
    date_reviewed = Datetime(
        title=_('Date Reviewed'), required=False, readonly=True)
    date_queued = Datetime(
        title=_('Date Queued'), required=False, readonly=True)
    # Cannote use Object as this would cause circular dependencies.
    root_message = Attribute(
        _("The first message in discussion of this merge proposal"))
    all_messages = Attribute(
        _("All messages discussing this merge proposal"))

    def getMessage(id):
        """Return the CodeReviewMessage with the specified ID."""

    def getNotificationRecipients(min_level):
        """Return the people who should be notified.

        Recipients will be returned as a dictionary where the key is the
        person, and the values are (subscription, rationale) tuples.

        :param min_level: The minimum notification level needed to be
            notified.
        """


    # Cannot specify value type without creating a circular dependency
    votes = List(
        title=_('The votes cast or expected for this proposal'),
        )

    def isValidTransition(next_state, user=None):
        """True if it is valid for user update the proposal to next_state."""

    def setAsWorkInProgress():
        """Set the state of the merge proposal to 'Work in progress'.

        This is often useful if the proposal was rejected and is being worked
        on again, or if the code failed to merge and requires rework.
        """

    def requestReview():
        """Set the state of merge proposal to 'Needs review'.

        As long as the branch is not yet merged, a review can be requested.
        Requesting a review sets the date_review_requested.
        """

    def approveBranch(reviewer, revision_id):
        """Mark the proposal as 'Code approved'.

        The time that the branch was approved is recoreded in `date_reviewed`.

        :param reviewer: A person authorised to review branches for merging.
        :param revision_id: The revision id of the branch that was
                            reviewed by the `reviewer`.

        :raises: UserNotBranchReviewer if the reviewer is not in the team of
                 the branch reviewer for the target branch.
        """

    def rejectBranch(reviewer, revision_id):
        """Mark the proposal as 'Rejected'.

        The time that the branch was rejected is recoreded in `date_reviewed`.

        :param reviewer: A person authorised to review branches for merging.
        :param revision_id: The revision id of the branch that was
                            reviewed by the `reviewer`.

        :raises: UserNotBranchReviewer if the reviewer is not in the team of
                 the branch reviewer for the target branch.
        """

    def enqueue(queuer, revision_id):
        """Put the proposal into the merge queue for the target branch.

        If the proposal is not in the Approved state before this method
        is called, approveBranch is called with the reviewer and revision_id
        specified.
        """

    def dequeue():
        """Take the proposal out of the merge queue of the target branch.

        :raises: BadStateTransition if the proposal is not in the queued
                 state.
        """

    def moveToFrontOfQueue():
        """Move the queue proposal to the front of the queue."""

    def mergeFailed(merger):
        """Mark the proposal as 'Code failed to merge'."""

    def markAsMerged(merged_revno=None, date_merged=None,
                     merge_reporter=None):
        """Mark the branch merge proposal as merged.

        If the `merged_revno` is supplied, then the `BranchRevision` is
        checked to see that revision is available in the target branch.  If it
        is then the date from that revision is used as the `date_merged`.  If
        it is not available, then the `date_merged` is set as if the
        merged_revno was not supplied.

        If no `merged_revno` is supplied, the `date_merged` is set to the
        value of date_merged, or if the parameter date_merged is None, then
        UTC_NOW is used.

        :param merged_revno: The revision number in the target branch that
                             contains the merge of the source branch.
        :type merged_revno: ``int``

        :param date_merged: The date/time that the merge took place.
        :type merged_revno: ``datetime`` or a stringified date time value.

        :param merge_reporter: The user that is marking the branch as merged.
        :type merge_reporter: ``Person``
        """

    def resubmit(registrant):
        """Mark the branch merge proposal as superseded and return a new one.

        The new proposal is created as work-in-progress, and copies across
        user-entered data like the whiteboard.
        """

    def isPersonValidReviewer(reviewer):
        """Return true if the `reviewer` is able to review the proposal.

        There is an attribute on branches called `reviewer` which allows
        a specific person or team to be set for a branch as an authorised
        person to approve merges for a branch.  If a reviewer is not set
        on the target branch, then the owner of the target branch is used
        as the authorised user.
        """

    def isMergable():
        """Is the proposal in a state that allows it to being merged?

        As long as the proposal isn't in one of the end states, it is valid
        to be merged.
        """

    def getUnlandedSourceBranchRevisions():
        """Return a sequence of `BranchRevision` objects.

        Returns those revisions that are in the revision history for the
        source branch that are not in the revision history of the target
        branch.  These are the revisions that have been committed to the
        source branch since it branched off the target branch.
        """

    def nominateReviewer(reviewer, registrant):
        """Create a vote for the specified person."""

    def createMessage(owner, subject, content=None, vote=None, vote_tag=None,
                      parent=None, _date_created=None):
        """Create an ICodeReviewMessage associated with this merge proposal.

        :param owner: The person who the message is from.
        :param subject: The subject line to use for the message.
        :param content: The text to use for the message content.  If
            unspecified, the text of the merge proposal is used.
        :param parent: The previous CodeReviewMessage in the thread.  If
            unspecified, the root message is used.
        :param _date_created: The date the message was created.  Provided only
            for testing purposes, as it can break
            BranchMergeProposal.root_message.
        """

    def createMessageFromMessage(self, message, vote, vote_tag):
        """Create an `ICodeReviewMessage` from an IMessage.

        :param message: The IMessage to use.
        :param vote: A CodeReviewVote (or None).
        :param vote_tag: A string (or None).
        """

    def deleteProposal():
        """Delete the proposal to merge."""


class IBranchMergeProposalGetter(Interface):
    """Utility for getting BranchMergeProposals."""

    def get(id):
        """Return the BranchMergeProposal with specified id."""
