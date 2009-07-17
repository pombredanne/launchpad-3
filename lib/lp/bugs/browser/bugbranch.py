# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser view classes for BugBranch-related objects."""

__metaclass__ = type
__all__ = [
    'BranchLinkToBugView',
    'BugBranchAddView',
    'BugBranchDeleteView',
    'BugBranchPrimaryContext',
    ]

from zope.event import notify
from zope.interface import implements

from lazr.lifecycle.event import ObjectDeletedEvent

from canonical.launchpad import _
from lp.bugs.interfaces.bugbranch import IBugBranch
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadEditFormView,
    LaunchpadFormView)
from canonical.launchpad.webapp.interfaces import IPrimaryContext

from canonical.widgets.link import LinkWidget


class BugBranchPrimaryContext:
    """The primary context is the bug branch link is that of the branch."""

    implements(IPrimaryContext)

    def __init__(self, bug_branch):
        self.context = IPrimaryContext(bug_branch.branch).context


class BugBranchAddView(LaunchpadFormView):
    """Browser view for linking a bug to a branch."""
    schema = IBugBranch
    # In order to have the branch field rendered using the appropriate
    # widget, we set the LaunchpadFormView attribute for_input to True
    # to get the read only fields rendered as input widgets.
    for_input = True

    field_names = ['branch']

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        branch = data['branch']
        self.context.bug.linkBranch(
            branch=branch, registrant=self.user)
        self.request.response.addNotification(
            "Successfully registered branch %s for this bug." %
            branch.name)

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url


class BugBranchDeleteView(LaunchpadEditFormView):
    """View to update a BugBranch."""
    schema = IBugBranch

    field_names = []

    def initialize(self):
        LaunchpadEditFormView.initialize(self)

    @property
    def next_url(self):
        return canonical_url(self.context.bug)

    cancel_url = next_url

    @action('Delete', name='delete')
    def delete_action(self, action, data):
        self.context.bug.unlinkBranch(self.context.branch, self.user)


class BranchLinkToBugView(LaunchpadFormView):
    """The view to create bug-branch links."""
    schema = IBugBranch
    # In order to have the bug field rendered using the appropriate
    # widget, we set the LaunchpadFormView attribute for_input to True
    # to get the read only fields rendered as input widgets.
    for_input = True

    field_names = ['bug']

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        bug = data['bug']
        bug_branch = bug.linkBranch(
            branch=self.context, registrant=self.user)

    @action(_('Cancel'), name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the branch page."""

    def validate(self, data):
        """Make sure that this bug isn't already linked to the branch."""
        if 'bug' not in data:
            return

        link_bug = data['bug']
