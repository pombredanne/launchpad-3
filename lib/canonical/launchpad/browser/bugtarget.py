# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTarget-related browser views."""

__metaclass__ = type

__all__ = ["FileBugView"]

from zope.component import getUtility

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    ILaunchBag, IDistribution, IBinaryPackageName, ISourcePackageName)
from canonical.launchpad.browser.addview import SQLObjectAddView

class FileBugView(SQLObjectAddView):
    """The view class that handles filing a bug on an IBugTarget."""

    def create(self, title=None, comment=None, private=False,
               packagename=None):
        """Add a bug to this IBugTarget."""
        current_user = getUtility(ILaunchBag).user

        if IDistribution.providedBy(self.context) and packagename:
            # We don't know if the package name we got was a source or binary
            # package name, so let the Soyuz API figure it out for us.
            sourcepackagename, binarypackagename = (
                self.context.getPackageNames(str(packagename.name)))

            bugtarget = self.context.getSourcePackage(sourcepackagename.name)
            bug = bugtarget.createBug(
                title=title, comment=comment, private=private, owner=current_user,
                binarypackagename=binarypackagename)
        else:
            bug = self.context.createBug(
                title=title, comment=comment, private=private, owner=current_user)

        self.addedBug = bug
        return self.addedBug

    def nextURL(self):
        # Give the user some feedback on the bug just opened.
        self.request.response.addNotification("Thank you for your bug report.")

        task = self.addedBug.bugtasks[0]
        return canonical_url(task)
