# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTarget-related browser views."""

__metaclass__ = type

__all__ = [
    "BugTargetBugListingView",
    "BugTargetBugsView",
    "BugTargetBugTagsView",
    "FileBugViewBase",
    "FileBugAdvancedView",
    "FileBugGuidedView",
    "FrontPageFileBugAdvancedView",
    "FrontPageFileBugGuidedView",
    "ProjectFileBugGuidedView",
    "ProjectFileBugAdvancedView",
    ]

import cgi
from cStringIO import StringIO
import email
import urllib

from zope.app.form.browser import TextWidget
from zope.app.form.interfaces import InputErrors
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.browser.bugtask import BugTaskSearchListingView
from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import (
    IBugTaskSet, ILaunchBag, IDistribution, IDistroRelease, IDistroReleaseSet,
    IProduct, IProject, IDistributionSourcePackage, NotFoundError,
    CreateBugParams, IBugAddForm, ILaunchpadCelebrities, IProductSeries,
    ITemporaryStorageManager, IMaloneApplication, IFrontPageBugAddForm,
    IProjectBugAddForm)
from canonical.launchpad.webapp import (
    canonical_url, LaunchpadView, LaunchpadFormView, action, custom_widget,
    urlappend)
from canonical.lp.dbschema import BugTaskStatus
from canonical.widgets.bug import BugTagsWidget, FileBugTargetWidget


class FileBugData:
    """Extra data to be added to the bug."""

    def __init__(self):
        self.initial_summary = None
        self.initial_summary = None
        self.initial_tags = []
        self.extra_description = None
        self.comments = []
        self.attachments = []

    def setFromRawMessage(self, raw_mime_msg):
        """Set the extra file bug data from a MIME multipart message.

            * The Subject header is the initial bug summary.
            * The Tags header specifies the initial bug tags.
            * The first inline part will be added to the description.
            * All other inline parts will be added as separate comments.
            * All attachment parts will be added as attachment.
        """
        mime_msg = email.message_from_string(raw_mime_msg)
        if mime_msg.is_multipart():
            self.initial_summary = mime_msg.get('Subject')
            tags = mime_msg.get('Tags', '')
            self.initial_tags = tags.lower().split()
            for part in mime_msg.get_payload():
                disposition_header = part.get('Content-Disposition', 'inline')
                # Get the type, excluding any parameters.
                disposition_type = disposition_header.split(';')[0]
                disposition_type = disposition_type.strip()
                if disposition_type == 'inline':
                    assert part.get_content_type() == 'text/plain', (
                        "Inline parts have to be plain text.")
                    charset = part.get_content_charset()
                    assert charset, (
                        "A charset has to be specified for text parts.")
                    part_text = part.get_payload(decode=True).decode(charset)
                    part_text = part_text.rstrip()
                    if self.extra_description is None:
                        self.extra_description = part_text
                    else:
                        self.comments.append(part_text)
                elif disposition_type == 'attachment':
                    attachment = dict(
                        filename=part.get_filename().strip("'"),
                        content_type=part['Content-type'],
                        content=StringIO(part.get_payload(decode=True)))
                    if part.get('Content-Description'):
                        attachment['description'] = part['Content-Description']
                    else:
                        attachment['description'] = attachment['filename']
                    self.attachments.append(attachment)
                else:
                    # If the message include other disposition types,
                    # simply ignore them. We don't want to break just
                    # because some extra information is included.
                    continue



