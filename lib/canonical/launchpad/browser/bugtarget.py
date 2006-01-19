# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTarget-related browser views."""

__metaclass__ = type

__all__ = ["FileBugView"]

from zope.component import getUtility

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import ILaunchBag, IDistribution
from canonical.launchpad.browser.addview import SQLObjectAddView

class FileBugView(SQLObjectAddView):
    """Browser view for filebug forms.

    This class handles bugs filed on an IBugTarget, and the 'generic' bug
    filing, where a distribution argument is passed with the form.
    """

    def create(self, title=None, comment=None, private=False,
               packagename=None, distribution=None):
        """Add a bug to this IBugTarget."""
        current_user = getUtility(ILaunchBag).user
        context = self.context
        if distribution is not None:
            # We're being called from the generic bug filing form, so manually
            # set the chosen distribution as the context.
            context = distribution

        if IDistribution.providedBy(context) and packagename:
            # We don't know if the package name we got was a source or binary
            # package name, so let the Soyuz API figure it out for us.
            sourcepackagename, binarypackagename = (
                context.getPackageNames(str(packagename.name)))

            bugtarget = context.getSourcePackage(sourcepackagename.name)
            bug = bugtarget.createBug(
                title=title, comment=comment, private=private, owner=current_user,
                binarypackagename=binarypackagename)
        else:
            bug = context.createBug(
                title=title, comment=comment, private=private, owner=current_user)

        self.addedBug = bug
        return self.addedBug

    def nextURL(self):
        # Give the user some feedback on the bug just opened.
        self.request.response.addNotification("Thank you for your bug report.")

        task = self.addedBug.bugtasks[0]
        return canonical_url(task)
