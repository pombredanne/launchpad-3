# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Specification views."""

__metaclass__ = type

__all__ = [
    'BranchLinkToSpecView',
    'SpecificationBranchStatusView',
    'SpecificationBranchBranchInlineEditView',
    ]

from canonical.launchpad import _
from canonical.launchpad.interfaces import ISpecificationBranch
from canonical.launchpad.webapp import (
    action,
    canonical_url,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )


class SpecificationBranchStatusView(LaunchpadEditFormView):
    """Edit the summary of the SpecificationBranch link."""

    schema = ISpecificationBranch
    field_names = ['summary']
    label = _('Edit specification branch summary')

    def initialize(self):
        self.specification = self.context.specification
        super(SpecificationBranchStatusView, self).initialize()

    @property
    def next_url(self):
        return canonical_url(self.specification)

    @action(_('Change Summary'), name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @action(_('Delete Link'), name='delete')
    def delete_action(self, action, data):
        self.context.destroySelf()


class SpecificationBranchBranchInlineEditView(SpecificationBranchStatusView):
    """Inline edit view for specification branch details."""

    initial_focus_widget = None
    label = None

    def initialize(self):
        self.branch = self.context.branch
        super(SpecificationBranchBranchInlineEditView, self).initialize()

    @property
    def prefix(self):
        return "field%s" % self.context.id

    @property
    def action_url(self):
        return "%s/+branch-edit" % canonical_url(self.context)

    @property
    def next_url(self):
        return canonical_url(self.branch)


class BranchLinkToSpecView(LaunchpadFormView):
    """The view to create spec-branch links."""

    schema = ISpecificationBranch
    # In order to have the bug field rendered using the appropriate
    # widget, we set the LaunchpadFormView attribute for_input to True
    # to get the read only fields rendered as input widgets.
    for_input=True

    field_names = ['specification', 'summary']

    @action('Link', name='link')
    def link_action(self, action, data):
        spec = data['specification']
        spec_branch = spec.linkBranch(
            branch=self.context, summary=data['summary'],
            registrant=self.user)
        self.next_url = canonical_url(self.context)

    def validate(self, data):
        """Make sure that this bug isn't already linked to the branch."""
        if 'specification' not in data:
            return

        link_spec = data['specification']
        for link in self.context.spec_links:
            if link.specification == link_spec:
                self.setFieldError(
                    'specification',
                    'The blueprint "%s" is already linked to this branch'
                    % link_spec.name)
