# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""IBugTarget-related browser views."""

__metaclass__ = type

__all__ = [
    "BugsVHostBreadcrumb",
    "BugsPatchesView",
    "BugTargetBugListingView",
    "BugTargetBugTagsView",
    "BugTargetBugsView",
    "FileBugAdvancedView",
    "FileBugGuidedView",
    "FileBugViewBase",
    "IProductBugConfiguration",
    "OfficialBugTagsManageView",
    "ProductConfigureBugTrackerView",
    "ProjectFileBugGuidedView",
    "product_to_productbugconfiguration",
    ]

import cgi
from cStringIO import StringIO
from datetime import datetime
from operator import itemgetter
import urllib

from lazr.restful.interface import copy_field
from pytz import timezone
from simplejson import dumps
from sqlobject import SQLObjectNotFound
from z3c.ptcompat import ViewPageTemplateFile
from zope import formlib
from zope.app.form.browser import TextWidget
from zope.app.form.interfaces import InputErrors
from zope.component import getUtility
from zope.interface import (
    alsoProvides,
    implements,
    Interface,
    )
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.schema import (
    Bool,
    Choice,
    )
from zope.schema.vocabulary import SimpleVocabulary
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.browser.feeds import (
    BugFeedLink,
    BugTargetLatestBugsFeedLink,
    FeedsMixin,
    )
from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.searchbuilder import any
from canonical.launchpad.validators.name import valid_name_pattern
from canonical.launchpad.webapp import (
    canonical_url,
    LaunchpadView,
    urlappend,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.webapp.publisher import HTTP_MOVED_PERMANENTLY
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    safe_action,
    )
from lp.app.browser.tales import BugTrackerFormatterAPI
from lp.app.enums import ServiceUsage
from lp.app.errors import (
    NotFoundError,
    UnexpectedFormData,
    )
from lp.app.interfaces.launchpad import (
    ILaunchpadUsage,
    IServiceUsage,
    )
from lp.app.widgets.product import (
    GhostCheckBoxWidget,
    GhostWidget,
    ProductBugTrackerWidget,
    )
from lp.bugs.browser.bugrole import BugRoleMixin
from lp.bugs.browser.bugtask import BugTaskSearchListingView
from lp.bugs.browser.widgets.bug import (
    BugTagsWidget,
    LargeBugTagsWidget,
    )
from lp.bugs.browser.widgets.bugtask import NewLineToSpacesWidget
from lp.bugs.interfaces.apportjob import IProcessApportBlobJobSource
from lp.bugs.interfaces.bug import (
    CreateBugParams,
    IBug,
    IBugAddForm,
    IBugSet,
    IProjectGroupBugAddForm,
    )
from lp.bugs.interfaces.bugsupervisor import IHasBugSupervisor
from lp.bugs.interfaces.bugtarget import (
    IBugTarget,
    IOfficialBugTagTargetPublic,
    IOfficialBugTagTargetRestricted,
    )
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    BugTaskStatus,
    IBugTaskSet,
    UNRESOLVED_BUGTASK_STATUSES,
    )
from lp.bugs.interfaces.bugtracker import IBugTracker
from lp.bugs.interfaces.malone import IMaloneApplication
from lp.bugs.interfaces.securitycontact import IHasSecurityContact
from lp.bugs.utilities.filebugdataparser import FileBugData
from lp.hardwaredb.interfaces.hwdb import IHWSubmissionSet
from lp.registry.browser.product import ProductConfigureBase
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.vocabularies import ValidPersonOrTeamVocabulary
from lp.services.job.interfaces.job import JobStatus
from lp.services.propertycache import cachedproperty

# A simple vocabulary for the subscribe_to_existing_bug form field.
SUBSCRIBE_TO_BUG_VOCABULARY = SimpleVocabulary.fromItems(
    [('yes', True), ('no', False)])


class IProductBugConfiguration(Interface):
    """A composite schema for editing bug app configuration."""

    bug_supervisor = copy_field(
        IHasBugSupervisor['bug_supervisor'], readonly=False)
    security_contact = copy_field(IHasSecurityContact['security_contact'])
    official_malone = copy_field(ILaunchpadUsage['official_malone'])
    enable_bug_expiration = copy_field(
        ILaunchpadUsage['enable_bug_expiration'])
    bugtracker = copy_field(IProduct['bugtracker'])
    remote_product = copy_field(IProduct['remote_product'])
    bug_reporting_guidelines = copy_field(
        IBugTarget['bug_reporting_guidelines'])
    bug_reported_acknowledgement = copy_field(
        IBugTarget['bug_reported_acknowledgement'])
    enable_bugfiling_duplicate_search = copy_field(
        IBugTarget['enable_bugfiling_duplicate_search'])


def product_to_productbugconfiguration(product):
    """Adapts an `IProduct` into an `IProductBugConfiguration`."""
    alsoProvides(
        removeSecurityProxy(product), IProductBugConfiguration)
    return product


