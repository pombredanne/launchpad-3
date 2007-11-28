# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Views, navigation and actions for BranchMergeProposals."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalSOP',
    'BranchMergeProposalContextMenu',
    'BranchMergeProposalEditView',
    'BranchMergeProposalMergedView',
    ]

from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.interfaces import (
    IBranchMergeProposal, IStructuralObjectPresentation)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, stepto, stepthrough, LaunchpadFormView,
    LaunchpadEditFormView, action, custom_widget)


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
    links = ['merge']

    @enabled_with_permission('launchpad.Edit')
    def merge(self):
        text = 'Mark as merged'
        return Link('+merged', text, icon='edit')


class BranchMergeProposalEditView(LaunchpadEditFormView):
    """The view to control the editing and deletion of merge proposals."""
    schema = IBranchMergeProposal

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
