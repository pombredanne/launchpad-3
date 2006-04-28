# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTarget-related browser views."""

__metaclass__ = type

__all__ = ["FileBugView"]

from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidgets
from zope.component import getUtility

from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.interfaces import (
    ILaunchBag, IDistribution, IProduct, NotFoundError)
from canonical.launchpad.webapp import canonical_url

class FileBugView(SQLObjectAddView):
    """Browser view for filebug forms.

    This class handles bugs filed on an IBugTarget, and the 'generic'
    bug filing, where a distribution argument is passed with the form.
    """

    notification = "Thank you for your bug report."

    def create(self, title=None, comment=None, private=False,
               packagename=None, distribution=None, security_related=False):
        """Add a bug to this IBugTarget."""
        current_user = getUtility(ILaunchBag).user
        context = self.context
        if distribution is not None:
            # We're being called from the generic bug filing form, so manually
            # set the chosen distribution as the context.
            context = distribution

        # Ensure that no package information is used, if the user
        # enters a package name but then selects "I don't know".
        if self.request.form.get("packagename_option") == "none":
            packagename = None

        if IDistribution.providedBy(context) and packagename:
            # We don't know if the package name we got was a source or binary
            # package name, so let the Soyuz API figure it out for us.
            packagename = str(packagename)
            try:
                sourcepackagename, binarypackagename = (
                    context.getPackageNames(packagename))
            except NotFoundError:
                # getPackageNames may raise NotFoundError. It would be
                # nicer to allow people to indicate a package even if
                # never published, but the quick fix for now is to note
                # the issue and move on.
                self.notification += ("<br /><br />Note that the package %r "
                                      "is not published in %s; the bug "
                                      "has therefore been targeted to the "
                                      "distribution only."
                                      % (packagename, context.displayname))
                comment += ("\r\n\r\nNote: the original reporter indicated "
                            "the bug was in package %r; however, that package "
                            "was not published in %s."
                            % (packagename, context.displayname))
                bug = context.createBug(
                    title=title, comment=comment, private=private,
                    security_related=security_related, owner=current_user)
            else:
                bugtarget = context.getSourcePackage(sourcepackagename.name)
                bug = bugtarget.createBug(
                    title=title, comment=comment, private=private,
                    security_related=security_related, owner=current_user,
                    binarypackagename=binarypackagename)
        else:
            bug = context.createBug(
                title=title, comment=comment, private=private,
                security_related=security_related, owner=current_user)

        self.addedBug = bug
        return self.addedBug

    def nextURL(self):
        # Give the user some feedback on the bug just opened.
        self.request.response.addNotification(self.notification)

        task = self.addedBug.bugtasks[0]
        return canonical_url(task)

    def _setUpWidgets(self):
        # Customize the onKeyPress event of the package name chooser,
        # so that it's corresponding radio button is selected.
        setUpWidgets(self, self.schema, IInputWidget, names=self.fieldNames)
        if "packagename" in self.fieldNames:
            self.packagename_widget.onKeyPress = "selectWidget('choose', event)"