class ProductConfigureBugTrackerView(BugRoleMixin, ProductConfigureBase):
    """View class to configure the bug tracker for a project."""

    label = "Configure bug tracker"
    schema = IProductBugConfiguration
    # This ProductBugTrackerWidget renders enable_bug_expiration and
    # remote_product as subordinate fields, so this view suppresses them.
    custom_widget('bugtracker', ProductBugTrackerWidget)
    custom_widget('enable_bug_expiration', GhostCheckBoxWidget)
    custom_widget('remote_product', GhostWidget)

    @property
    def field_names(self):
        """Return the list of field names to display."""
        field_names = [
            "bugtracker",
            "enable_bug_expiration",
            "remote_product",
            "bug_reporting_guidelines",
            "bug_reported_acknowledgement",
            "enable_bugfiling_duplicate_search",
            ]
        if check_permission("launchpad.Edit", self.context):
            field_names.extend(["bug_supervisor", "security_contact"])

        return field_names

    def validate(self, data):
        """Constrain bug expiration to Launchpad Bugs tracker."""
        if check_permission("launchpad.Edit", self.context):
            self.validateBugSupervisor(data)
            self.validateSecurityContact(data)
        # enable_bug_expiration is disabled by JavaScript when bugtracker
        # is not 'In Launchpad'. The constraint is enforced here in case the
        # JavaScript fails to activate or run. Note that the bugtracker
        # name : values are {'In Launchpad' : object, 'Somewhere else' : None
        # 'In a registered bug tracker' : IBugTracker}.
        bugtracker = data.get('bugtracker', None)
        if bugtracker is None or IBugTracker.providedBy(bugtracker):
            data['enable_bug_expiration'] = False

    @action("Change", name='change')
    def change_action(self, action, data):
        # bug_supervisor and security_contactrequires a transition method,
        # so it must be handled separately and removed for the
        # updateContextFromData to work as expected.
        if check_permission("launchpad.Edit", self.context):
            self.changeBugSupervisor(data['bug_supervisor'])
            del data['bug_supervisor']
            self.changeSecurityContact(data['security_contact'])
            del data['security_contact']
        self.updateContextFromData(data)


