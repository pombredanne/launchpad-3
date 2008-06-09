# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0322

"""Views, navigation and actions for BranchMergeProposals."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalSOP',
    'BranchMergeProposalContextMenu',
    'BranchMergeProposalDeleteView',
    'BranchMergeProposalDequeueView',
    'BranchMergeProposalEditView',
    'BranchMergeProposalEnqueueView',
    'BranchMergeProposalInlineDequeueView',
    'BranchMergeProposalJumpQueueView',
    'BranchMergeProposalNavigation',
    'BranchMergeProposalMergedView',
    'BranchMergeProposalRequestReviewView',
    'BranchMergeProposalResubmitView',
    'BranchMergeProposalReviewView',
    'BranchMergeProposalView',
    'BranchMergeProposalWorkInProgressView',
    ]

from zope.component import getUtility
from zope.event import notify as zope_notify
from zope.formlib import form
from zope.interface import Interface
from zope.schema import Int

from canonical.cachedproperty import cachedproperty
from canonical.config import config

from canonical.launchpad import _
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.fields import Summary, Whiteboard
from canonical.launchpad.interfaces import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES,
    BranchMergeProposalStatus,
    BranchType,
    IBranchMergeProposal,
    IMessageSet,
    IStructuralObjectPresentation,
    WrongBranchMergeProposal)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadEditFormView, LaunchpadView, action, stepthrough, Navigation)
from canonical.launchpad.webapp.authorization import check_permission


def notify(func):
    """Decorate a view method to send a notification."""
    def decorator(view, *args, **kwargs):
        snapshot = BranchMergeProposalDelta.snapshot(view.context)
        result = func(view, *args, **kwargs)
        zope_notify(SQLObjectModifiedEvent(view.context, snapshot, []))
        return result
    return decorator


def update_and_notify(func):
    """Decorate an action to update from a form and send a notification."""
    @notify
    def decorator(view, action, data):
        result = func(view, action, data)
        form.applyChanges(
            view.context, view.form_fields, data, view.adapters)
        return result
    return decorator


class BranchMergeProposalSOP(StructuralObjectPresentation):
    """Provides the structural heading for `IBranchMergeProposal`.

    Delegates the method calls to the SOP of the source branch.
    """
    def __init__(self, context):
        StructuralObjectPresentation.__init__(self, context)
        self.delegate = IStructuralObjectPresentation(
            self.context.source_branch)

    def getIntroHeading(self):
        """See `IStructuralHeaderPresentation`."""
        return self.delegate.getIntroHeading()

    def getMainHeading(self):
        """See `IStructuralHeaderPresentation`."""
        return self.delegate.getMainHeading()


class BranchMergeProposalContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = IBranchMergeProposal
    links = ['edit', 'delete', 'set_work_in_progress', 'request_review',
             'review', 'merge', 'enqueue', 'dequeue', 'resubmit']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Edit details'
        status = self.context.queue_status
        enabled = status not in BRANCH_MERGE_PROPOSAL_FINAL_STATES
        return Link('+edit', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def delete(self):
        text = 'Delete proposal to merge'
        return Link('+delete', text, icon='edit')

    def _enabledForStatus(self, next_state):
        """True if the next_state is a valid transition for the current user.

        Return False if the current state is next_state.
        """
        status = self.context.queue_status
        if status == next_state:
            return False
        else:
            return self.context.isValidTransition(next_state, self.user)

    @enabled_with_permission('launchpad.Edit')
    def set_work_in_progress(self):
        text = 'Work in progress'
        enabled = self._enabledForStatus(
            BranchMergeProposalStatus.WORK_IN_PROGRESS)
        return Link('+work-in-progress', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def request_review(self):
        text = 'Request review'
        enabled = self._enabledForStatus(
            BranchMergeProposalStatus.NEEDS_REVIEW)
        return Link('+request-review', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def review(self):
        text = 'Review proposal'
        enabled = self._enabledForStatus(
            BranchMergeProposalStatus.CODE_APPROVED)
        return Link('+review', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def merge(self):
        text = 'Mark as merged'
        enabled = self._enabledForStatus(
            BranchMergeProposalStatus.MERGED)
        return Link('+merged', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def enqueue(self):
        text = 'Queue for merging'
        enabled = self._enabledForStatus(
            BranchMergeProposalStatus.QUEUED)
        return Link('+enqueue', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def dequeue(self):
        text = 'Remove from queue'
        enabled = (self.context.queue_status ==
                   BranchMergeProposalStatus.QUEUED)
        return Link('+dequeue', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def resubmit(self):
        text = 'Resubmit proposal'
        enabled = self._enabledForStatus(
            BranchMergeProposalStatus.SUPERSEDED)
        return Link('+resubmit', text, icon='edit', enabled=enabled)


class UnmergedRevisionsMixin:
    """Provides the methods needed to show unmerged revisions."""

    @cachedproperty
    def unlanded_revisions(self):
        """Return the unlanded revisions from the source branch."""
        return self.context.getUnlandedSourceBranchRevisions()

    @property
    def codebrowse_url(self):
        """Return the link to codebrowse for this branch."""
        return (config.codehosting.codebrowse_root +
                self.context.source_branch.unique_name)


class BranchMergeProposalRevisionIdMixin:
    """A mixin class to provide access to the revision ids."""

    def _getRevisionNumberForRevisionId(self, revision_id):
        """Find the revision number that corresponds to the revision id.

        If there was no last reviewed revision, None is returned.

        If the reviewed revision is no longer in the revision history of
        the source branch, then a message is returned.
        """
        if revision_id is None:
            return None
        # If the source branch is REMOTE, then there won't be any ids.
        source_branch = self.context.source_branch
        if source_branch.branch_type == BranchType.REMOTE:
            return revision_id
        else:
            branch_revision = source_branch.getBranchRevisionByRevisionId(
                revision_id)
            if branch_revision is None:
                return "no longer in the source branch."
            elif branch_revision.sequence is None:
                return (
                    "no longer in the revision history of the source branch.")
            else:
                return branch_revision.sequence

    @cachedproperty
    def reviewed_revision_number(self):
        """Return the number of the reviewed revision."""
        return self._getRevisionNumberForRevisionId(
            self.context.reviewed_revision_id)

    @cachedproperty
    def queued_revision_number(self):
        """Return the number of the queued revision."""
        return self._getRevisionNumberForRevisionId(
            self.context.queued_revision_id)


class BranchMergeProposalNavigation(Navigation):
    """Navigation from BranchMergeProposal to CodeReviewComment views."""

    usedfor = IBranchMergeProposal

    @stepthrough('comments')
    def traverse_comment(self, id):
        try:
            id = int(id)
        except ValueError:
            return None
        try:
            return self.context.getComment(id)
        except WrongBranchMergeProposal:
            return None


class BranchMergeProposalView(LaunchpadView, UnmergedRevisionsMixin,
                              BranchMergeProposalRevisionIdMixin):
    """A basic view used for the index page."""

    label = "Proposal to merge branches"
    __used_for__ = IBranchMergeProposal

    @property
    def queue_location(self):
        """The location of the queue view."""
        # Will point to the target_branch queue, or the queue
        # with multiple targets if specified.
        return canonical_url(self.context.target_branch) + '/+merge-queue'

    @property
    def comment_location(self):
        """Location of page for commenting on this proposal."""
        return canonical_url(self.context, view_name='+comment')

    @property
    def comments(self):
        """Return comments associated with this proposal, plus styling info.

        Comments are in threaded order, and the style indicates indenting
        for use with threads.
        """
        message_to_comment = {}
        messages = []
        for comment in self.context.all_comments:
            message_to_comment[comment.message] = comment
            messages.append(comment.message)
        message_set = getUtility(IMessageSet)
        threads = message_set.threadMessages(messages)
        result = []
        for depth, message in message_set.flattenThreads(threads):
            comment = message_to_comment[message]
            style = 'margin-left: %dem;' % (2 * depth)
            result.append(dict(style=style, comment=comment))
        return result


class BranchMergeProposalWorkInProgressView(LaunchpadEditFormView):
    """The view used to set a proposal back to 'work in progress'."""

    schema = IBranchMergeProposal
    field_names = ["whiteboard"]
    label = "Set proposal as work in progress"

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action('Set as work in progress', name='wip')
    @notify
    def wip_action(self, action, data):
        """Set the status to 'Needs review'."""
        self.context.setAsWorkInProgress()
        self.updateContextFromData(data)

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""

    def validate(self, data):
        """Ensure that the proposal is in an appropriate state."""
        if self.context.queue_status == BranchMergeProposalStatus.MERGED:
            self.addError("The merge proposal is not an a valid state to "
                          "mark as 'Work in progress'.")


class BranchMergeProposalRequestReviewView(LaunchpadEditFormView):
    """The view used to request a review of the merge proposal."""

    schema = IBranchMergeProposal
    field_names = ["whiteboard"]
    label = "Request review"

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action('Request review', name='review')
    @update_and_notify
    def review_action(self, action, data):
        """Set the status to 'Needs review'."""
        self.context.requestReview()

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""

    def validate(self, data):
        """Ensure that the proposal is in an appropriate state."""
        if self.context.queue_status == BranchMergeProposalStatus.MERGED:
            self.addError("The merge proposal is not an a valid state to "
                          "mark as 'Needs review'.")


class ReviewForm(Interface):
    """A simple interface to define the revision number field."""

    revision_number = Int(
        title=_("Reviewed Revision"), required=True,
        description=_("The revision number on the source branch which "
                      "has been reviewed."))

    whiteboard = Whiteboard(
        title=_('Whiteboard'), required=False,
        description=_('Notes about the merge.'))


class MergeProposalEditView(LaunchpadEditFormView,
                            BranchMergeProposalRevisionIdMixin):
    """A base class for merge proposal edit views."""

    @property
    def next_url(self):
        # Since the property stops inherited classes from specifying
        # an explicit next_url, have this property look for a _next_url
        # and use that if found, and if one is not set, then use the
        # canonical_url of the context (the merge proposal itself) as
        # the default.
        return getattr(self, '_next_url', canonical_url(self.context))

    def _getRevisionId(self, data):
        """Translate the revision number that was entered into a revision id.

        If the branch is REMOTE we won't have any scanned revisions to compare
        against, so store the raw integer revision number as the revision id.
        """
        source_branch = self.context.source_branch
        # Get the revision number out of the data.
        if source_branch.branch_type == BranchType.REMOTE:
            return data.pop('revision_number')
        else:
            branch_revision = source_branch.getBranchRevision(
                data.pop('revision_number'))
            return branch_revision.revision.revision_id

    def _validateRevisionNumber(self, data, revision_name):
        """Check to make sure that the revision number entered is valid."""
        rev_no = data.get('revision_number')
        if rev_no is not None:
            try:
                rev_no = int(rev_no)
            except ValueError:
                self.setFieldError(
                    'revision_number',
                    'The %s revision must be a positive number.'
                    % revision_name)
            else:
                if rev_no < 1:
                    self.setFieldError(
                        'revision_number',
                        'The %s revision must be a positive number.'
                        % revision_name)
                # Accept any positive integer for a REMOTE branch.
                source_branch = self.context.source_branch
                if (source_branch.branch_type != BranchType.REMOTE and
                    rev_no > source_branch.revision_count):
                    self.setFieldError(
                        'revision_number',
                        'The %s revision cannot be larger than the '
                        'tip revision of the source branch.'
                        % revision_name)


class BranchMergeProposalResubmitView(MergeProposalEditView,
                                      UnmergedRevisionsMixin):
    """The view to resubmit a proposal to merge."""

    schema = IBranchMergeProposal
    label = "Resubmit proposal to merge"
    field_names = ["whiteboard"]

    @action('Resubmit', name='resubmit')
    @update_and_notify
    def resubmit_action(self, action, data):
        """Resubmit this proposal."""
        proposal = self.context.resubmit(self.user)
        self.request.response.addInfoNotification(_(
            "Please update the whiteboard for the new proposal."))
        self._next_url = canonical_url(proposal) + "/+edit"

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""
        self.next_url = canonical_url(self.context)


class BranchMergeProposalReviewView(MergeProposalEditView,
                                    UnmergedRevisionsMixin):
    """The view to approve or reject a merge proposal."""

    schema = ReviewForm
    label = "Review proposal to merge"

    @property
    def adapters(self):
        """See `LaunchpadFormView`"""
        return {ReviewForm: self.context}

    @property
    def initial_values(self):
        # Default to reviewing the tip of the source branch.
        return {'revision_number': self.context.source_branch.revision_count}

    @action('Approve', name='approve')
    @update_and_notify
    def approve_action(self, action, data):
        """Set the status to approved."""
        self.context.approveBranch(self.user, self._getRevisionId(data))

    @action('Reject', name='reject')
    @update_and_notify
    def reject_action(self, action, data):
        """Set the status to rejected."""
        self.context.rejectBranch(self.user, self._getRevisionId(data))

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""

    def validate(self, data):
        """Ensure that the proposal is in an appropriate state."""
        if self.context.queue_status == BranchMergeProposalStatus.MERGED:
            self.addError("The merge proposal is not an a valid state to "
                          "review.")
        self._validateRevisionNumber(data, 'reviewed')


class BranchMergeProposalEditView(MergeProposalEditView):
    """The view to control the editing of merge proposals."""
    schema = IBranchMergeProposal
    label = "Edit branch merge proposal"
    field_names = ["whiteboard"]

    @action('Update', name='update')
    def update_action(self, action, data):
        """Update the whiteboard and go back to the source branch."""
        self.updateContextFromData(data)

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""


class BranchMergeProposalDeleteView(MergeProposalEditView):
    """The view to control the deletion of merge proposals."""
    schema = IBranchMergeProposal
    label = "Delete branch merge proposal"
    field_names = []

    def initialize(self):
        # Store the source branch for `next_url` to make sure that
        # it is available in the situation where the merge proposal
        # is deleted.
        self.source_branch = self.context.source_branch
        super(BranchMergeProposalDeleteView, self).initialize()

    @action('Delete proposal', name='delete')
    def delete_action(self, action, data):
        """Delete the merge proposal and go back to the source branch."""
        self.context.deleteProposal()
        # Override the next url to be the source branch.
        self._next_url = canonical_url(self.source_branch)

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""


class BranchMergeProposalMergedView(LaunchpadEditFormView):
    """The view to mark a merge proposal as merged."""
    schema = IBranchMergeProposal
    label = "Edit branch merge proposal"
    field_names = ["merged_revno"]

    @property
    def initial_values(self):
        # Default to reviewing the tip of the source branch.
        return {'merged_revno': self.context.source_branch.revision_count}

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action('Mark as Merged', name='mark_merged')
    @notify
    def mark_merged_action(self, action, data):
        """Update the whiteboard and go back to the source branch."""
        if self.context.queue_status == BranchMergeProposalStatus.MERGED:
            self.request.response.addWarningNotification(
                'The proposal has already been marked as merged.')
        else:
            revno = data['merged_revno']
            self.context.markAsMerged(revno, merge_reporter=self.user)
            self.request.response.addNotification(
                'The proposal has now been marked as merged.')

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the merge proposal."""

    def validate(self, data):
        # Ensure a positive integer value.
        revno = data.get('merged_revno')
        if revno is not None:
            if revno <= 0:
                self.setFieldError(
                    'merged_revno',
                    'Revision numbers must be positive integers.')


