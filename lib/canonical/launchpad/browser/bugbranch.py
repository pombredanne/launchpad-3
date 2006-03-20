# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes for BugBranch-related objects."""

__metaclass__ = type
__all__ = ["BugBranchAddView"]

from canonical.launchpad.webapp import canonical_url

class BugBranchAddView:
    """Browser view for linking a bug to a branch."""
    def process(self, branch, comment):
        bug = self.context.bug

        bug.addBranch(branch)

        if comment:
            bug.newMessage(
                owner=self.user, content=comment,
                publish_create_event=False)

        self.request.response.addNotification(
            "Successfully registered branch %s for this bug." %
            branch.name)

    def nextURL(self):
        return canonical_url(self.context)
