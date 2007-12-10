# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""The interface for branch merge proposals."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalStatus',
    'InvalidBranchMergeProposal',
    'IBranchMergeProposal',
    'UserNotBranchReviewer',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Int

from canonical.launchpad import _
from canonical.launchpad.fields import Whiteboard
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


class IBranchMergeProposal(Interface):
    """Branch merge proposals show intent of landing one branch on another."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this question."))

    registrant = Choice(
        title=_('Person'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=True,
        description=_('The person who registered the landing target.'))

    source_branch = Choice(
        title=_('Source Branch'),
        vocabulary='Branch', required=True, readonly=True,
        description=_("The branch that has code to land."))

    target_branch = Choice(
        title=_('Target Branch'),
        vocabulary='Branch', required=True, readonly=True,
        description=_("The branch that the source branch will be merged into."))

    dependent_branch = Choice(
        title=_('Dependent Branch'),
        vocabulary='Branch', required=False, readonly=True,
        description=_("The branch that the source branch branched from. "
                      "If this is the same as the target branch, then leave "
                      "this field blank."))

    whiteboard = Whiteboard(
        title=_('Whiteboard'), required=False,
        description=_('Notes about the merge.'))

    queue_status = Attribute(_("The current state of the proposal."))

    reviewer = Attribute(
        _("The person that accepted (or rejected) the code for merging."))
    reviewed_revision_id = Attribute(
        _("The revision id that has been approved by the reviewer."))

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

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    date_review_requested = Datetime(
        title=_('Date Review Requested'), required=False, readonly=True)
    date_reviewed = Datetime(
        title=_('Date Reviewed'), required=False, readonly=True)

    def requestReview():
        """Set the state of merge proposal to 'Needs review'.

        As long as the branch is not yet merged, a review can be requested.
        Requesting a review sets the date_review_requested.
        """

    def approveBranch(reviewer, revision_id):
        """Mark the proposal as 'Code approved'.

        The time that the branch was approved is recoreded in `date_reviewed`.

        :param reviewer: A person authorised to approve branches for merging.
        :param revision_id: The revision id of the tip of the branch that was
                            reviewed by the `reviewer`.

        :raises: UserNotBranchReviewer if the reviewer is not in the team of
                 the branch reviewer for the target branch.
        """

    def rejectBranch(reviewer):
        """Mark the proposal as 'Rejected'.

        The time that the branch was rejected is recoreded in `date_reviewed`.

        :raises: UserNotBranchReviewer if the reviewer is not in the team of
                 the branch reviewer for the target branch.
        """

    def mergeFailed(merger):
        """Mark the proposal as 'Code failed to merge'."""

    def markAsMerged(merged_revno=None, date_merged=None, merge_reporter=None):
        """Mark the branch merge proposal as merged.

        If the `merged_revno` is supplied, then the `BranchRevision` is checked
        to see that revision is available in the target branch.  If it is
        then the date from that revision is used as the `date_merged`.  If it
        is not available, then the `date_merged` is set as if the merged_revno
        was not supplied.

        If no `merged_revno` is supplied, the `date_merged` is set to the value
        of date_merged, or if the parameter date_merged is None, then UTC_NOW
        is used.

        :param merged_revno: The revision number in the target branch that
                             contains the merge of the source branch.
        :type merged_revno: ``int``

        :param date_merged: The date/time that the merge took place.
        :type merged_revno: ``datetime`` or a stringified date time value.

        :param merge_reporter: The user that is marking the branch as merged.
        :type merge_reporter: ``Person``
        """

    def personCanReview(reviewer):
        """Return true if the `reviewer` is able to review the proposal.

        There is an attribute on branches called `reviewer` which allows
        a specific person or team to be set for a branch as an authorised
        person to approve merges for a branch.  If a reviewer is not set
        on the target branch, then the owner of the target branch is used
        as the authorised user.
        """

    def isReviewable(self):
        """Is the proposal is in a state condusive to being reviewed?

        If the proposal is in one of the following states, then it can
        be reviewed:
          * Work in progress
          * Review requested
          * Approved
          * Rejected
        """
