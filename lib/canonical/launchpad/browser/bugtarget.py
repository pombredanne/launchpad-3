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
    IBug, IBugTaskSet, ILaunchBag, IDistribution, IDistroSeries, IProduct,
    IProject, IDistributionSourcePackage, NotFoundError,
    CreateBugParams, IBugAddForm, ILaunchpadCelebrities,
    IProductSeries, ITemporaryStorageManager, IMaloneApplication,
    IFrontPageBugAddForm, IProjectBugAddForm, UNRESOLVED_BUGTASK_STATUSES,
    BugTaskStatus)
from canonical.launchpad.webapp import (
    canonical_url, LaunchpadView, LaunchpadFormView, action, custom_widget,
    safe_action, urlappend)
from canonical.widgets.bug import BugTagsWidget
from canonical.widgets.launchpadtarget import LaunchpadTargetWidget
from canonical.launchpad.vocabularies import ValidPersonOrTeamVocabulary

class FileBugData:
    """Extra data to be added to the bug."""

    def __init__(self):
        self.initial_summary = None
        self.initial_summary = None
        self.initial_tags = []
        self.private = None
        self.subscribers = []
        self.extra_description = None
        self.comments = []
        self.attachments = []

    def setFromRawMessage(self, raw_mime_msg):
        """Set the extra file bug data from a MIME multipart message.

            * The Subject header is the initial bug summary.
            * The Tags header specifies the initial bug tags.
            * The Private header sets the visibility of the bug.
            * The Subscribers header specifies additional initial subscribers
            * The first inline part will be added to the description.
            * All other inline parts will be added as separate comments.
            * All attachment parts will be added as attachment.
        """
        mime_msg = email.message_from_string(raw_mime_msg)
        if mime_msg.is_multipart():
            self.initial_summary = mime_msg.get('Subject')
            tags = mime_msg.get('Tags', '')
            self.initial_tags = tags.lower().split()
            private = mime_msg.get('Private')
            if private:
                if private.lower() == 'yes':
                    self.private = True
                elif private.lower() == 'no':
                    self.private = False
                else:
                    # If the value is anything other than yes or no we just
                    # ignore it as we cannot currently give the user an error
                    pass
            subscribers = mime_msg.get('Subscribers', '')
            self.subscribers = subscribers.split()
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
    frontpage_form = False

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
            # XXX: Bjorn Tillenius 2006-01-15:
            #      We should include more details of what will be added
            #      to the bug report.
            self.request.response.addNotification(
                'Extra debug information will be added to the bug report'
                ' automatically.')

    @property
    def field_names(self):
        """Return the list of field names to display."""
        context = self.context
        field_names = ['title', 'comment', 'tags', 'security_related',
                       'bug_already_reported_as']
        if (IDistribution.providedBy(context) or
            IDistributionSourcePackage.providedBy(context)):
            field_names.append('packagename')
        elif IMaloneApplication.providedBy(context):
            field_names.append('bugtarget')
        elif IProject.providedBy(context):
            field_names.append('product')
        elif not IProduct.providedBy(context):
            raise AssertionError('Unknown context: %r' % context)

        return field_names

    @property
    def initial_values(self):
        """Give packagename a default value, if applicable."""
        if not IDistributionSourcePackage.providedBy(self.context):
            return {}

        return {'packagename': self.context.name}

    def isPrivate(self):
        """Whether bug reports on this target are private by default."""
        return IProduct.providedBy(self.context) and self.context.private_bugs

    def contextIsProduct(self):
        return IProduct.providedBy(self.context)

    def contextIsProject(self):
        return IProject.providedBy(self.context)

    def getPackageNameFieldCSSClass(self):
        """Return the CSS class for the packagename field."""
        if self.widget_errors.get("packagename"):
            return 'error'
        else:
            return ''

    def validate(self, data):
        """Make sure the package name, if provided, exists in the distro."""

        # The comment field is only required if filing a new bug.
        if self.submit_bug_action.submitted():
            comment = data.get('comment')
            if comment:
                if len(comment) > IBug['description'].max_length:
                    self.setFieldError('comment',
                        'The description is too long. If you have lots '
                        'text to add, attach a file to the bug instead.')
            else:
                self.setFieldError('comment', "Required input is missing.")
        # Check a bug has been selected when the user wants to
        # subscribe to an existing bug.
        elif self.this_is_my_bug_action.submitted():
            if not data.get('bug_already_reported_as'):
                self.setFieldError('bug_already_reported_as', "Please choose a bug.")
        else:
            # We only care about those two actions.
            pass

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
                    if distribution.serieses:
                        # If a distribution doesn't have any serieses,
                        # it won't have any source packages published at
                        # all, so we set the error only if there are
                        # serieses.
                        packagename_error = (
                            '"%s" does not exist in %s. Please choose a '
                            "different package. If you're unsure, please "
                            'select "I don\'t know"' % (
                                packagename, distribution.displayname))
                        self.setFieldError("packagename", packagename_error)
            else:
                self.setFieldError("packagename", "Please enter a package name")

        # If we've been called from the frontpage filebug forms we must check
        # that whatever product or distro is having a bug filed against it
        # actually uses Malone for its bug tracking.
        product_or_distro = self.getProductOrDistroFromContext()
        if (product_or_distro is not None and
            not product_or_distro.official_malone):
            self.setFieldError('bugtarget',
                               "%s does not use Launchpad as its bug tracker " %
                               product_or_distro.displayname)

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

    def getSecurityContext(self):
        """Return the context used for security bugs."""
        return self.getMainContext()

    @property
    def can_decide_security_contact(self):
        """Will we be able to discern a security contact for this?"""
        return (self.getSecurityContext() is not None)

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

        if extra_data.private:
            params.private = extra_data.private

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

        if extra_data.subscribers:
            # Subscribe additional subscribers to this bug
            for subscriber in extra_data.subscribers:
                valid_person_vocabulary = ValidPersonOrTeamVocabulary()
                try:
                    person = valid_person_vocabulary.getTermByToken(
                        subscriber).value
                except LookupError:
                    # We cannot currently pass this error up to the user, so
                    # we'll just ignore it.
                    pass
                else:
                    bug.subscribe(person)
                    notifications.append(
                        '%s has been subscribed to this bug.' %
                        person.displayname)

        # Give the user some feedback on the bug just opened.
        for notification in notifications:
            self.request.response.addNotification(notification)
        if bug.security_related:
            self.request.response.addNotification(
                'Security-related bugs are by default <span title="Private '
                'bugs are visible only to their direct subscribers.">private'
                '</span>. You may choose to <a href="+secrecy">publically '
                'disclose</a> this bug.')
        if bug.private and not bug.security_related:
            self.request.response.addNotification(
                'This bug report has been marked as <span title="Private '
                'bugs are visible only to their direct subscribers.">private'
                '</span>. You may choose to <a href="+secrecy">change '
                'this</a>.')

        self.request.response.redirect(canonical_url(bug.bugtasks[0]))

    @action("Subscribe to This Bug Report", name="this_is_my_bug",
            failure=handleSubmitBugFailure)
    def this_is_my_bug_action(self, action, data):
        """Subscribe to the bug suggested."""
        bug = data.get('bug_already_reported_as')

        if bug.isSubscribed(self.user):
            self.request.response.addNotification(
                "You are already subscribed to this bug.")
        else:
            bug.subscribe(self.user)
            self.request.response.addNotification(
                "You have been subscribed to this bug.")

        self.next_url = canonical_url(bug.bugtasks[0])

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
            # XXX: Bjorn Tillenius 2006-01-15:
            #      We should handle this case better, since a user might
            #      come to this page when finishing his account
            #      registration. In that case we should inform the user
            #      that the blob has expired.
            raise NotFound(self, name, request=request)
        return self

    def browserDefault(self, request):
        """See IBrowserPublisher."""
        return self, ()

    def getProductOrDistroFromContext(self):
        """Return the product or distribution relative to the context.

        For instance, if the context is an IDistroSeries, return the
        distribution related to it. Will return None if the context is
        not related to a product or a distro.
        """
        context = self.context
        if IProduct.providedBy(context) or IDistribution.providedBy(context):
            return context
        elif IProductSeries.providedBy(context):
            return context.product
        elif (IDistroSeries.providedBy(context) or
              IDistributionSourcePackage.providedBy(context)):
            return context.distribution
        else:
            return None

    def showOptionalMarker(self, field_name):
        """See `LaunchpadFormView`."""
        # The comment field _is_ required, but only when filing the
        # bug. Since the same form is also used for subscribing to a
        # bug, the comment field in the schema cannot be marked
        # required=True. Instead it's validated in
        # FileBugViewBase.validate. So... we need to suppress the
        # "(Optional)" marker.
        if field_name == 'comment':
            return False
        else:
            return LaunchpadFormView.showOptionalMarker(self, field_name)

    def getRelevantBugTask(self, bug):
        """Return the first bugtask from this bug that's relevant in
        the current context.

        XXX Gavin Panella 2007-07-13:
        This is a pragmatic function, not general purpose. It
        tries to find a bugtask that can be used to pretty-up the
        page, making it more user-friendly and informative. It's not
        concerned by total accuracy, and will return the first
        'relevant' bugtask it finds even if there are other
        candidates. Be warned!
        """
        context = self.context
        bugtasks = bug.bugtasks

        if IDistribution.providedBy(context):
            def isRelevant(bugtask, context):
                return bugtask.distribution == context
        elif IProject.providedBy(context):
            def isRelevant(bugtask, context):
                return bugtask.pillar.project == context
        else:
            def isRelevant(bugtask, context):
                return bugtask.target == context

        for bugtask in bugtasks:
            if isRelevant(bugtask, context):
                return bugtask
        else:
            return None