class FileBugViewBase(LaunchpadFormView):
    """Base class for views related to filing a bug."""

    implements(IBrowserPublisher)

    extra_data_token = None
    advanced_form = False
    can_decide_security_contact = True

    def __init__(self, context, request):
        LaunchpadFormView.__init__(self, context, request)
        self.extra_data = FileBugData()

    def initialize(self):
        LaunchpadFormView.initialize(self)
        if self.extra_data_token is not None:
            # self.extra_data has been initialized in publishTraverse().
            if self.extra_data.initial_summary:
                self.widgets['title'].setRenderedValue(
                    self.extra_data.initial_summary)
            if self.extra_data.initial_tags:
                self.widgets['tags'].setRenderedValue(
                    self.extra_data.initial_tags)
            # XXX: We should include more details of what will be added
            #      to the bug report.
            #      -- Bjorn Tillenius, 2006-01-15
            self.request.response.addNotification(
                'Extra debug information will be added to the bug report'
                ' automatically.')

    @property
    def initial_values(self):
        """Give packagename a default value, if applicable."""
        if not IDistributionSourcePackage.providedBy(self.context):
            return {}

        return {'packagename': self.context.name}

    def contextIsProduct(self):
        return IProduct.providedBy(self.context)

    def getPackageNameFieldCSSClass(self):
        """Return the CSS class for the packagename field."""
        if self.widget_errors.get("packagename"):
            return 'error'
        else:
            return ''

    def validate(self, data):
        """Make sure the package name, if provided, exists in the distro."""
        # We have to poke at the packagename value directly in the
        # request, because if validation failed while getting the
        # widget's data, it won't appear in the data dict.
        form = self.request.form
        if form.get("packagename_option") == "choose":
            packagename = form.get("field.packagename")
            if packagename:
                if IDistribution.providedBy(self.context):
                    distribution = self.context
                elif 'distribution' in data:
                    distribution = data['distribution']
                else:
                    assert IDistributionSourcePackage.providedBy(self.context)
                    distribution = self.context.distribution

                try:
                    distribution.guessPackageNames(packagename)
                except NotFoundError:
                    if distribution.releases:
                        # If a distribution doesn't have any releases,
                        # it won't have any source packages published at
                        # all, so we set the error only if there are
                        # releases.
                        packagename_error = (
                            '"%s" does not exist in %s. Please choose a '
                            "different package. If you're unsure, please "
                            'select "I don\'t know"' % (
                                packagename, distribution.displayname))
                        self.setFieldError("packagename", packagename_error)
            else:
                self.setFieldError("packagename", "Please enter a package name")

    def setUpWidgets(self):
        """Customize the onKeyPress event of the package name chooser."""
        LaunchpadFormView.setUpWidgets(self)

        if "packagename" in self.field_names:
            self.widgets["packagename"].onKeyPress = (
                "selectWidget('choose', event)")

    def contextUsesMalone(self):
        """Does the context use Malone as its official bugtracker?"""
        if IProject.providedBy(self.context):
            products_using_malone = [
                product for product in self.context.products
                if product.official_malone]
            return len(products_using_malone) > 0
        else:
            return self.getMainContext().official_malone

    def getMainContext(self):
        if IDistributionSourcePackage.providedBy(self.context):
            return self.context.distribution
        else:
            return self.context

    def shouldSelectPackageName(self):
        """Should the radio button to select a package be selected?"""
        return (
            self.request.form.get("field.packagename") or
            self.initial_values.get("packagename"))

    def handleSubmitBugFailure(self, action, data, errors):
        return self.showFileBugForm()

    @action("Submit Bug Report", name="submit_bug",
            failure=handleSubmitBugFailure)
    def submit_bug_action(self, action, data):
        """Add a bug to this IBugTarget."""
        title = data["title"]
        comment = data["comment"].rstrip()
        packagename = data.get("packagename")
        security_related = data.get("security_related", False)
        distribution = data.get(
            "distribution", getUtility(ILaunchBag).distribution)
        product = getUtility(ILaunchBag).product

        context = self.context
        if distribution is not None:
            # We're being called from the generic bug filing form, so
            # manually set the chosen distribution as the context.
            context = distribution
        elif IProject.providedBy(context):
            context = data['product']
        elif IMaloneApplication.providedBy(context):
            context = data['bugtarget']

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

        notifications = ["Thank you for your bug report."]
        params = CreateBugParams(
            title=title, comment=comment, owner=self.user,
            security_related=security_related, private=private,
            tags=data.get('tags'))
        if IDistribution.providedBy(context) and packagename:
            # We don't know if the package name we got was a source or binary
            # package name, so let the Soyuz API figure it out for us.
            packagename = str(packagename.name)
            try:
                sourcepackagename, binarypackagename = (
                    context.guessPackageNames(packagename))
            except NotFoundError:
                # guessPackageNames may raise NotFoundError. It would be
                # nicer to allow people to indicate a package even if
                # never published, but the quick fix for now is to note
                # the issue and move on.
                notifications.append(
                    "The package %s is not published in %s; the "
                    "bug was targeted only to the distribution."
                    % (packagename, context.displayname))
                params.comment += (
                    "\r\n\r\nNote: the original reporter indicated "
                    "the bug was in package %r; however, that package "
                    "was not published in %s." % (
                        packagename, context.displayname))
            else:
                context = context.getSourcePackage(sourcepackagename.name)
                params.binarypackagename = binarypackagename

        extra_data = self.extra_data
        if extra_data.extra_description:
            params.comment = "%s\n\n%s" % (
                params.comment, extra_data.extra_description)
            notifications.append(
                'Additional information was added to the bug description.')

        self.added_bug = bug = context.createBug(params)
        notify(SQLObjectCreatedEvent(bug))

        for comment in extra_data.comments:
            bug.newMessage(self.user, bug.followup_subject(), comment)
            notifications.append(
                'A comment with additional information was added to the'
                ' bug report.')

        if extra_data.attachments:
            # Attach all the comments to a single empty comment.
            attachment_comment = bug.newMessage(
                owner=self.user, subject=bug.followup_subject(), content=None)
            for attachment in extra_data.attachments:
                bug.addAttachment(
                    owner=self.user, file_=attachment['content'],
                    description=attachment['description'],
                    comment=attachment_comment,
                    filename=attachment['filename'],
                    content_type=attachment['content_type'])
                notifications.append(
                    'The file "%s" was attached to the bug report.' % 
                        cgi.escape(attachment['filename']))

        # Give the user some feedback on the bug just opened.
        for notification in notifications:
            self.request.response.addNotification(notification)
        if bug.private:
            self.request.response.addNotification(
                'Security-related bugs are by default <span title="Private '
                'bugs are visible only to their direct subscribers.">private'
                '</span>. You may choose to <a href="+secrecy">publically '
                'disclose</a> this bug.')

        self.request.response.redirect(canonical_url(bug.bugtasks[0]))

    def showFileBugForm(self):
        """Override this method in base classes to show the filebug form."""
        raise NotImplementedError

    @property
    def advanced_filebug_url(self):
        """The URL to the advanced bug filing form.

        If a token was passed to this view, it will be be passed through
        to the advanced bug filing form via the returned URL.
        """
        url = urlappend(canonical_url(self.context), '+filebug-advanced')
        if self.extra_data_token is not None:
            url = urlappend(url, self.extra_data_token)
        return url

    def publishTraverse(self, request, name):
        """See IBrowserPublisher."""
        if self.extra_data_token is not None:
            # publishTraverse() has already been called once before,
            # which means that he URL contains more path components than
            # expected.
            raise NotFound(self, name, request=request)

        extra_bug_data = getUtility(ITemporaryStorageManager).fetch(name)
        if extra_bug_data is not None:
            self.extra_data_token = name
            self.extra_data.setFromRawMessage(extra_bug_data.blob)
        else:
            # The URL might be mistyped, or the blob has expired.
            # XXX: We should handle this case better, since a user might
            #      come to this page when finishing his account
            #      registration. In that case we should inform the user
            #      that the blob has expired.
            #      -- Bjorn Tillenius, 2006-01-15
            raise NotFound(self, name, request=request)
        return self

    def browserDefault(self, request):
        """See IBrowserPublisher."""
        return self, ()

    def getProductOrDistroFromContext(self):
        """Return the product or distribution relative to the context.

        For instance, if the context is an IDistroRelease, return the
        distribution related to it. Will return None if the context is
        not related to a product or a distro.
        """
        context = self.context
        if IProduct.providedBy(context) or IDistribution.providedBy(context):
            return context
        elif IProductSeries.providedBy(context):
            return context.product
        elif (IDistroRelease.providedBy(context) or
              IDistributionSourcePackage.providedBy(context)):
            return context.distribution
        else:
            return None


