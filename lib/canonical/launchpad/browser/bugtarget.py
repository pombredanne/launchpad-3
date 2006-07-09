# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTarget-related browser views."""

__metaclass__ = type

__all__ = [
    "BugTargetBugListingView",
    "FileBugView"
    ]

from zope.app.form.interfaces import IInputWidget, WidgetsError
from zope.app.form.utility import setUpWidgets
from zope.component import getUtility
from zope.event import notify

from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import (
    ILaunchBag, IDistribution, IDistroRelease, IDistroReleaseSet,
    IProduct, IDistributionSourcePackage, NotFoundError)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.generalform import GeneralFormView

class FileBugView(GeneralFormView):
    """Browser view for filebug forms.

    This class handles bugs filed on an IBugTarget, and the 'generic'
    bug filing, where a distribution argument is passed with the form.
    """

    notification = "Thank you for your bug report."

    def initialize(self):
        self.packagename_error = ""

    @property
    def initial_values(self):
        """Set the default package name on which to file a bug."""
        if not IDistributionSourcePackage.providedBy(self.context):
            return

        if self.request.get("field.packagename"):
            return

        return {'packagename': self.context.name}

    def validateFromRequest(self):
        """Make sure the package name, if provided, exists in the distro."""
        self.packagename_error = ""
        form = self.request.form
        if form.get("packagename_option") == "choose":
            packagename = str(form.get("field.packagename"))
            if packagename:
                try:
                    self.context.getPackageNames(packagename)
                except NotFoundError:
                    self.packagename_error = (
                        '"%s" does not exist in %s. Please choose a different '
                        'package. If you\'re unsure, please select '
                        '"I don\'t know"' % (
                            packagename, self.context.displayname))
            else:
                self.packagename_error = "Please enter a package name"

        if self.packagename_error:
            raise WidgetsError(self.packagename_error)

    def process(self, title=None, comment=None, private=False,
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
                    title=title, comment=comment,
                    security_related=security_related,
                    owner=current_user)
            else:
                bugtarget = context.getSourcePackage(sourcepackagename.name)
                bug = bugtarget.createBug(
                    title=title, comment=comment,
                    security_related=security_related,
                    owner=current_user,
                    binarypackagename=binarypackagename)
        else:
            bug = context.createBug(
                title=title, comment=comment,
                security_related=security_related,
                owner=current_user)

            notify(SQLObjectCreatedEvent(bug))

        # Give the user some feedback on the bug just opened.
        self.request.response.addNotification(self.notification)
        self._nextURL = canonical_url(bug.bugtasks[0])

    def _setUpWidgets(self):
        # Customize the onKeyPress event of the package name chooser,
        # so that it's corresponding radio button is selected.
        setUpWidgets(
            self, self.schema, IInputWidget, initial=self.initial_values,
            names=self.fieldNames)

        if "packagename" in self.fieldNames:
            self.packagename_widget.onKeyPress = "selectWidget('choose', event)"

    def getProductOrDistroFromContext(self):
        """Return the IProduct or IDistribution for this context."""
        context = self.context

        if IDistribution.providedBy(context) or IProduct.providedBy(context):
            return context
        else:
            assert IDistributionSourcePackage.providedBy(context), (
                "Expected a bug filing context that provides one of "
                "IDistribution, IProduct, or IDistributionSourcePackage. "
                "Got: %r" % context)

            return context.distribution


class BugTargetBugListingView:
    """Helper methods for rendering bug listings."""

    @property
    def release_buglistings(self):
        """Return a buglisting for each release.

        The list is sorted newest release to oldest.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        distribution_context = IDistribution(self.context, None)
        distrorelease_context = IDistroRelease(self.context, None)

        if distrorelease_context:
            distribution = distrorelease_context.distribution
        elif distribution_context:
            distribution = distribution_context
        else:
            raise AssertionError, ("release_bug_counts called with "
                                   "illegal context")

        releases = getUtility(IDistroReleaseSet).search(
            distribution=distribution, orderBy="-datereleased")

        release_buglistings = []
        for release in releases:
            release_buglistings.append(
                dict(
                    title=release.displayname,
                    url=canonical_url(release) + "/+bugs",
                    count=release.open_bugtasks.count()))

        return release_buglistings
