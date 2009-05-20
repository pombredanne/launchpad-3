# Copyright 2007, 20008, 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""The interface for branch merge proposals."""

__metaclass__ = type
__all__ = [
    'BadBranchMergeProposalSearchContext',
    'BadStateTransition',
    'BranchMergeProposalExists',
    'BranchMergeProposalStatus',
    'BRANCH_MERGE_PROPOSAL_FINAL_STATES',
    'InvalidBranchMergeProposal',
    'IBranchMergeProposal',
    'IBranchMergeProposalGetter',
    'IBranchMergeProposalJob',
    'IBranchMergeProposalListingBatchNavigator',
    'ICreateMergeProposalJob',
    'ICreateMergeProposalJobSource',
    'IMergeProposalCreatedJob',
    'IMergeProposalCreatedJobSource',
    'UserNotBranchReviewer',
    'WrongBranchMergeProposal',
    ]

from zope.interface import Attribute, Interface
from zope.schema import (
    Bytes, Choice, Datetime, Int, Object, Text, TextLine)
from lazr.enum import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice, Summary, Whiteboard
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.person import IPerson
from canonical.launchpad.interfaces.diff import IPreviewDiff, IStaticDiff
from lp.services.job.interfaces.job import IJob
from canonical.launchpad.webapp.interfaces import ITableBatchNavigator
from lazr.restful.fields import CollectionField, Reference
from lazr.restful.declarations import (
    call_with, export_as_webservice_entry, export_read_operation,
    export_write_operation, exported, operation_parameters,
    operation_returns_entry, REQUEST_USER)


class InvalidBranchMergeProposal(Exception):
    """Raised during the creation of a new branch merge proposal.

    The text of the exception is the rule violation.
    """


class BranchMergeProposalExists(InvalidBranchMergeProposal):
    """Raised if there is already a matching BranchMergeProposal."""


class UserNotBranchReviewer(Exception):
    """The user who attempted to review the merge proposal isn't a reviewer.

    A specific reviewer may be set on a branch.  If a specific reviewer
    isn't set then any user in the team of the owner of the branch is
    considered a reviewer.
    """


class BadStateTransition(Exception):
    """The user requested a state transition that is not possible."""


class WrongBranchMergeProposal(Exception):
    """The comment requested is not associated with this merge proposal."""


