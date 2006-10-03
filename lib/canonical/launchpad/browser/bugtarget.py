# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTarget-related browser views."""

__metaclass__ = type

__all__ = [
    "BugTargetBugListingView",
    "BugTargetBugTagsView",
    "FileBugView",
    "FileBugSearchForDupesView"
    ]

import urllib

from zope.app.form.browser import TextWidget
from zope.app.form.interfaces import IInputWidget, WidgetsError, InputErrors
from zope.app.form.utility import setUpWidgets
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify

from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import (
    ILaunchBag, IDistribution, IDistroRelease, IDistroReleaseSet,
    IProduct, IDistributionSourcePackage, NotFoundError, CreateBugParams,
    IBugAddForm, BugTaskSearchParams)
from canonical.launchpad.webapp import (
    canonical_url, LaunchpadView, LaunchpadFormView, action, custom_widget)
from canonical.launchpad.webapp.batching import TableBatchNavigator
from canonical.launchpad.webapp.generalform import GeneralFormView


class FileBugViewMixin:
    """Mixin class for views related to filing a bug."""

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


class FileBugView(GeneralFormView, FileBugViewMixin):
    """Browser view for filebug forms.

    This class handles bugs filed on an IBugTarget, and the 'generic'
    bug filing, where a distribution argument is passed with the form.
    """

    def initialize(self):
        self.packagename_error = ""

    @property
    def initial_values(self):
        """Set the default package name when filing a distribution bug."""
        if not IDistributionSourcePackage.providedBy(self.context):
            return {}

        if self.request.get("field.packagename"):
            return {}

        return {'packagename': self.context.name}

    def shouldSelectChoosePackageNameRadioButton(self):
        """Should the radio button to select a package be selected?"""
        # XXX, Brad Bollenbach, 2006-07-13: We also call _renderedValueSet() in
        # case there is a default value in the widget, i.e., a value that was
        # set outside the request. See https://launchpad.net/bugs/52912.
        return (
            self.request.form.get("field.packagename") or
            self.packagename_widget._renderedValueSet())

    def validateFromRequest(self):
        """Make sure the package name, if provided, exists in the distro."""
        self.packagename_error = ""
        form = self.request.form

        if form.get("packagename_option") == "choose":
            packagename = form.get("field.packagename")
            if packagename:
                if IDistribution.providedBy(self.context):
                    distribution = self.context
                else:
                    assert IDistributionSourcePackage.providedBy(self.context)
                    distribution = self.context.distribution

                try:
                    distribution.guessPackageNames(packagename)
                except NotFoundError:
                    self.packagename_error = (
                        '"%s" does not exist in %s. Please choose a different '
                        'package. If you\'re unsure, please select '
                        '"I don\'t know"' % (
                            packagename, distribution.displayname))
            else:
                self.packagename_error = "Please enter a package name"

        if self.packagename_error:
            raise WidgetsError(self.packagename_error)

    def process(self, title=None, comment=None, packagename=None,
                distribution=None, security_related=False):
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

        # Security bugs are always private when filed, but can be disclosed
        # after they've been reported.
        if security_related:
            private = True
        else:
            private = False

        notification = "Thank you for your bug report."
        if IDistribution.providedBy(context) and packagename:
            # We don't know if the package name we got was a source or binary
            # package name, so let the Soyuz API figure it out for us.
            packagename = str(packagename)
            try:
                sourcepackagename, binarypackagename = (
                    context.guessPackageNames(packagename))
            except NotFoundError:
                # guessPackageNames may raise NotFoundError. It would be
                # nicer to allow people to indicate a package even if
                # never published, but the quick fix for now is to note
                # the issue and move on.
                notification += (
                    "<br /><br />The package %s is not published in %s; the "
                    "bug was targeted only to the distribution."
                    % (packagename, context.displayname))
                comment += ("\r\n\r\nNote: the original reporter indicated "
                            "the bug was in package %r; however, that package "
                            "was not published in %s."
                            % (packagename, context.displayname))
                params = CreateBugParams(
                    title=title, comment=comment, private=private,
                    security_related=security_related, owner=current_user)
            else:
                context = context.getSourcePackage(sourcepackagename.name)
                params = CreateBugParams(
                    title=title, comment=comment, private=private,
                    security_related=security_related, owner=current_user,
                    binarypackagename=binarypackagename)
        else:
            params = CreateBugParams(
                title=title, comment=comment, private=private,
                security_related=security_related, owner=current_user)

        bug = context.createBug(params)
        notify(SQLObjectCreatedEvent(bug))

        # Give the user some feedback on the bug just opened.
        self.request.response.addNotification(notification)
        if bug.private:
            self.request.response.addNotification(
                'Security-related bugs are by default <span title="Private '
                'bugs are visible only to their direct subscribers.">private'
                '</span>. You may choose to <a href="+secrecy">publically '
                'disclose</a> this bug.')
        self._nextURL = canonical_url(bug.bugtasks[0])

    def _setUpWidgets(self):
        # Customize the onKeyPress event of the package name chooser,
        # so that it's corresponding radio button is selected.
        setUpWidgets(
            self, self.schema, IInputWidget, initial=self.initial_values,
            names=self.fieldNames)

        if "packagename" in self.fieldNames:
            self.packagename_widget.onKeyPress = "selectWidget('choose', event)"