class FileBugAdvancedView(FileBugViewBase):
    """Browser view for filing a bug.

    This view skips searching for duplicates.
    """
    schema = IBugAddForm
    # XXX: Brad Bollenbach 2006-10-04: This assignment to actions is a
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

    def showFileBugForm(self):
        return self.template()


class FileBugGuidedView(FileBugViewBase):
    schema = IBugAddForm
    # XXX: Brad Bollenbach 2006-10-04: This assignment to actions is a
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

    @safe_action
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
            if self.widgets['bugtarget'].hasValidInput():
                search_context = self.widgets['bugtarget'].getInputValue()
            else:
                search_context = None

        return search_context

    @cachedproperty
    def similar_bugs(self):
        """Return the similar bugs based on the user search."""
        matching_bugs = []
        title = self.getSearchText()
        if not title:
            return []
        search_context = self.getSearchContext()
        if search_context is None:
            return []
        elif IProduct.providedBy(search_context):
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

        # XXX: Bjorn Tillenius 2006-12-13 bug=75764
        #      We might end up returning less than :limit: bugs, but in
        #      most cases we won't, and '4*limit' is here to prevent
        #      this page from timing out in production. Later I'll fix
        #      this properly by selecting distinct Bugs directly
        #      If matching_bugtasks isn't sliced, it will take a long time
        #      to iterate over it, even over only 10, because
        #      Transaction.iterSelect() listifies the result.
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
        if search_context is None:
            return []
        else:
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

    def _getSelectedProduct(self):
        """Return the product that's selected."""
        assert self.widgets['product'].hasValidInput(), (
            "This method should be called only when we know which"
            " product the user selected.")
        return self.widgets['product'].getInputValue()

    @cachedproperty
    def most_common_bugs(self):
        """Return a list of the most duplicated bugs."""
        # We can only discover the most common bugs when a product has
        # been selected.
        if self.widgets['product'].hasValidInput():
            selected_product = self._getSelectedProduct()
            return selected_product.getMostCommonBugs(
                self.user, limit=self._MATCHING_BUGS_LIMIT)
        else:
            return []

    def getSecurityContext(self):
        """See FileBugViewBase."""
        return self._getSelectedProduct()


