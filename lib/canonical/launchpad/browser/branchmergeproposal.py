# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Views, navigation and actions for BranchMergeProposals."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalSOP',
    'BranchMergeProposalContextMenu',
    'BranchMergeProposalEditView',
    'BranchMergeProposalMergedView',
    'BranchMergeProposalRequestReviewView',
    'ReviewBranchMergeProposalView',
    ]

from zope.component import getUtility
from zope.interface import Attribute, Interface
from zope.schema import Choice, Int

from canonical.cachedproperty import cachedproperty
from canonical.config import config

from canonical.launchpad import _
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.interfaces import (
    BranchMergeProposalStatus, BranchType, IBranchMergeProposal,
    ILaunchpadCelebrities, IStructuralObjectPresentation)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, stepto, stepthrough, LaunchpadFormView,
    LaunchpadEditFormView, action, custom_widget)
from canonical.widgets.link import LinkWidget

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
    links = ['request_review', 'review', 'merge']

    @enabled_with_permission('launchpad.Edit')
    def request_review(self):
        text = 'Request review'
        # Enable the review option if the proposal is not merged nor already
        # in the needs review state.
        enabled = self.context.queue_status not in (
            BranchMergeProposalStatus.MERGED,
            BranchMergeProposalStatus.NEEDS_REVIEW)
        return Link('+request-review', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def review(self):
        text = 'Review proposal'
        # Enable the review option if the proposal is reviewable, and the
        # user is a reviewer.
        lp_admins = getUtility(ILaunchpadCelebrities).admin
        valid_reviewer = (self.context.personCanReview(self.user) or
                          self.user.inTeam(lp_admins))
        enabled = self.context.isReviewable() and valid_reviewer
        return Link('+review', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def merge(self):
        text = 'Mark as merged'
        return Link('+merged', text, icon='edit')


class BranchMergeProposalRequestReviewView(LaunchpadEditFormView):
    """The view used to request a review of the merge proposal."""

    schema = IBranchMergeProposal
    field_names = []
    label = "Request review"

    @property
    def next_url(self):
        return canonical_url(self.context.source_branch)

    @action('Request review', name='review')
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
        description=_("The revision number on the target branch which "
                      "has been reviewed."))

class MergeProposalEditView(LaunchpadEditFormView):
    """A base class for merge proposal edit views."""

    @cachedproperty
    def reviewed_revision_number(self):
        """Return the number of the last reviewed revision.

        If there was no last reviewed revision, None is returned.

        If the reviewed revision is no longer in the revision history of
        the source branch, then a message is returned.
        """
        # If the source branch is REMOTE, then there won't be any ids.
        source_branch = self.context.source_branch
        if source_branch.branch_type == BranchType.REMOTE:
            return self.context.reviewed_revision_id
        else:
            branch_revision = source_branch.getBranchRevisionByRevisionId(
                self.context.reviewed_revision_id)
            if branch_revision is None:
                return "no longer in the source branch."
            elif branch_revision.sequence is None:
                return (
                    "no longer in the revision history of the source branch.")
            else:
                return branch_revision.sequence


class ReviewBranchMergeProposalView(MergeProposalEditView):
    """The view to approve or reject a merge proposal."""

    schema = ReviewForm
    label = "Review proposal to merge"

    @property
    def initial_values(self):
        # Default to reviewing the tip of the source branch.
        return {'revision_number': self.context.source_branch.revision_count}

    @cachedproperty
    def unlanded_revisions(self):
        """Return the unlanded revisions from the source branch."""
        return self.context.getUnlandedSourceBranchRevisions()

    @property
    def adapters(self):
        return {ReviewForm: self.context}

    @property
    def next_url(self):
        return canonical_url(self.context.source_branch)

    def _getRevisionId(self, data):
        """Translate the revision number that was entered into a revision id.

        If the branch is REMOTE we won't have any scanned revisions to compare
        against, so store the raw integer revision number as the revision id.
        """
        source_branch = self.context.source_branch
        if source_branch.branch_type == BranchType.REMOTE:
            return data['revision_number']
        else:
            branch_revision = source_branch.getBranchRevision(
                data['revision_number'])
            return branch_revision.revision.revision_id

    @action('Approve', name='approve')
    def approve_action(self, action, data):
        """Set the status to approved."""
        self.context.approveBranch(self.user, self._getRevisionId(data))

    @action('Reject', name='reject')
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
        # Check to make sure that the revision number entered is valid.
        rev_no = data.get('revision_number')
        if rev_no is not None:
            try:
                rev_no = int(rev_no)
            except ValueError:
                self.setFieldError(
                    'revision_number',
                    'The reviewed revision must be a positive number.')
            else:
                if rev_no < 1:
                    self.setFieldError(
                        'revision_number',
                        'The reviewed revision must be a positive number.')
                # Accept any positive integer for a REMOTE branch.
                source_branch = self.context.source_branch
                if (source_branch.branch_type != BranchType.REMOTE and
                    rev_no > source_branch.revision_count):
                    self.setFieldError(
                        'revision_number',
                        'The reviewed revision cannot be larger than the '
                        'tip revision of the source branch.')

    @property
    def codebrowse_url(self):
        """Return the link to codebrowse for this branch."""
        return (config.codehosting.codebrowse_root +
                self.context.source_branch.unique_name)


class BranchMergeProposalEditView(MergeProposalEditView):
    """The view to control the editing and deletion of merge proposals."""
    schema = IBranchMergeProposal
    label = "Edit branch merge proposal"
    field_names = ["whiteboard"]

    def initialize(self):
        # Store the source branch for `next_url` to make sure that
        # it is available in the situation where the merge proposal
        # is deleted.
        self.source_branch = self.context.source_branch
        super(BranchMergeProposalEditView, self).initialize()

    @property
    def next_url(self):
        return canonical_url(self.source_branch)

    @action('Update', name='update')
    def update_action(self, action, data):
        """Update the whiteboard and go back to the source branch."""
        self.updateContextFromData(data)

    @action('Delete', name='delete')
    def delete_action(self, action, data):
        """Delete the merge proposal and go back to the source branch."""
        self.context.destroySelf()

    @action('Cancel', name='cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""


class BranchMergeProposalMergedView(LaunchpadEditFormView):
    """The view to mark a merge proposal as merged."""
    schema = IBranchMergeProposal
    label = "Edit branch merge proposal"
    field_names = ["merged_revno"]

    @action('Mark as Merged', name='mark_merged')
    def mark_merged_action(self, action, data):
        """Update the whiteboard and go back to the source branch."""
        revno = data['merged_revno']
        self.context.markAsMerged(revno, merge_reporter=self.user)
        # Now go back to the source branch.
        self.next_url = canonical_url(self.context.source_branch)

    @action('Cancel', name='cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the merge proposal."""
        self.next_url = canonical_url(self.context)

    def validate(self, data):
        # Ensure a positive integer value.
        revno = data.get('merged_revno')
        if revno is not None:
            if revno <= 0:
                self.setFieldError(
                    'merged_revno',
                    'Revision numbers must be positive integers.')
