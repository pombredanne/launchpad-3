# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes for BugBranch-related objects."""

__metaclass__ = type
__all__ = [
    "BugBranchAddView",
    "BugBranchStatusView"]

from zope.app.form.interfaces import IInputWidget, IDisplayWidget
from zope.app.form.utility import setUpWidgets

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.helpers import check_permission

class BugBranchAddView:
    """Browser view for linking a bug to a branch."""
    def process(self, branch, whiteboard):
        bug = self.context.bug

        bug.addBranch(branch, whiteboard)

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
        if check_permission("launchpad.Edit", self.context):
            interface = IInputWidget
        else:
            interface = IDisplayWidget

        setUpWidgets(
            self, self.schema, interface, names=self.fieldNames,
            initial=self.initial_values)

    def process(self, status, whiteboard):
        bug_branch = self.context
        if ((status != bug_branch.status) or
            (whiteboard != bug_branch.whiteboard)):
            bug_branch.status = status
            bug_branch.whiteboard = whiteboard

            self.request.response.addNotification(
                "Successfully updated branch status.")

    def nextURL(self):
        return canonical_url(self.context.bug)