class ProjectFileBugAdvancedView(FileBugAdvancedView):
    """Advanced filebug page for IProject."""

    # Make inheriting the base class' actions work.
    actions = FileBugAdvancedView.actions
    schema = IProjectBugAddForm
    can_decide_security_contact = False


class FrontPageFileBugMixin:
    """Provides common methods for front-page bug-filing forms."""

    frontpage_form = True

    def contextUsesMalone(self):
        """Checks whether the current context uses Malone for bug tracking.

        If a bug is being filed against a product or distro then that product
        or distro's official_malone property is used to determine the return
        value of contextUsesMalone(). Otherwise, contextUsesMalone() will
        always return True, since doing otherwise will cause the front page
        file bug forms to be hidden.
        """
        product_or_distro = self.getProductOrDistroFromContext()

        if product_or_distro is None:
            return True
        else:
            return product_or_distro.official_malone

    def contextIsProduct(self):
        """Is the context a product?"""
        product_or_distro = self.getProductOrDistroFromContext()
        return IProduct.providedBy(product_or_distro)

    def getProductOrDistroFromContext(self):
        """Return the product or distribution relative to the context.

        For instance, if the context is an IDistroSeries, return the
        distribution related to it. This method will return None if the
        context is not related to a product or a distro.
        """
        context = self.context

        # We need to find a product or distribution from what we've had
        # submitted to us.
        if self.widgets['bugtarget'].hasValidInput():
            context = self.widgets['bugtarget'].getInputValue()
        else:
            return None

        if IProduct.providedBy(context) or IDistribution.providedBy(context):
            return context
        elif IProductSeries.providedBy(context):
            return context.product
        elif (IDistroSeries.providedBy(context) or
              IDistributionSourcePackage.providedBy(context)):
            return context.distribution
        else:
            return None