class BadBranchMergeProposalSearchContext(Exception):
    """The context is not valid for a branch merge proposal search."""


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
        Approved

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

    export_as_webservice_entry()

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this question."))

    registrant = exported(
        PublicPersonChoice(
            title=_('Person'), required=True,
            vocabulary='ValidPersonOrTeam', readonly=True,
            description=_('The person who registered the landing target.')))

    source_branch = exported(
        Reference(
            title=_('Source Branch'), schema=IBranch,
            required=True, readonly=True,
            description=_("The branch that has code to land.")))

    target_branch = exported(
        Reference(
            title=_('Target Branch'),
            schema=IBranch, required=True, readonly=True,
            description=_(
                "The branch that the source branch will be merged into.")))

    dependent_branch = exported(
        Reference(
            title=_('Dependent Branch'),
            schema=IBranch, required=False, readonly=True,
            description=_("The branch that the source branch branched from. "
                          "If this is the same as the target branch, then "
                          "leave this field blank.")))

    whiteboard = Whiteboard(
        title=_('Whiteboard'), required=False,
        description=_('Notes about the merge.'))

    queue_status = exported(
        Choice(
            title=_('Status'),
            vocabulary=BranchMergeProposalStatus, required=True,
            readonly=True,
            description=_("The current state of the proposal.")))

    # Not to be confused with a code reviewer. A code reviewer is someone who
    # can vote or has voted on a proposal.
    reviewer = exported(
        PublicPersonChoice(
            title=_('Review person or team'), required=False,
            readonly=True, vocabulary='ValidPersonOrTeam',
            description=_("The person that accepted (or rejected) the code "
                          "for merging.")))

    review_diff = Reference(
        IStaticDiff, title=_('The diff to be used for reviews.'),
        readonly=True)

    preview_diff = exported(
        Reference(
            IPreviewDiff,
            title=_('The current diff of the source branch against the '
                    'target branch.'), readonly=True))

    reviewed_revision_id = Attribute(
        _("The revision id that has been approved by the reviewer."))


    commit_message = exported(
        Summary(
            title=_("Commit Message"), required=False,
            description=_("The commit message that should be used when "
                          "merging the source branch.")))

    queue_position = exported(
        Int(
            title=_("Queue Position"), required=False, readonly=True,
            description=_("The position in the queue.")))

    queuer = exported(
        PublicPersonChoice(
            title=_('Queuer'), vocabulary='ValidPerson',
            required=False, readonly=True,
            description=_("The person that queued up the branch.")))

    queued_revision_id = exported(
        Text(
            title=_("Queued Revision ID"), readonly=True,
            required=False,
            description=_("The revision id that has been queued for "
                          "landing.")))

    merged_revno = exported(
        Int(
            title=_("Merged Revision Number"), required=False,
            readonly=True,
            description=_("The revision number on the target branch which "
                          "contains the merge from the source branch.")))

    date_merged = exported(
        Datetime(
            title=_('Date Merged'), required=False,
            readonly=True,
            description=_("The date that the source branch was merged into "
                          "the target branch")))

    title = Attribute(
        "A nice human readable name to describe the merge proposal. "
        "This is generated from the source and target branch, and used "
        "as the tal fmt:link text and for email subjects.")

    merge_reporter = exported(
        PublicPersonChoice(
            title=_("Merge Reporter"), vocabulary="ValidPerson",
            required=False, readonly=True,
            description=_("The user that marked the branch as merged.")))

    supersedes = exported(
        Reference(
            title=_("Supersedes"),
            schema=Interface, required=False, readonly=True,
            description=_("The branch merge proposal that this one "
                          "supersedes.")))
    superseded_by = exported(
        Reference(
            title=_("Superseded By"), schema=Interface,
            required=False, readonly=True,
            description=_(
                "The branch merge proposal that supersedes this one.")))

    date_created = exported(
        Datetime(
            title=_('Date Created'), required=True, readonly=True))
    date_review_requested = exported(
        Datetime(
            title=_('Date Review Requested'), required=False, readonly=True))
    date_reviewed = exported(
        Datetime(
            title=_('Date Reviewed'), required=False, readonly=True))
    date_queued = exported(
        Datetime(
            title=_('Date Queued'), required=False, readonly=True))
    # Cannote use Object as this would cause circular dependencies.
    root_comment = Attribute(
        _("The first message in discussion of this merge proposal"))
    root_message_id = Text(
        title=_('The email message id from the first message'),
        required=False)
    all_comments = exported(
        CollectionField(
            title=_("All messages discussing this merge proposal"),
            value_type=Reference(schema=Interface), # ICodeReviewComment
            readonly=True))

    address = exported(
        TextLine(
            title=_('The email address for this proposal.'),
            readonly=True,
            description=_('Any emails sent to this address will result'
                          'in comments being added.')))

    @operation_parameters(
        id=Int(
            title=_("A CodeReviewComment ID.")))
    @operation_returns_entry(Interface) # ICodeReviewComment
    @export_read_operation()
    def getComment(id):
        """Return the CodeReviewComment with the specified ID."""

    def getVoteReference(id):
        """Return the CodeReviewVoteReference with the specified ID."""

    def getNotificationRecipients(min_level):
        """Return the people who should be notified.

        Recipients will be returned as a dictionary where the key is the
        person, and the values are (subscription, rationale) tuples.

        :param min_level: The minimum notification level needed to be
            notified.
        """


    # Cannot specify value type without creating a circular dependency
    votes = exported(
        CollectionField(
            title=_('The votes cast or expected for this proposal'),
            value_type=Reference(schema=Interface), #ICodeReviewVoteReference
            readonly=True
            )
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

    @operation_parameters(
        reviewer=Reference(
            title=_("A person for which the reviewer status is in question."),
            schema=IPerson))
    @export_read_operation()
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

    @operation_parameters(
        reviewer=Reference(
            title=_("A reviewer."), schema=IPerson),
        review_type=Text())
    @call_with(registrant=REQUEST_USER)
    @export_write_operation()
    def nominateReviewer(reviewer, registrant, review_type=None):
        """Set the specified person as a reviewer.

        If they are not already a reviewer, a vote is created.  Otherwise,
        the details are updated.
        """

    def getUsersVoteReference(user):
        """Get the existing vote reference for the given user.

        :return: A `CodeReviewVoteReference` or None.
        """

    @operation_parameters(
        subject=Text(), content=Text(),
        vote=Choice(vocabulary='CodeReviewVote'), review_type=Text(),
        parent=Reference(schema=Interface))
    @call_with(owner=REQUEST_USER)
    @export_write_operation()
    def createComment(owner, subject, content=None, vote=None,
                      review_type=None, parent=None):
        """Create an ICodeReviewComment associated with this merge proposal.

        :param owner: The person who the message is from.
        :param subject: The subject line to use for the message.
        :param content: The text to use for the message content.  If
            unspecified, the text of the merge proposal is used.
        :param parent: The previous CodeReviewComment in the thread.  If
            unspecified, the root message is used.
        """

    def createCommentFromMessage(message, vote, review_type,
                                 original_email=None):
        """Create an `ICodeReviewComment` from an IMessage.

        :param message: The IMessage to use.
        :param vote: A CodeReviewVote (or None).
        :param review_type: A string (or None).
        :param original_email: Optional original email message.
        """

    def deleteProposal():
        """Delete the proposal to merge."""

    @operation_parameters(
        diff_content=Bytes(), diff_stat=Text(),
        source_revision_id=TextLine(), target_revision_id=TextLine(),
        dependent_revision_id=TextLine(), conflicts=Text())
    @export_write_operation()
    def updatePreviewDiff(diff_content, diff_stat,
                        source_revision_id, target_revision_id,
                        dependent_revision_id=None, conflicts=None):
        """Update the preview diff for this proposal.

        If there is not an existing preview diff, one will be created.

        :param diff_content: The raw bytes of the diff content to be put in
            the librarian.
        :param diff_stat: Text describing the files added, remove or modified.
        :param source_revision_id: The revision id that was used from the
            source branch.
        :param target_revision_id: The revision id that was used from the
            target branch.
        :param dependent_revision_id: The revision id that was used from the
            dependent branch.
        :param conflicts: Text describing the conflicts if any.
        """


class IBranchMergeProposalJob(Interface):
    """A Job related to a Branch Merge Proposal."""

    branch_merge_proposal = Object(
        title=_('The BranchMergeProposal this job is about'),
        schema=IBranchMergeProposal, required=True)

    job = Object(title=_('The common Job attributes'), schema=IJob,
        required=True)

    metadata = Attribute('A dict of data about the job.')

    def destroySelf():
        """Destroy this object."""


class IBranchMergeProposalListingBatchNavigator(ITableBatchNavigator):
    """A marker interface for registering the appropriate listings."""


class IBranchMergeProposalGetter(Interface):
    """Utility for getting BranchMergeProposals."""

    def get(id):
        """Return the BranchMergeProposal with specified id."""

    def getProposalsForContext(context, status=None, visible_by_user=None):
        """Return BranchMergeProposals associated with the context.

        :param context: Either an `IPerson` or `IProduct`.
        :param status: An iterable of queue_status of the proposals to return.
            If None is specified, all the proposals of all possible states
            are returned.
        :param visible_by_user: If a person is not supplied, only merge
            proposals based on public branches are returned.  If a person is
            supplied, merge proposals based on both public branches, and the
            private branches that the person is entitled to see are returned.
            Private branches are only visible to the owner and subscribers of
            the branch, and to LP admins.
        :raises BadBranchMergeProposalSearchContext: If the context is not
            understood.
        """

    def getVotesForProposals(proposals):
        """Return a dict containing a mapping of proposals to vote references.

        The values of the dict are lists of CodeReviewVoteReference objects.
        """

    def getVoteSummariesForProposals(proposals):
        """Return the vote summaries for the proposals.

        A vote summary is a dict has a 'comment_count' and may also have
        values for each of the CodeReviewVote enumerated values.

        :return: A dict keyed on the proposals.
        """

for name in ['supersedes', 'superseded_by']:
    IBranchMergeProposal[name].schema = IBranchMergeProposal


class ICreateMergeProposalJob(Interface):
    """A Job that creates a branch merge proposal.

    It uses a Message, which must contain a merge directive.
    """

    def run():
        """Run this job and create the merge proposals."""


class ICreateMergeProposalJobSource(Interface):
    """Acquire MergeProposalJobs."""

    def create(message_bytes):
        """Return a CreateMergeProposalJob for this message."""

    def iterReady():
        """Iterate through jobs that are ready to run."""


class IMergeProposalCreatedJob(Interface):
    """Interface for review diffs."""

    def run():
        """Perform the diff and email specified by this job."""


class IMergeProposalCreatedJobSource(Interface):
    """Interface for acquiring MergeProposalCreatedJobs."""

    def create(bmp):
        """Create a MergeProposalCreatedJob for the specified Job."""

    def iterReady():
        """Iterate through all ready MergeProposalCreatedJobs."""
