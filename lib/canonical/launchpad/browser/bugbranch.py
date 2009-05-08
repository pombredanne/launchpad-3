# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes for BugBranch-related objects."""

__metaclass__ = type
__all__ = [
    'BranchLinkToBugView',
    'BugBranchAddView',
    'BugBranchBranchInlineEditView',
    'BugBranchBugInlineEditView',
    'BugBranchEditView',
    'BugBranchPrimaryContext',
    ]

from zope.event import notify
from zope.interface import implements

from lazr.lifecycle.event import ObjectDeletedEvent

from canonical.launchpad import _
from canonical.launchpad.interfaces import IBugBranch
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
        self.context.bug.addBranch(
            branch=branch, registrant=self.user)
        self.request.response.addNotification(
            "Successfully registered branch %s for this bug." %
            branch.name)

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url


class BugBranchEditView(LaunchpadEditFormView):
    """View to update a BugBranch."""
    schema = IBugBranch

    field_names = ['branch', 'bug',]

    custom_widget('branch', LinkWidget)
    custom_widget('bug', LinkWidget)

    def initialize(self):
        self.bug = self.context.bug
        super(BugBranchEditView, self).initialize()

    @property
    def next_url(self):
        return canonical_url(self.bug)

    @action('Delete', name='delete')
    def delete_action(self, action, data):
        self.context.bug.removeBranch(self.context.branch, self.user)


class BugBranchBranchInlineEditView(BugBranchEditView):
    """Inline edit view for bug branch details."""
    schema = IBugBranch
    field_names = []
    initial_focus_widget = None

    def initialize(self):
        self.branch = self.context.branch
        super(BugBranchBranchInlineEditView, self).initialize()

    @property
    def prefix(self):
        return "field%s" % self.context.id

    @property
    def action_url(self):
        return "%s/+branch-edit" % canonical_url(self.context)

    @property
    def next_url(self):
        return canonical_url(self.branch)


class BugBranchBugInlineEditView(BugBranchEditView):
    """Inline edit view for bug branch details."""
    schema = IBugBranch
    field_names = []
    initial_focus_widget = None

    @property
    def prefix(self):
        return "field%s" % self.context.id

    @property
    def action_url(self):
        return "%s/+bug-edit" % canonical_url(self.context)


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
        bug_branch = bug.addBranch(
            branch=self.context, registrant=self.user)

    @action(_('Cancel'), name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the branch page."""

    def validate(self, data):
        """Make sure that this bug isn't already linked to the branch."""
        if 'bug' not in data:
            return

        link_bug = data['bug']
        for bug in self.context.related_bugs:
            if bug == link_bug:
                self.setFieldError(
                    'bug',
                    'Bug #%s is already linked to this branch' % bug.id)