class FrontPageFileBugGuidedView(FrontPageFileBugMixin, FileBugGuidedView):
    """Browser view class for the top-level +filebug page."""
    schema = IFrontPageBugAddForm
    custom_widget('bugtarget', LaunchpadTargetWidget)

    # Make inheriting the base class' actions work.
    actions = FileBugGuidedView.actions

    @property
    def initial_values(self):
        return {"bugtarget": getUtility(ILaunchpadCelebrities).ubuntu}

    def validate_search(self, action, data):
        """Validates the parameters for the similar-bug search."""
        errors = FileBugGuidedView.validate_search(self, action, data)
        try:
            data['bugtarget'] = self.widgets['bugtarget'].getInputValue()

            # Check that Malone is actually used by this bugtarget.
            if (IProduct.providedBy(data['bugtarget']) or
                IDistribution.providedBy(data['bugtarget'])):
                product_or_distro = data['bugtarget']
            elif IProductSeries.providedBy(data['bugtarget']):
                product_or_distro = data['bugtarget'].product
            elif (IDistroSeries.providedBy(data['bugtarget']) or
                  IDistributionSourcePackage.providedBy(data['bugtarget'])):
                product_or_distro = data['bugtarget'].distribution
            else:
                product_or_distro = None

            if (product_or_distro is not None and
                not product_or_distro.official_malone):
                self.setFieldError('bugtarget',
                                    "%s does not use Launchpad as its bug "
                                    "tracker" %
                                    product_or_distro.displayname)

        except InputErrors, error:
            self.setFieldError("bugtarget", error.doc())
            errors.append(error)
        return errors

    def getSecurityContext(self):
        """See FileBugViewBase."""
        try:
            bugtarget = self.widgets['bugtarget'].getInputValue()
        except InputErrors, error:
            return None
        if IDistributionSourcePackage.providedBy(bugtarget):
            return bugtarget.distribution
        else:
            assert (
                IProduct.providedBy(bugtarget) or
                IDistribution.providedBy(bugtarget)), (
                "Unknown bug target: %r" % bugtarget)
            return bugtarget