class EnqueueForm(Interface):
    """A simple interface to populate the form to enqueue a proposal."""

    revision_number = Int(
        title=_("Queue Revision"), required=True,
        description=_("The revision number of the source branch "
                      "which is to be merged into the target branch."))

    commit_message = Summary(
        title=_("Commit Message"), required=True,
        description=_("The commit message to be used when merging "
                      "the source branch."))

    whiteboard = Whiteboard(
        title=_('Whiteboard'), required=False,
        description=_('Notes about the merge.'))


class BranchMergeProposalEnqueueView(MergeProposalEditView,
                                     UnmergedRevisionsMixin):
    """The view to submit a merge proposal for merging."""

    schema = EnqueueForm
    label = "Queue branch for merging"

    @property
    def initial_values(self):
        # If the user is a valid reviewer, then default the revision
        # number to be the tip.
        if self.context.isPersonValidReviewer(self.user):
            revision_number = self.context.source_branch.revision_count
        else:
            revision_number = self._getRevisionNumberForRevisionId(
                self.context.reviewed_revision_id)

        return {'revision_number': revision_number}

    @property
    def adapters(self):
        """See `LaunchpadFormView`"""
        return {EnqueueForm: self.context}

    def setUpFields(self):
        super(BranchMergeProposalEnqueueView, self).setUpFields()
        # If the user is not a valid reviewer for the target branch,
        # then the revision number should be read only, so an
        # untrusted user cannot land changes that have not bee reviewed.
        if not self.context.isPersonValidReviewer(self.user):
            self.form_fields['revision_number'].for_display = True

    @action('Enqueue', name='enqueue')
    @update_and_notify
    def enqueue_action(self, action, data):
        """Update the whiteboard and enqueue the merge proposal."""
        if self.context.isPersonValidReviewer(self.user):
            revision_id = self._getRevisionId(data)
        else:
            revision_id = self.context.reviewed_revision_id
        self.context.enqueue(self.user, revision_id)

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the merge proposal."""

    def validate(self, data):
        """Make sure that the proposal has been reviewed.

        Or that the logged in user is able to review the branch as well.
        """
        if not self.context.isValidTransition(
            BranchMergeProposalStatus.QUEUED, self.user):
            self.addError(
                "The merge proposal is cannot be queued as it has not "
                "been reviewed.")

        self._validateRevisionNumber(data, 'enqueued')


class BranchMergeProposalDequeueView(LaunchpadEditFormView):
    """The view to remove a merge proposal from the merge queue."""

    schema = IBranchMergeProposal
    field_names = ["whiteboard"]

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action('Dequeue', name='dequeue')
    @update_and_notify
    def dequeue_action(self, action, data):
        """Update the whiteboard and remove the proposal from the queue."""
        self.context.dequeue()

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the merge proposal."""

    def validate(self, data):
        """Make sure the proposal is queued before removing."""
        if self.context.queue_status != BranchMergeProposalStatus.QUEUED:
            self.addError("The merge proposal is not queued.")


