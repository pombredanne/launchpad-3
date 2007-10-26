# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Specification views."""

__metaclass__ = type

__all__ = [
    'SpecificationBranchStatusView',
    'SpecificationBranchBranchInlineEditView',
    ]

from canonical.launchpad import _
from canonical.launchpad.interfaces import ISpecificationBranch
from canonical.launchpad.webapp import (
    LaunchpadEditFormView, action, canonical_url)


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
