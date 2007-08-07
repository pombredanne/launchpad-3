# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Views, navigation and actions for BranchMergeProposals."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalContextMenu',
    'BranchMergeProposalEditView',
    'BranchMergeProposalMergedView',
    ]

from canonical.launchpad.interfaces import IBranchMergeProposal
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, stepto, stepthrough, LaunchpadFormView,
    LaunchpadEditFormView, action, custom_widget)


class BranchMergeProposalContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = IBranchMergeProposal
    facet = 'branches'
    links = ['merge']

    @enabled_with_permission('launchpad.Edit')
    def merge(self):
        text = 'Mark as merged'
        return Link('+merged', text, icon='edit')


class BranchMergeProposalEditView(LaunchpadEditFormView):
    schema = IBranchMergeProposal

    field_names = ["whiteboard"]

    def initialize(self):
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
        self.source_branch.removeLandingTarget(
            self.context.target_branch)

    @action('Cancel', name='cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""


class BranchMergeProposalMergedView(LaunchpadEditFormView):
    schema = IBranchMergeProposal

    field_names = ["merged_revno"]

    def initialize(self):
        self.source_branch = self.context.source_branch
        super(BranchMergeProposalMergedView, self).initialize()

    @property
    def next_url(self):
        return canonical_url(self.source_branch)

    @action('Mark as Merged', name='mark_merged')
    def mark_merged_action(self, action, data):
        """Update the whiteboard and go back to the source branch."""
        revno = data['merged_revno']
        self.context.markAsMerged(revno)

    @action('Cancel', name='cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the source branch."""

    def validate(self, data):
        super(BranchMergeProposalMergedView, self).validate(data)
        # Ensure a positive integer value.
        revno = data.get('merged_revno')
        if revno is not None:
            if revno <= 0:
                self.setFieldError(
                    'merged_revno',
                    'Revision numbers must be positive integers.')