class FileBugAdvancedView(FileBugViewBase):
    """Browser view for filing a bug.

    This view skips searching for duplicates.
    """
    schema = IBugAddForm
    # XXX, Brad Bollenbach, 2006-10-04: This assignment to actions is a
    # hack to make the action decorator Just Work across
    # inheritance. Technically, this isn't needed for this class,
    # because it defines no further actions, but I've added it just to
    # preclude mysterious bugs if/when another action is defined in this
    # class!
    actions = FileBugViewBase.actions
    custom_widget('title', TextWidget, displayWidth=40)
    custom_widget('tags', BugTagsWidget)
    template = ViewPageTemplateFile(
        "../templates/bugtarget-filebug-advanced.pt")
    advanced_form = True

    @property
    def field_names(self):
        """Return the list of field names to display."""
        context = self.context
        field_names = ['title', 'comment', 'security_related', 'tags']
        if (IDistribution.providedBy(context) or
            IDistributionSourcePackage.providedBy(context)):
            field_names.append('packagename')
        elif not IProduct.providedBy(context):
            raise AssertionError('Unknown context: %r' % context)
        return field_names

    def showFileBugForm(self):
        return self.template()


class FileBugGuidedView(FileBugViewBase):
    schema = IBugAddForm
    # XXX, Brad Bollenbach, 2006-10-04: This assignment to actions is a
    # hack to make the action decorator Just Work across inheritance.
    actions = FileBugViewBase.actions
    custom_widget('title', TextWidget, displayWidth=40)
    custom_widget('tags', BugTagsWidget)

    _MATCHING_BUGS_LIMIT = 10
    _SEARCH_FOR_DUPES = ViewPageTemplateFile(
        "../templates/bugtarget-filebug-search.pt")
    _FILEBUG_FORM = ViewPageTemplateFile(
        "../templates/bugtarget-filebug-submit-bug.pt")

    template = _SEARCH_FOR_DUPES

    focused_element_id = 'field.title'

    @property
    def field_names(self):
        """Return the list of field names to display."""
        context = self.context
        field_names = ['title', 'comment', 'tags']
        if (IDistribution.providedBy(context) or
            IDistributionSourcePackage.providedBy(context)):
            field_names.append('packagename')
        elif not IProduct.providedBy(context):
            raise AssertionError('Unknown context: %r' % context)

        return field_names

    @action("Continue", name="search", validator="validate_search")
    def search_action(self, action, data):
        """Search for similar bug reports."""
        # Don't give focus to any widget, to ensure that the browser
        # won't scroll past the "possible duplicates" list.
        self.initial_focus_widget = None
        return self.showFileBugForm()

    def getSearchContext(self):
        """Return the context used to search for similar bugs."""
        if IDistributionSourcePackage.providedBy(self.context):
            return self.context

        search_context = self.getMainContext()
        if IProject.providedBy(search_context):
            assert self.widgets['product'].hasValidInput(), (
                "This method should be called only when we know which"
                " product the user selected.")
            search_context = self.widgets['product'].getInputValue()
        elif IMaloneApplication.providedBy(search_context):
            assert self.widgets['bugtarget'].hasValidInput(), (
                "This method should be called only when we know which"
                " distribution the user selected.")
            search_context = self.widgets['bugtarget'].getInputValue()
        return search_context

    @cachedproperty
    def similar_bugs(self):
        """Return the similar bugs based on the user search."""
        matching_bugs = []
        title = self.getSearchText()
        if not title:
            return []
        search_context = self.getSearchContext()
        if IProduct.providedBy(search_context):
            context_params = {'product': search_context}
        elif IDistribution.providedBy(search_context):
            context_params = {'distribution': search_context}
        else:
            assert IDistributionSourcePackage.providedBy(search_context), (
                    'Unknown search context: %r' % search_context)
            context_params = {
                'distribution': search_context.distribution,
                'sourcepackagename': search_context.sourcepackagename}

        matching_bugtasks = getUtility(IBugTaskSet).findSimilar(
            self.user, title, **context_params)
        # Remove all the prejoins, since we won't use them and they slow
        # down the query significantly.
        matching_bugtasks = matching_bugtasks.prejoin([])

        # XXX: We might end up returning less than :limit: bugs, but in
        #      most cases we won't, and '4*limit' is here to prevent
        #      this page from timing out in production. Later I'll fix
        #      this properly by selecting distinct Bugs directly
        #      If matching_bugtasks isn't sliced, it will take a long time
        #      to iterate over it, even over only 10, because
        #      Transaction.iterSelect() listifies the result. Bug 75764.
        #      -- Bjorn Tillenius, 2006-12-13
        # We select more than :self._MATCHING_BUGS_LIMIT: since if a bug
        # affects more than one source package, it will be returned more
        # than one time. 4 is an arbitrary number that should be large
        # enough.
        for bugtask in matching_bugtasks[:4*self._MATCHING_BUGS_LIMIT]:
            if not bugtask.bug in matching_bugs:
                matching_bugs.append(bugtask.bug)
                if len(matching_bugs) >= self._MATCHING_BUGS_LIMIT:
                    break

        return matching_bugs

    @cachedproperty
    def most_common_bugs(self):
        """Return a list of the most duplicated bugs."""
        search_context = self.getSearchContext()
        return search_context.getMostCommonBugs(
            self.user, limit=self._MATCHING_BUGS_LIMIT)

    @property
    def found_possible_duplicates(self):
        return self.similar_bugs or self.most_common_bugs


    def getSearchText(self):
        """Return the search string entered by the user."""
        try:
            return self.widgets['title'].getInputValue()
        except InputErrors:
            return None

    def validate_search(self, action, data):
        """Make sure some keywords are provided."""
        try:
            data['title'] = self.widgets['title'].getInputValue()
        except InputErrors, error:
            self.setFieldError("title", "A summary is required.")
            return [error]

        # Return an empty list of errors to satisfy the validation API,
        # and say "we've handled the validation and found no errors."
        return []

    def validate_no_dupe_found(self, action, data):
        return ()

    @action("Continue", name="continue",
            validator="validate_no_dupe_found")
    def continue_action(self, action, data):
        """The same action as no-dupe-found, with a different label."""
        return self.showFileBugForm()

    def showFileBugForm(self):
        return self._FILEBUG_FORM()

