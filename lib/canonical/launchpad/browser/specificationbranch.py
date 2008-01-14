# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Specification views."""

__metaclass__ = type

__all__ = [
    'SpecificationBranchStatusView',
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

    next_url = None

    @action(_('Change Summary'), name='change')
    def change_action(self, action, data):
        self.next_url = canonical_url(self.context.specification)
        self.updateContextFromData(data)

    @action(_('Delete Link'), name='delete')
    def delete_action(self, action, data):
        self.next_url = canonical_url(self.context.specification)
        self.context.destroySelf()