class BranchMergeProposalInlineDequeueView(LaunchpadEditFormView):
    """The view to provide a 'dequeue' button to the queue view."""

    schema = IBranchMergeProposal
    field_names = []

    @property
    def next_url(self):
        return canonical_url(self.context.target_branch) + '/+merge-queue'

    @action('Dequeue', name='dequeue')
    @notify
    def dequeue_action(self, action, data):
        """Remove the proposal from the queue if queued."""
        if self.context.queue_status == BranchMergeProposalStatus.QUEUED:
            self.context.dequeue()

    @property
    def prefix(self):
        return "field%s" % self.context.id

    @property
    def action_url(self):
        return "%s/+dequeue-inline" % canonical_url(self.context)


class BranchMergeProposalJumpQueueView(LaunchpadEditFormView):
    """The view to provide a move the proposal to the front of the queue."""

    schema = IBranchMergeProposal
    field_names = []

    @property
    def next_url(self):
        return canonical_url(self.context.target_branch) + '/+merge-queue'

    @action('Move to front', name='move')
    @notify
    def move_action(self, action, data):
        """Move the proposal to the front of the queue (if queued)."""
        if (self.context.queue_status == BranchMergeProposalStatus.QUEUED and
            check_permission('launchpad.Edit', self.context.target_branch)):
            self.context.moveToFrontOfQueue()

    @property
    def prefix(self):
        return "field%s" % self.context.id

    @property
    def action_url(self):
        return "%s/+jump-queue" % canonical_url(self.context)