class ProjectFileBugGuidedView(FileBugGuidedView):
    """Guided filebug pages for IProject."""

    # Make inheriting the base class' actions work.
    actions = FileBugGuidedView.actions
    schema = IProjectBugAddForm
    can_decide_security_contact = False

    field_names = ['product', 'title', 'comment', 'tags']

    @cachedproperty
    def most_common_bugs(self):
        """Return a list of the most duplicated bugs."""
        assert self.widgets['product'].hasValidInput(), (
            "This method should be called only when we know which"
            " product the user selected.")
        selected_product = self.widgets['product'].getInputValue()
        return selected_product.getMostCommonBugs(
            self.user, limit=self._MATCHING_BUGS_LIMIT)


class ProjectFileBugAdvancedView(FileBugAdvancedView):
    """Advanced filebug page for IProject."""

    # Make inheriting the base class' actions work.
    actions = FileBugAdvancedView.actions
    schema = IProjectBugAddForm
    can_decide_security_contact = False

    field_names = ['product', 'title', 'comment', 'security_related', 'tags']


class FrontPageFileBugGuidedView(FileBugGuidedView):
    """Browser view class for the top-level +filebug page."""
    schema = IFrontPageBugAddForm
    custom_widget('bugtarget', FileBugTargetWidget)

    # Make inheriting the base class' actions work.
    actions = FileBugGuidedView.actions

    @property
    def initial_values(self):
        return {"bugtarget": getUtility(ILaunchpadCelebrities).ubuntu}

    @property
    def field_names(self):
        return ['title', 'comment', 'bugtarget', 'tags']

    def contextUsesMalone(self):
        """Say context uses Malone so that the filebug form is shown!"""
        return True

    def validate_search(self, action, data):
        errors = FileBugGuidedView.validate_search(self, action, data)
        try:
            data['bugtarget'] = self.widgets['bugtarget'].getInputValue()
        except InputErrors, error:
            self.setFieldError("bugtarget", error.doc())
            errors.append(error)
        return errors


