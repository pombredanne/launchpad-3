# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTarget-related browser views."""

__metaclass__ = type

__all__ = ["FileBugView"]

from zope.component import getUtility

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    ILaunchBag, IDistribution)
from canonical.launchpad.browser.addview import SQLObjectAddView

class FileBugView(SQLObjectAddView):
    """The view class that handles filing a bug on an IBugTarget."""

    def create(self, title=None, comment=None, private=False,
               sourcepackagename=None):
        """Add a bug to this IBugTarget."""
        current_user = getUtility(ILaunchBag).user

        if IDistribution.providedBy(self.context) and sourcepackagename:
            # This is a bug filed on a distribution, but a specific package name
            # was provided, so let's get a reference to that package as the bug
            # target.
            bugtarget = self.context.getSourcePackage(sourcepackagename)
        else:
            bugtarget = self.context

        bug = bugtarget.createBug(
            title=title, comment=comment, private=private, owner=current_user)

        self.addedBug = bug
        return self.addedBug

    def nextURL(self):
        task = self.addedBug.bugtasks[0]
        return canonical_url(task)
