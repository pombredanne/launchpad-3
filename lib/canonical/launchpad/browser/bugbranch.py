# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes for BugBranch-related objects."""

__metaclass__ = type
__all__ = [
    "BranchLinkToBugView",
    "BugBranchAddView",
    "BugBranchStatusView",
    ]

from zope.app.form.interfaces import IInputWidget, IDisplayWidget
from zope.app.form.utility import setUpWidgets
from zope.event import notify

from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.interfaces import IBugBranch
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView)
from canonical.launchpad.webapp.snapshot import Snapshot
from canonical.launchpad.webapp.authorization import check_permission


class BugBranchAddView:
    """Browser view for linking a bug to a branch."""

    def process(self, branch, whiteboard):
        self.context.bug.addBranch(branch, whiteboard)

        self.request.response.addNotification(
            "Successfully registered branch %s for this bug." %
            branch.name)

    def nextURL(self):
        return canonical_url(self.context)


class BugBranchStatusView:
    """Browser view for editing branch status."""

    @property
    def initial_values(self):
        return {
            'status': self.context.status,
            'whiteboard': self.context.whiteboard}

    def _setUpWidgets(self):
        # The same form is reused for both viewing and editing the
        # branch, so render the form with edit widgets when the user
        # can edit the form values, otherwise render a read-only form.
        #
        # XXX, Brad Bollenbach, 2006-03-21: When Zope 3.2 lands, this
        # form should be redone if the new form machinery can make it
        # simpler.
        if check_permission("launchpad.Edit", self.context):
            interface = IInputWidget
        else:
            interface = IDisplayWidget

        setUpWidgets(
            self, self.schema, interface, names=self.fieldNames,
            initial=self.initial_values)

    def process(self, status, whiteboard):
        bug_branch = self.context
        bug_branch_before_modification = Snapshot(
            bug_branch, providing=IBugBranch)

        # If either field has changed, update both for simplicity.
        if ((status != bug_branch.status) or
            (whiteboard != bug_branch.whiteboard)):
            bug_branch.status = status
            bug_branch.whiteboard = whiteboard

            bug_branch_changed = SQLObjectModifiedEvent(
                bug_branch, bug_branch_before_modification,
                ["status", "whiteboard"])

            notify(bug_branch_changed)

            self.request.response.addNotification(
                "Successfully updated branch status.")

    def nextURL(self):
        return canonical_url(self.context.bug)


class BranchLinkToBugView(LaunchpadFormView):
    """The view to create bug-branch links."""
    schema = IBugBranch
    # In order to have the bug field rendered using the appropriate
    # widget, we set the LaunchpadFormView attribute for_input to True
    # to get the read only fields rendered as input widgets.
    for_input=True

    field_names = ['bug', 'status', 'whiteboard']

    @action('Link', name='link')
    def link_action(self, action, data):
        bug = data['bug']
        bug_branch = bug.addBranch(
            branch=self.context, whiteboard=data['whiteboard'],
            status=data['status'])
        self.next_url = canonical_url(self.context)

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