class FrontPageFileBugAdvancedView(FileBugAdvancedView):
    """Browser view class for the top-level +filebug-advanced page."""
    schema = IFrontPageBugAddForm
    custom_widget('bugtarget', FileBugTargetWidget)

    # Make inheriting the base class' actions work.
    actions = FileBugAdvancedView.actions
    can_decide_security_contact = False

    @property
    def initial_values(self):
        return {"bugtarget": getUtility(ILaunchpadCelebrities).ubuntu}

    @property
    def field_names(self):
        return ['title', 'comment', 'security_related', 'bugtarget', 'tags']

    def contextUsesMalone(self):
        """Say context uses Malone so that the filebug form is shown!"""
        return True


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


class BugCountDataItem:
    """Data about bug count for a status."""

    def __init__(self, label, count, color):
        self.label = label
        self.count = count
        if color.startswith('#'):
            self.color = 'MochiKit.Color.Color.fromHexString("%s")' % color
        else:
            self.color = 'MochiKit.Color.Color["%sColor"]()' % color


class BugTargetBugsView(BugTaskSearchListingView):
    """View for the Bugs front page."""

    # XXX: These colors should be changed. It's the same colors that are used
    #      to color statuses in buglistings using CSS, but there should be one
    #      unique color for each status in the pie chart
    #      -- Bjorn Tillenius, 2007-02-13
    status_color = {
        BugTaskStatus.UNCONFIRMED: '#993300',
        BugTaskStatus.NEEDSINFO: 'red',
        BugTaskStatus.CONFIRMED: 'orange',
        BugTaskStatus.INPROGRESS: 'blue',
        BugTaskStatus.FIXCOMMITTED: 'green',
        BugTaskStatus.FIXRELEASED: 'magenta',
        BugTaskStatus.REJECTED: 'yellow',
        BugTaskStatus.UNKNOWN: 'purple',
    }

    def initialize(self):
        BugTaskSearchListingView.initialize(self)
        bug_statuses_to_show = [
            BugTaskStatus.UNCONFIRMED,
            BugTaskStatus.NEEDSINFO,
            BugTaskStatus.CONFIRMED,
            BugTaskStatus.INPROGRESS,
            BugTaskStatus.FIXCOMMITTED,
            ]
        if IDistroRelease.providedBy(self.context):
            bug_statuses_to_show.append(BugTaskStatus.FIXRELEASED)
        bug_counts = sorted(
            self.context.getBugCounts(self.user, bug_statuses_to_show).items())
        self.bug_count_items = [
            BugCountDataItem(status.title, count, self.status_color[status])
            for status, count in bug_counts]

    def getChartJavascript(self):
        """Return a snippet of Javascript that draws a pie chart."""
        # XXX: This snippet doesn't work in IE, since (I think) there
        #      has to be a delay between creating the canvas element and
        #      using it to draw the chart. -- Bjorn Tillenius, 2007-02-13
        js_template = """
            function drawGraph() {
                var options = {
                  "drawBackground": false,
                  "colorScheme": [%(color_list)s],
                  "xTicks": [%(label_list)s]};
                var data = [%(data_list)s];
                var plotter = PlotKit.EasyPlot(
                    "pie", options, $("bugs-chart"), [data]);
            }
            MochiKit.DOM.addLoadEvent(drawGraph);
            """
        # The color list should inlude only colors for slices that will
        # be drawn in the pie chart, so colors that don't have any bugs
        # associated with them.
        color_list = ', '.join(
            data_item.color for data_item in self.bug_count_items
            if data_item.count > 0)
        label_list = ', '.join([
            '{v:%i, label:"%s"}' % (index, data_item.label)
            for index, data_item in enumerate(self.bug_count_items)])
        data_list = ', '.join([
            '[%i, %i]' % (index, data_item.count)
            for index, data_item in enumerate(self.bug_count_items)])
        return js_template % dict(
            color_list=color_list, label_list=label_list, data_list=data_list)


class BugTargetBugTagsView(LaunchpadView):
    """Helper methods for rendering the bug tags portlet."""

    def _getSearchURL(self, tag):
        """Return the search URL for the tag."""
        # Use path_only here to reduce the size of the rendered page.
        return "%s?field.tag=%s" % (
            self.request.getURL(path_only=True), urllib.quote(tag))

    def getUsedBugTagsWithURLs(self):
        """Return the bug tags and their search URLs."""
        bug_tag_counts = self.context.getUsedBugTagsWithOpenCounts(self.user)
        return [
            {'tag': tag, 'count': count, 'url': self._getSearchURL(tag)}
            for tag, count in bug_tag_counts]