class FileBugViewBase(LaunchpadFormView):
    """Base class for views related to filing a bug."""

    implements(IBrowserPublisher)

    extra_data_token = None
    advanced_form = False
    frontpage_form = False
    data_parser = None

    def __init__(self, context, request):
        LaunchpadFormView.__init__(self, context, request)
        self.extra_data = FileBugData()

    def initialize(self):
        LaunchpadFormView.initialize(self)
        if (not self.redirect_ubuntu_filebug and
            self.extra_data_token is not None and
            not self.extra_data_to_process):
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

    @cachedproperty
    def redirect_ubuntu_filebug(self):
        if IDistribution.providedBy(self.context):
            bug_supervisor = self.context.bug_supervisor
        elif (IDistributionSourcePackage.providedBy(self.context) or
              ISourcePackage.providedBy(self.context)):
            bug_supervisor = self.context.distribution.bug_supervisor
        else:
            bug_supervisor = None

        # Work out whether the redirect should be overidden.
        do_not_redirect = (
            self.request.form.get('no-redirect') is not None or
            [key for key in self.request.form.keys()
            if 'field.actions' in key] != [] or
            self.user.inTeam(bug_supervisor))

        return (
            config.malone.ubuntu_disable_filebug and
            self.targetIsUbuntu() and
            self.extra_data_token is None and
            not do_not_redirect)

    @property
    def field_names(self):
        """Return the list of field names to display."""
        context = self.context
        field_names = ['title', 'comment', 'tags', 'security_related',
                       'bug_already_reported_as', 'filecontent', 'patch',
                       'attachment_description', 'subscribe_to_existing_bug']
        if (IDistribution.providedBy(context) or
            IDistributionSourcePackage.providedBy(context)):
            field_names.append('packagename')
        elif IMaloneApplication.providedBy(context):
            field_names.append('bugtarget')
        elif IProjectGroup.providedBy(context):
            field_names.append('product')
        elif not IProduct.providedBy(context):
            raise AssertionError('Unknown context: %r' % context)

        if IHasBugSupervisor.providedBy(context):
            if self.user.inTeam(context.bug_supervisor):
                field_names.extend(
                    ['assignee', 'importance', 'milestone', 'status'])

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
        return IProjectGroup.providedBy(self.context)

    def targetIsUbuntu(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return (self.context == ubuntu or
                (IMaloneApplication.providedBy(self.context) and
                 self.request.form.get('field.bugtarget.distribution') ==
                 ubuntu.name))

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
                self.setFieldError('bug_already_reported_as',
                                   "Please choose a bug.")
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
                    if distribution.series:
                        # If a distribution doesn't have any series,
                        # it won't have any source packages published at
                        # all, so we set the error only if there are
                        # series.
                        packagename_error = (
                            '"%s" does not exist in %s. Please choose a '
                            "different package. If you're unsure, please "
                            'select "I don\'t know"' % (
                                packagename, distribution.displayname))
                        self.setFieldError("packagename", packagename_error)
            else:
                self.setFieldError("packagename",
                                   "Please enter a package name")

        # If we've been called from the frontpage filebug forms we must check
        # that whatever product or distro is having a bug filed against it
        # actually uses Malone for its bug tracking.
        product_or_distro = self.getProductOrDistroFromContext()
        if (product_or_distro is not None and
            product_or_distro.bug_tracking_usage != ServiceUsage.LAUNCHPAD):
            self.setFieldError(
                'bugtarget',
                "%s does not use Launchpad as its bug tracker " %
                product_or_distro.displayname)

    def setUpWidgets(self):
        """Customize the onKeyPress event of the package name chooser."""
        LaunchpadFormView.setUpWidgets(self)

        if "packagename" in self.field_names:
            self.widgets["packagename"].onKeyPress = (
                "selectWidget('choose', event)")

    def setUpFields(self):
        """Set up the form fields. See `LaunchpadFormView`."""
        super(FileBugViewBase, self).setUpFields()

        # Override the vocabulary for the subscribe_to_existing_bug
        # field.
        subscribe_field = Choice(
            __name__='subscribe_to_existing_bug',
            title=u'Subscribe to this bug',
            vocabulary=SUBSCRIBE_TO_BUG_VOCABULARY,
            required=True, default=False)

        self.form_fields = self.form_fields.omit('subscribe_to_existing_bug')
        self.form_fields += formlib.form.Fields(subscribe_field)

        security_related_field = Bool(
            __name__='security_related',
            title=_("This bug is a security vulnerability"),
            required=False, default=False)

        self.form_fields = self.form_fields.omit('security_related')
        self.form_fields += formlib.form.Fields(security_related_field)

    def contextUsesMalone(self):
        """Does the context use Malone as its official bugtracker?"""
        if IProjectGroup.providedBy(self.context):
            products_using_malone = [
                product for product in self.context.products
                if product.bug_tracking_usage == ServiceUsage.LAUNCHPAD]
            return len(products_using_malone) > 0
        else:
            bug_tracking_usage = self.getMainContext().bug_tracking_usage
            return bug_tracking_usage == ServiceUsage.LAUNCHPAD

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

        context = self.context
        if distribution is not None:
            # We're being called from the generic bug filing form, so
            # manually set the chosen distribution as the context.
            context = distribution
        elif IProjectGroup.providedBy(context):
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

        notifications = [self.getAcknowledgementMessage(self.context)]
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

        # Apply any extra options given by a bug supervisor.
        bugtask = self.added_bug.default_bugtask
        if 'assignee' in data:
            bugtask.transitionToAssignee(data['assignee'])
        if 'status' in data:
            bugtask.transitionToStatus(data['status'], self.user)
        if 'importance' in data:
            bugtask.transitionToImportance(data['importance'], self.user)
        if 'milestone' in data:
            bugtask.milestone = data['milestone']

        for comment in extra_data.comments:
            bug.newMessage(self.user, bug.followup_subject(), comment)
            notifications.append(
                'A comment with additional information was added to the'
                ' bug report.')

        # XXX 2007-01-19 gmb:
        #     We need to have a proper FileUpload widget rather than
        #     this rather hackish solution.
        attachment = self.request.form.get(self.widgets['filecontent'].name)
        if attachment or extra_data.attachments:
            # Attach all the comments to a single empty comment.
            attachment_comment = bug.newMessage(
                owner=self.user, subject=bug.followup_subject(), content=None)

            # Deal with attachments added in the filebug form.
            if attachment:
                # We convert slashes in filenames to hyphens to avoid
                # problems.
                filename = attachment.filename.replace('/', '-')

                # If the user hasn't entered a description for the
                # attachment we use its name.
                file_description = None
                if 'attachment_description' in data:
                    file_description = data['attachment_description']
                if file_description is None:
                    file_description = filename

                bug.addAttachment(
                    owner=self.user, data=StringIO(data['filecontent']),
                    filename=filename, description=file_description,
                    comment=attachment_comment, is_patch=data['patch'])

                notifications.append(
                    'The file "%s" was attached to the bug report.' %
                        cgi.escape(filename))

            for attachment in extra_data.attachments:
                bug.linkAttachment(
                    owner=self.user, file_alias=attachment['file_alias'],
                    description=attachment['description'],
                    comment=attachment_comment,
                    send_notifications=False)
                notifications.append(
                    'The file "%s" was attached to the bug report.' %
                        cgi.escape(attachment['file_alias'].filename))

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
                    bug.subscribe(person, self.user)
                    notifications.append(
                        '%s has been subscribed to this bug.' %
                        person.displayname)

        submission_set = getUtility(IHWSubmissionSet)
        for submission_key in extra_data.hwdb_submission_keys:
            submission = submission_set.getBySubmissionKey(
                submission_key, self.user)
            if submission is not None:
                bug.linkHWSubmission(submission)

        # Give the user some feedback on the bug just opened.
        for notification in notifications:
            self.request.response.addNotification(notification)
        if bug.security_related:
            self.request.response.addNotification(
                structured(
                'Security-related bugs are by default private '
                '(visible only to their direct subscribers). '
                'You may choose to <a href="+secrecy">publicly '
                'disclose</a> this bug.'))
        if bug.private and not bug.security_related:
            self.request.response.addNotification(
                structured(
                'This bug report has been marked private '
                '(visible only to its direct subscribers). '
                'You may choose to <a href="+secrecy">change this</a>.'))

        self.request.response.redirect(canonical_url(bug.bugtasks[0]))

    @action("Yes, this is the bug I'm trying to report",
            name="this_is_my_bug", failure=handleSubmitBugFailure)
    def this_is_my_bug_action(self, action, data):
        """Subscribe to the bug suggested."""
        bug = data.get('bug_already_reported_as')
        subscribe = data.get('subscribe_to_existing_bug')

        if bug.isUserAffected(self.user):
            self.request.response.addNotification(
                "This bug is already marked as affecting you.")
        else:
            bug.markUserAffected(self.user)
            self.request.response.addNotification(
                "This bug has been marked as affecting you.")

        # If the user wants to be subscribed, subscribe them, unless
        # they're already subscribed.
        if subscribe:
            if bug.isSubscribed(self.user):
                self.request.response.addNotification(
                    "You are already subscribed to this bug.")
            else:
                bug.subscribe(self.user, self.user)
                self.request.response.addNotification(
                    "You have been subscribed to this bug.")

        self.next_url = canonical_url(bug.bugtasks[0])

    def showFileBugForm(self):
        """Override this method in base classes to show the filebug form."""
        raise NotImplementedError

    @property
    def inline_filebug_base_url(self):
        """Return the base URL for the current request.

        This allows us to build URLs in Javascript without guessing at
        domains.
        """
        return self.request.getRootURL(None)

    @property
    def inline_filebug_form_url(self):
        """Return the URL to the inline filebug form.

        If a token was passed to this view, it will be be passed through
        to the inline bug filing form via the returned URL.
        """
        url = canonical_url(self.context, view_name='+filebug-inline-form')
        if self.extra_data_token is not None:
            url = urlappend(url, self.extra_data_token)
        return url

    @property
    def duplicate_search_url(self):
        """Return the URL to the inline duplicate search view."""
        url = canonical_url(self.context, view_name='+filebug-show-similar')
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

        self.extra_data_token = name
        if self.extra_data_processing_job is None:
            # The URL might be mistyped, or the blob has expired.
            # XXX: Bjorn Tillenius 2006-01-15:
            #      We should handle this case better, since a user might
            #      come to this page when finishing his account
            #      registration. In that case we should inform the user
            #      that the blob has expired.
            raise NotFound(self, name, request=request)
        else:
            self.extra_data = self.extra_data_processing_job.getFileBugData()

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
        """Return the first bugtask from this bug that's relevant in the
        current context.

        This is a pragmatic function, not general purpose. It tries to
        find a bugtask that can be used to pretty-up the page, making
        it more user-friendly and informative. It's not concerned by
        total accuracy, and will return the first 'relevant' bugtask
        it finds even if there are other candidates. Be warned!
        """
        context = self.context

        if IProjectGroup.providedBy(context):
            contexts = set(context.products)
        else:
            contexts = [context]

        for bugtask in bug.bugtasks:
            if bugtask.target in contexts or bugtask.pillar in contexts:
                return bugtask
        return None

    @property
    def bugtarget(self):
        """The bugtarget we're currently assuming.

        The same as the context.
        """
        return self.context

    @property
    def bug_reporting_guidelines(self):
        """Guidelines for filing bugs in the current context.

        Returns a list of dicts, with each dict containing values for
        "preamble" and "content".
        """

        def target_name(target):
            # IProjectGroup can be considered the target of a bug during
            # the bug filing process, but does not extend IBugTarget
            # and ultimately cannot actually be the target of a
            # bug. Hence this function to determine a suitable
            # name/title to display. Hurrumph.
            if IBugTarget.providedBy(target):
                return target.bugtargetdisplayname
            else:
                return target.title

        guidelines = []
        context = self.bugtarget
        if context is not None:
            content = context.bug_reporting_guidelines
            if content is not None and len(content) > 0:
                guidelines.append({
                        "source": target_name(context),
                        "content": content,
                        })
            # Distribution source packages are shown with both their
            # own reporting guidelines and those of their
            # distribution.
            if IDistributionSourcePackage.providedBy(context):
                distribution = context.distribution
                content = distribution.bug_reporting_guidelines
                if content is not None and len(content) > 0:
                    guidelines.append({
                            "source": target_name(distribution),
                            "content": content,
                            })
        return guidelines

    default_bug_reported_acknowledgement = "Thank you for your bug report."

    def getAcknowledgementMessage(self, context):
        """An acknowlegement message displayed to the user."""
        # If a given context doesnot have a custom message, we go up in the
        # "object hierachy" until we find one. If no cusotmized messages
        # exist for any conext, a default message is returned.
        #
        # bug_reported_acknowledgement is defined as a "real" property
        # for IDistribution, IDistributionSourcePackage, IProduct and
        # IProjectGroup. Other IBugTarget implementations inherit this
        # property from their parents. For these classes, we can directly
        # try to find a custom message farther up in the hierarchy.
        message = context.bug_reported_acknowledgement
        if message is not None and len(message.strip()) > 0:
            return message
        next_context = None
        if IProductSeries.providedBy(context):
            # we don't need to look at
            # context.product.bug_reported_acknowledgement because a
            # product series inherits this property from the product.
            next_context = context.product.project
        elif IProduct.providedBy(context):
            next_context = context.project
        elif IDistributionSourcePackage.providedBy(context):
            next_context = context.distribution
        # IDistroseries and ISourcePackage inherit
        # bug_reported_acknowledgement from their IDistribution, so we
        # don't need to look up this property in IDistribution.
        # IDistribution and IProjectGroup don't have any parents.
        elif (IDistribution.providedBy(context) or
              IProjectGroup.providedBy(context) or
              IDistroSeries.providedBy(context) or
              ISourcePackage.providedBy(context)):
            pass
        else:
            raise TypeError("Unexpected bug target: %r" % context)
        if next_context is not None:
            return self.getAcknowledgementMessage(next_context)
        return self.default_bug_reported_acknowledgement

    @cachedproperty
    def extra_data_processing_job(self):
        """Return the ProcessApportBlobJob for a given BLOB token."""
        if self.extra_data_token is None:
            # If there's no extra data token, don't bother looking for a
            # ProcessApportBlobJob.
            return None

        try:
            return getUtility(IProcessApportBlobJobSource).getByBlobUUID(
                self.extra_data_token)
        except SQLObjectNotFound:
            return None

    @property
    def extra_data_to_process(self):
        """Return True if there is extra data to process."""
        apport_processing_job = self.extra_data_processing_job
        if apport_processing_job is None:
            return False
        elif apport_processing_job.job.status == JobStatus.COMPLETED:
            return False
        else:
            return True


class FileBugInlineFormView(FileBugViewBase):
    """A browser view for displaying the inline filebug form."""
    schema = IBugAddForm


class FileBugAdvancedView(FileBugViewBase):
    """Browser view for filing a bug.

    This view exists only to redirect from +filebug-advanced to +filebug.
    """

    def initialize(self):
        filebug_url = canonical_url(
            self.context, rootsite='bugs', view_name='+filebug')
        self.request.response.redirect(
            filebug_url, status=HTTP_MOVED_PERMANENTLY)


class FilebugShowSimilarBugsView(FileBugViewBase):
    """A view for showing possible dupes for a bug.

    This view will only be used to populate asynchronously-driven parts
    of a page.
    """
    schema = IBugAddForm

    # XXX: Brad Bollenbach 2006-10-04: This assignment to actions is a
    # hack to make the action decorator Just Work across inheritance.
    actions = FileBugViewBase.actions
    custom_widget('title', TextWidget, displayWidth=40)
    custom_widget('tags', BugTagsWidget)

    _MATCHING_BUGS_LIMIT = 10
    show_summary_in_results = False

    @property
    def action_url(self):
        """Return the +filebug page as the action URL.

        This enables better validation error handling,
        since the form is always used inline on the +filebug page.
        """
        url = '%s/+filebug' % canonical_url(self.context)
        if self.extra_data_token is not None:
            url = urlappend(url, self.extra_data_token)
        return url

    @property
    def search_context(self):
        """Return the context used to search for similar bugs."""
        return self.context

    @property
    def search_text(self):
        """Return the search string entered by the user."""
        return self.request.get('title')

    @cachedproperty
    def similar_bugs(self):
        """Return the similar bugs based on the user search."""
        title = self.search_text
        if not title:
            return []
        search_context = self.search_context
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
        matching_bugs = getUtility(IBugSet).getDistinctBugsForBugTasks(
            matching_bugtasks, self.user, self._MATCHING_BUGS_LIMIT)
        return matching_bugs

    @property
    def show_duplicate_list(self):
        """Return whether or not to show the duplicate list.

        We only show the dupes if:
          - The context uses Malone AND
          - There are dupes to show AND
          - There are no widget errors.
        """
        return (
            self.contextUsesMalone and
            len(self.similar_bugs) > 0 and
            len(self.widget_errors) == 0)


class FileBugGuidedView(FilebugShowSimilarBugsView):

    _SEARCH_FOR_DUPES = ViewPageTemplateFile(
        "../templates/bugtarget-filebug-search.pt")
    _FILEBUG_FORM = ViewPageTemplateFile(
        "../templates/bugtarget-filebug-submit-bug.pt")

    # XXX 2009-07-17 Graham Binns
    #     As above, this assignment to actions is to make sure that the
    #     actions from the ancestor views are preserved, otherwise they
    #     get nuked.
    actions = FilebugShowSimilarBugsView.actions
    template = _SEARCH_FOR_DUPES

    focused_element_id = 'field.title'
    show_summary_in_results = True

    def initialize(self):
        FilebugShowSimilarBugsView.initialize(self)
        if self.redirect_ubuntu_filebug:
            # The user is trying to file a new Ubuntu bug via the web
            # interface and without using apport. Redirect to a page
            # explaining the preferred bug-filing procedure.
            self.request.response.redirect(
                config.malone.ubuntu_bug_filing_url)

    @safe_action
    @action("Continue", name="search", validator="validate_search")
    def search_action(self, action, data):
        """Search for similar bug reports."""
        # Don't give focus to any widget, to ensure that the browser
        # won't scroll past the "possible duplicates" list.
        self.initial_focus_widget = None
        return self.showFileBugForm()

    @property
    def search_context(self):
        """Return the context used to search for similar bugs."""
        if IDistributionSourcePackage.providedBy(self.context):
            return self.context

        search_context = self.getMainContext()
        if IProjectGroup.providedBy(search_context):
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

    @property
    def search_text(self):
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
    """Guided filebug pages for IProjectGroup."""

    # Make inheriting the base class' actions work.
    actions = FileBugGuidedView.actions
    schema = IProjectGroupBugAddForm

    @cachedproperty
    def products_using_malone(self):
        return [
            product for product in self.context.products
            if product.bug_tracking_usage == ServiceUsage.LAUNCHPAD]

    @property
    def default_product(self):
        if len(self.products_using_malone) > 0:
            return self.products_using_malone[0]
        else:
            return None

    @property
    def inline_filebug_form_url(self):
        """Return the URL to the inline filebug form.

        If a token was passed to this view, it will be be passed through
        to the inline bug filing form via the returned URL.

        The URL returned will be the URL of the first of the current
        ProjectGroup's products, since that's the product that will be
        selected by default when the view is rendered.
        """
        url = canonical_url(
            self.default_product, view_name='+filebug-inline-form')
        if self.extra_data_token is not None:
            url = urlappend(url, self.extra_data_token)
        return url

    @property
    def duplicate_search_url(self):
        """Return the URL to the inline duplicate search view.

        The URL returned will be the URL of the first of the current
        ProjectGroup's products, since that's the product that will be
        selected by default when the view is rendered.
        """
        url = canonical_url(
            self.default_product, view_name='+filebug-show-similar')
        if self.extra_data_token is not None:
            url = urlappend(url, self.extra_data_token)
        return url

    def _getSelectedProduct(self):
        """Return the product that's selected."""
        assert self.widgets['product'].hasValidInput(), (
            "This method should be called only when we know which"
            " product the user selected.")
        return self.widgets['product'].getInputValue()

    def getSecurityContext(self):
        """See FileBugViewBase."""
        return self._getSelectedProduct()


class BugTargetBugListingView:
    """Helper methods for rendering bug listings."""

    @property
    def series_list(self):
        if IDistribution(self.context, None):
            series = self.context.series
        elif IProduct(self.context, None):
            series = self.context.series
        elif IDistroSeries(self.context, None):
            series = self.context.distribution.series
        elif IProductSeries(self.context, None):
            series = self.context.product.series
        else:
            raise AssertionError("series_list called with illegal context")
        return series

    @property
    def series_buglistings(self):
        """Return a buglisting for each series.

        The list is sorted newest series to oldest.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        series_buglistings = []
        for series in self.series_list:
            series_bug_count = series.open_bugtasks.count()
            if series_bug_count > 0:
                series_buglistings.append(
                    dict(
                        title=series.name,
                        url=canonical_url(series) + "/+bugs",
                        count=series_bug_count,
                        ))

        return series_buglistings

    @property
    def milestone_buglistings(self):
        """Return a buglisting for each milestone."""
        milestone_buglistings = []
        for series in self.series_list:
            for milestone in series.milestones:
                milestone_bug_count = milestone.open_bugtasks.count()
                if milestone_bug_count > 0:
                    milestone_buglistings.append(
                        dict(
                            title=milestone.name,
                            url=canonical_url(milestone),
                            count=milestone_bug_count,
                            ))
        return milestone_buglistings


class BugCountDataItem:
    """Data about bug count for a status."""

    def __init__(self, label, count, color):
        self.label = label
        self.count = count
        if color.startswith('#'):
            self.color = 'MochiKit.Color.Color.fromHexString("%s")' % color
        else:
            self.color = 'MochiKit.Color.Color["%sColor"]()' % color


class BugTargetBugsView(BugTaskSearchListingView, FeedsMixin):
    """View for the Bugs front page."""

    # We have a custom searchtext widget here so that we can set the
    # width of the search box properly.
    custom_widget('searchtext', NewLineToSpacesWidget, displayWidth=36)

    # Only include <link> tags for bug feeds when using this view.
    feed_types = (
        BugFeedLink,
        BugTargetLatestBugsFeedLink,
        )

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

    override_title_breadcrumbs = True

    @property
    def label(self):
        """The display label for the view."""
        return 'Bugs in %s' % self.context.title

    def initialize(self):
        BugTaskSearchListingView.initialize(self)
        bug_statuses_to_show = list(UNRESOLVED_BUGTASK_STATUSES)
        if IDistroSeries.providedBy(self.context):
            bug_statuses_to_show.append(BugTaskStatus.FIXRELEASED)

    @property
    def can_have_external_bugtracker(self):
        return (IProduct.providedBy(self.context)
                or IProductSeries.providedBy(self.context))

    @property
    def bug_tracking_usage(self):
        """Whether the context tracks bugs in launchpad.

        :returns: ServiceUsage enum value
        """
        service_usage = IServiceUsage(self.context)
        return service_usage.bug_tracking_usage

    @property
    def bugtracker(self):
        """Description of the context's bugtracker.

        :returns: str which may contain HTML.
        """
        if self.bug_tracking_usage == ServiceUsage.LAUNCHPAD:
            return 'Launchpad'
        elif self.external_bugtracker:
            return BugTrackerFormatterAPI(self.external_bugtracker).link(None)
        else:
            return 'None specified'

    @cachedproperty
    def hot_bugs_info(self):
        """Return a dict of the 10 hottest tasks and a has_more_bugs flag."""
        has_more_bugs = False
        params = BugTaskSearchParams(
            orderby='-heat', omit_dupes=True,
            user=self.user, status=any(*UNRESOLVED_BUGTASK_STATUSES))
        # Use 4x as many tasks as bugs that are needed to improve performance.
        bugtasks = self.context.searchTasks(params)[:40]
        hot_bugtasks = []
        hot_bugs = []
        for task in bugtasks:
            # Use hot_bugs list to ensure a bug is only listed once.
            if task.bug not in hot_bugs:
                if len(hot_bugtasks) < 10:
                    hot_bugtasks.append(task)
                    hot_bugs.append(task.bug)
                else:
                    has_more_bugs = True
                    break
        return {'has_more_bugs': has_more_bugs, 'bugtasks': hot_bugtasks}


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

    @property
    def official_tags(self):
        """Get the official tags to diplay."""
        official_tags = set(self.context.official_bug_tags)
        tags = [tag for tag in self.getUsedBugTagsWithURLs()
                if tag['tag'] in official_tags]
        used_tags = set(tag['tag'] for tag in tags)
        tags.sort(key=itemgetter('count'), reverse=True)
        for tag in sorted(official_tags - used_tags):
            tags.append(
                {'tag': tag, 'count': 0, 'url': self._getSearchURL(tag)})
        return tags

    @property
    def other_tags(self):
        """Get the unofficial tags to diplay."""
        official_tags = set(self.context.official_bug_tags)
        tags = [tag for tag in self.getUsedBugTagsWithURLs()
                if tag['tag'] not in official_tags]
        tags.sort(key=itemgetter('count'), reverse=True)
        return tags[:10]

    @property
    def tags_cloud_data(self):
        """The data for rendering a tags cloud"""
        official_tags = self.context.official_bug_tags
        tags = self.getUsedBugTagsWithURLs()
        other_tags = [tag for tag in tags if tag['tag'] not in official_tags]
        popular_tags = [tag['tag'] for tag in sorted(
            other_tags, key=itemgetter('count'), reverse=True)[:10]]
        tags = [
            tag for tag in tags
            if tag['tag'] in official_tags + popular_tags]
        all_tag_dicts = [tag['tag'] for tag in tags]
        for official_tag in official_tags:
            if official_tag not in all_tag_dicts:
                tags.append({
                    'tag': official_tag,
                    'count': 0,
                    'url': "+bugs?field.tag=%s" % urllib.quote(official_tag)})
        max_count = float(max([1] + [tag['count'] for tag in tags]))
        for tag in tags:
            if tag['tag'] in official_tags:
                if tag['count'] == 0:
                    tag['factor'] = 1.5
                else:
                    tag['factor'] = 1.5 + (tag['count'] / max_count)
            else:
                tag['factor'] = 1 + (tag['count'] / max_count)
        return sorted(tags, key=itemgetter('tag'))

    @property
    def show_manage_tags_link(self):
        """Should a link to a "manage official tags" page be shown?"""
        return (IOfficialBugTagTargetRestricted.providedBy(self.context) and
                check_permission('launchpad.BugSupervisor', self.context))


class OfficialBugTagsManageView(LaunchpadEditFormView):
    """View class for management of official bug tags."""

    schema = IOfficialBugTagTargetPublic
    custom_widget('official_bug_tags', LargeBugTagsWidget)

    @property
    def label(self):
        """The form label."""
        return 'Manage official bug tags for %s' % self.context.title

    @property
    def page_title(self):
        """The page title."""
        return self.label

    @action('Save', name='save')
    def save_action(self, action, data):
        """Action for saving new official bug tags."""
        self.context.official_bug_tags = data['official_bug_tags']
        self.next_url = canonical_url(self.context)

    @property
    def tags_js_data(self):
        """Return the JSON representation of the bug tags."""
        used_tags = dict(self.context.getUsedBugTagsWithOpenCounts(self.user))
        official_tags = list(self.context.official_bug_tags)
        return """<script type="text/javascript">
                      var used_bug_tags = %s;
                      var official_bug_tags = %s;
                      var valid_name_pattern = %s;
                  </script>
               """ % (
               dumps(used_tags),
               dumps(official_tags),
               dumps(valid_name_pattern.pattern))

    @property
    def cancel_url(self):
        """The URL the user is sent to when clicking the "cancel" link."""
        return canonical_url(self.context)


class BugsVHostBreadcrumb(Breadcrumb):
    rootsite = 'bugs'
    text = 'Bugs'


class BugsPatchesView(LaunchpadView):
    """View list of patch attachments associated with bugs."""

    @property
    def label(self):
        """The display label for the view."""
        if IPerson.providedBy(self.context):
            return 'Patch attachments for %s' % self.context.displayname
        else:
            return 'Patch attachments in %s' % self.context.displayname

    @property
    def patch_task_orderings(self):
        """The list of possible sort orderings for the patches view.

        The orderings are a list of tuples of the form:
          [(DisplayName, InternalOrderingName), ...]
        For example:
          [("Patch age", "-latest_patch_uploaded"),
           ("Importance", "-importance"),
           ...]
        """
        orderings = [("patch age", "-latest_patch_uploaded"),
                     ("importance", "-importance"),
                     ("status", "status"),
                     ("oldest first", "datecreated"),
                     ("newest first", "-datecreated")]
        targetname = self.targetName()
        if targetname is not None:
            # Lower case for consistency with the other orderings.
            orderings.append((targetname.lower(), "targetname"))
        return orderings

    def batchedPatchTasks(self):
        """Return a BatchNavigator for bug tasks with patch attachments."""
        orderby = self.request.get("orderby", "-latest_patch_uploaded")
        if orderby not in [x[1] for x in self.patch_task_orderings]:
            raise UnexpectedFormData(
                "Unexpected value for field 'orderby': '%s'" % orderby)
        return BatchNavigator(
            self.context.searchTasks(
                None, user=self.user, order_by=orderby,
                status=UNRESOLVED_BUGTASK_STATUSES,
                omit_duplicates=True, has_patch=True),
            self.request)

    def targetName(self):
        """Return the name of the current context's target type, or None.

        The name is something like "Package" or "Project" (meaning
        Product); it is intended to be appropriate to use as a column
        name in a web page, for example.  If no target type is
        appropriate for the current context, then return None.
        """
        if (IDistribution.providedBy(self.context) or
            IDistroSeries.providedBy(self.context)):
            return "Package"
        elif (IProjectGroup.providedBy(self.context) or
              IPerson.providedBy(self.context)):
            # In the case of an IPerson, the target column can vary
            # row-by-row, showing both packages and products.  We
            # decided to go with the table header "Project" for both,
            # as its meaning is broad and could conceivably cover
            # packages too.  We also considered "Target", but rejected
            # it because it's used as a verb elsewhere in Launchpad's
            # UI, with a totally different meaning.  If anyone can
            # think of a better term than "Project", please JFDI here.
            return "Project"  # "Project" meaning Product, of course
        else:
            return None

    def patchAge(self, patch):
        """Return a timedelta object for the age of a patch attachment."""
        now = datetime.now(timezone('UTC'))
        return now - patch.message.datecreated

    def proxiedUrlForLibraryFile(self, patch):
        """Return the proxied download URL for a Librarian file."""
        return ProxiedLibraryFileAlias(patch.libraryfile, patch).http_url
