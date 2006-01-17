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
            # If a binary package was selected create the bug with both the
            # binary and source package, otherwise create the bug with just the
            # source package.
            binarypackagename = None
            sourcepackagename = None
            if IBinaryPackageName.providedBy(packagename):
                distrorelease = self.context.currentrelease
                distrorelease_i386 = distrorelease['i386']
                i386_binarypackage = distrorelease_i386.getBinaryPackage(
                    packagename)
                i386_current_binarypackage = i386_binarypackage.currentrelease
                distro_sourcepackage_release = i386_current_binarypackage.distributionsourcepackagerelease
                sourcepackage = distro_sourcepackage_release.sourcepackage

                binarypackagename = packagename
                sourcepackagename = sourcepackage.sourcepackagename
            else:
                sourcepackagename = packagename

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