class FrontPageFileBugAdvancedView(FrontPageFileBugMixin, FileBugAdvancedView):
    """Browser view class for the top-level +filebug-advanced page."""
    schema = IFrontPageBugAddForm
    custom_widget('bugtarget', LaunchpadTargetWidget)

    # Make inheriting the base class' actions work.
    actions = FileBugAdvancedView.actions
    can_decide_security_contact = False

    @property
    def initial_values(self):
        return {"bugtarget": getUtility(ILaunchpadCelebrities).ubuntu}

    def validate(self, data):
        """Ensures that the target uses Malone for its bug tracking.

        If the target does use Malone, further validation is carried out by
        FileBugViewBase.validate()
        """
        product_or_distro = self.getProductOrDistroFromContext()

        # If we have a context that we can test for Malone use, we do so.
        if (product_or_distro is not None and
            not product_or_distro.official_malone):
            self.setFieldError('bugtarget',
                               "%s does not use Launchpad as its bug tracker" %
                               product_or_distro.displayname)
        else:
            return super(FrontPageFileBugAdvancedView, self).validate(data)


class BugTargetBugListingView:
    """Helper methods for rendering bug listings."""

    @property
    def series_buglistings(self):
        """Return a buglisting for each series.

        The list is sorted newest series to oldest.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        if IDistribution(self.context, None):
            serieses = self.context.serieses
        elif IProduct(self.context, None):
            serieses = self.context.serieses
        elif IDistroSeries(self.context, None):
            serieses = self.context.distribution.serieses
        elif IProductSeries(self.context, None):
            serieses = self.context.product.serieses
        else:
            raise AssertionError, ("series_bug_counts called with "
                                   "illegal context")

        series_buglistings = []
        for series in serieses:
            series_buglistings.append(
                dict(
                    title=series.name,
                    url=canonical_url(series) + "/+bugs",
                    count=series.open_bugtasks.count()))

        return series_buglistings


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

    # XXX: Bjorn Tillenius 2007-02-13:
    #      These colors should be changed. It's the same colors that are used
    #      to color statuses in buglistings using CSS, but there should be one
    #      unique color for each status in the pie chart
    status_color = {
        BugTaskStatus.NEW: '#993300',
        BugTaskStatus.INCOMPLETE: 'red',
        BugTaskStatus.CONFIRMED: 'orange',
        BugTaskStatus.TRIAGED: 'black',
        BugTaskStatus.INPROGRESS: 'blue',
        BugTaskStatus.FIXCOMMITTED: 'green',
        BugTaskStatus.FIXRELEASED: 'magenta',
        BugTaskStatus.INVALID: 'yellow',
        BugTaskStatus.UNKNOWN: 'purple',
    }

    def initialize(self):
        BugTaskSearchListingView.initialize(self)
        bug_statuses_to_show = list(UNRESOLVED_BUGTASK_STATUSES)
        if IDistroSeries.providedBy(self.context):
            bug_statuses_to_show.append(BugTaskStatus.FIXRELEASED)
        bug_counts = sorted(
            self.context.getBugCounts(self.user, bug_statuses_to_show).items())
        self.bug_count_items = [
            BugCountDataItem(status.title, count, self.status_color[status])
            for status, count in bug_counts]

    def getChartJavascript(self):
        """Return a snippet of Javascript that draws a pie chart."""
        # XXX: Bjorn Tillenius 2007-02-13:
        #      This snippet doesn't work in IE, since (I think) there
        #      has to be a delay between creating the canvas element and
        #      using it to draw the chart.
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
            registerLaunchpadFunction(drawGraph);
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
        return "+bugs?field.tag=%s" % urllib.quote(tag)

    def getUsedBugTagsWithURLs(self):
        """Return the bug tags and their search URLs."""
        bug_tag_counts = self.context.getUsedBugTagsWithOpenCounts(self.user)
        return [
            {'tag': tag, 'count': count, 'url': self._getSearchURL(tag)}
            for tag, count in bug_tag_counts]