class FileBugSearchForDupesView(LaunchpadFormView, FileBugViewMixin):
    schema = IBugAddForm
    custom_widget('title', TextWidget, displayWidth=40)

    _MATCHING_BUGS_LIMIT = 10
    _SEARCH_FOR_DUPES = ViewPageTemplateFile(
        "../templates/bugtarget-filebug-search.pt")
    _DISPLAY_DUPES = ViewPageTemplateFile(
        "../templates/bugtarget-filebug-search-results.pt")
    _FILEBUG_FORM = ViewPageTemplateFile(
        "../templates/bugtarget-filebug-simple.pt")

    template = _SEARCH_FOR_DUPES

    focused_element_id = 'field.title'

    # The steps in the filebug workflow, which are displayed on each
    # page of the process.
    _FILEBUG_STEPS = [
        ("search", "Describe the bug in brief"),
        ("check_for_similar", "See if it's already been reported"),
        ("filebug", "Describe the bug in more detail")]

    current_step = "search"

    @property
    def field_names(self):
        """Return the list of field names to display."""
        context = self.context
        if IProduct.providedBy(context):
            return ['title', 'comment']
        else:
            assert (
                IDistribution.providedBy(context) or
                IDistributionSourcePackage.providedBy(context))

            return ['title', 'comment', 'packagename']

    @property
    def initial_values(self):
        """Give packagename a default value, if applicable."""
        if not IDistributionSourcePackage.providedBy(self.context):
            return {}

        return {'packagename': self.context.name}

    def setUpWidgets(self):
        """Customize the onKeyPress event of the package name chooser."""
        LaunchpadFormView.setUpWidgets(self)

        if "packagename" in self.field_names:
            self.widgets["packagename"].onKeyPress = (
                "selectWidget('choose', event)")

    def contextUsesMalone(self):
        """Does the context use Malone as its official bugtracker?"""
        return self.getProductOrDistroFromContext().official_malone

    def shouldSelectPackageName(self):
        """Should the choose-a-package radio button be selected?"""
        return bool(self.initial_values.get("packagename"))

    @action("See if it's already been reported",
            name="search", validator="validate_search")
    def search_action(self, action, data):
        """Search for similar bug reports."""
        self.current_step = "check_for_similar"
        return self._DISPLAY_DUPES()

    def getSteps(self):
        steps = []
        for step_name, step_title in self._FILEBUG_STEPS:
            is_current_step = step_name == self.current_step
            steps.append(
                dict(selected=is_current_step, title=step_title))
        return steps

    def getSimilarBugs(self):
        """Return the similar bugs based on the user search."""
        matching_bugs = []
        title = self.getSearchText()
        params = BugTaskSearchParams(self.user, searchtext=title)
        for bugtask in self.context.searchTasks(params):
            if not bugtask.bug in matching_bugs:
                matching_bugs.append(bugtask.bug)
                if len(matching_bugs) >= self._MATCHING_BUGS_LIMIT:
                    break

        return matching_bugs

    def getSearchText(self):
        """Return the search string entered by the user."""
        return self.widgets['title'].getInputValue()

    def validate_search(self, action, data):
        """Make sure some keywords are provided."""
        try:
            data['title'] = self.widgets['title'].getInputValue()
        except InputErrors, error:
            self.setFieldError("title", "A summary is required.")
            return [error]

        # Return an empty list of errors to satisfy the validation API,
        # and say "we've handled the validation and found no errors."
        return ()

    @action("I don't see my bug in this list",
            name="no_dupe_found", validator="validate_no_dupe_found")
    def no_dupe_found_action(self, action, data):
        """Show the simple bug form."""
        return self.showFileBugForm()

    def validate_no_dupe_found(self, action, data):
        return ()

    def showFileBugForm(self):
        self.current_step = "filebug"
        return self._FILEBUG_FORM()

    @action("Submit Bug Report", name="submit_bug",
            failure="showFileBugForm")
    def submit_bug_action(self, action, data):
        """Add a bug to this IBugTarget."""
        title = data.get("title")
        comment = data.get("comment")
        packagename = data.get("packagename")
        distribution = getUtility(ILaunchBag).distribution
        product = getUtility(ILaunchBag).product

        context = self.context
        if distribution is not None:
            # We're being called from the generic bug filing form, so manually
            # set the chosen distribution as the context.
            context = distribution

        # Ensure that no package information is used, if the user
        # enters a package name but then selects "I don't know".
        if self.request.form.get("packagename_option") == "none":
            packagename = None

        notification = "Thank you for your bug report."
        if IDistribution.providedBy(context) and packagename:
            # We don't know if the package name we got was a source or binary
            # package name, so let the Soyuz API figure it out for us.
            packagename = str(packagename)
            try:
                sourcepackagename, binarypackagename = (
                    context.guessPackageNames(packagename))
            except NotFoundError:
                # guessPackageNames may raise NotFoundError. It would be
                # nicer to allow people to indicate a package even if
                # never published, but the quick fix for now is to note
                # the issue and move on.
                notification += (
                    "<br /><br />The package %s is not published in %s; the "
                    "bug was targeted only to the distribution."
                    % (packagename, context.displayname))
                comment += ("\r\n\r\nNote: the original reporter indicated "
                            "the bug was in package %r; however, that package "
                            "was not published in %s."
                            % (packagename, context.displayname))
                params = CreateBugParams(
                    title=title, comment=comment, owner=self.user)
            else:
                context = context.getSourcePackage(sourcepackagename.name)
                params = CreateBugParams(
                    title=title, comment=comment, owner=self.user,
                    binarypackagename=binarypackagename)
        else:
            params = CreateBugParams(
                title=title, comment=comment, owner=self.user)

        bug = context.createBug(params)
        notify(SQLObjectCreatedEvent(bug))

        # Give the user some feedback on the bug just opened.
        self.request.response.addNotification(notification)
        self.request.response.redirect(canonical_url(bug.bugtasks[0]))

    def getMostCommonBugs(self):
        """Return a list of the most duplicated bugs."""
        return self.context.getMostCommonBugs(
            self.user, limit=self._MATCHING_BUGS_LIMIT)


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


class BugTargetBugTagsView(LaunchpadView):
    """Helper methods for rendering the bug tags portlet."""

    def _getSearchURL(self, tag):
        """Return the search URL for the tag."""
        return "%s?field.tag=%s" % (
            self.request.getURL(), urllib.quote(tag))

    def getUsedBugTagsWithURLs(self):
        """Return the bug tags and their search URLs."""
        bug_tag_counts = self.context.getUsedBugTagsWithOpenCounts(self.user)
        return [
            {'tag': tag, 'count': count, 'url': self._getSearchURL(tag)}
            for tag, count in bug_tag_counts]
