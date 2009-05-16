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
    "OfficialBugTagsManageView",
    "ProjectFileBugGuidedView",
    "ProjectFileBugAdvancedView",
    ]

import cgi
from cStringIO import StringIO
from email import message_from_string
from operator import itemgetter
from simplejson import dumps
import tempfile
import urllib

from zope.app.form.browser import TextWidget
from zope.app.form.interfaces import InputErrors
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from z3c.ptcompat import ViewPageTemplateFile

from lazr.lifecycle.event import ObjectCreatedEvent

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.browser.bugtask import BugTaskSearchListingView
from canonical.launchpad.browser.feeds import (
    BugFeedLink, BugTargetLatestBugsFeedLink, FeedsMixin,
    PersonLatestBugsFeedLink)
from canonical.launchpad.interfaces.bugsupervisor import IHasBugSupervisor
from canonical.launchpad.interfaces.bugtarget import (
    IBugTarget, IOfficialBugTagTargetPublic, IOfficialBugTagTargetRestricted)
from canonical.launchpad.interfaces.bugtask import (
    BugTaskStatus, IBugTaskSet, UNRESOLVED_BUGTASK_STATUSES)
from canonical.launchpad.interfaces.launchpad import (
    IHasExternalBugTracker, ILaunchpadUsage)
from canonical.launchpad.interfaces import (
    CreateBugParams, IBug, IBugAddForm, IDistribution,
    IDistributionSourcePackage, IDistroSeries, IFrontPageBugAddForm,
    ILaunchBag, ILaunchpadCelebrities, IMaloneApplication, IProduct,
    IProductSeries, IProject, IProjectBugAddForm, ITemporaryStorageManager,
    NotFoundError)
from canonical.launchpad.webapp import (
    LaunchpadEditFormView, LaunchpadFormView, LaunchpadView, action,
    canonical_url, custom_widget, safe_action, urlappend)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.tales import BugTrackerFormatterAPI
from canonical.widgets.bug import BugTagsWidget, LargeBugTagsWidget
from canonical.widgets.launchpadtarget import LaunchpadTargetWidget
from canonical.launchpad.validators.name import valid_name_pattern
from canonical.launchpad.webapp.menu import structured

from lp.registry.vocabularies import ValidPersonOrTeamVocabulary


class FileBugDataParser:
    """Parser for a message containing extra bug information.

    Applications like Apport upload such messages, before filing the
    bug.
    """

    def __init__(self, blob_file):
        self.blob_file = blob_file
        self.headers = {}
        self._buffer = ''
        self.extra_description = None
        self.comments = []
        self.attachments = []
        self.BUFFER_SIZE = 8192

    def _consumeBytes(self, end_string):
        """Read bytes from the message up to the end_string.

        The end_string is included in the output.

        If end-of-file is reached, '' is returned.
        """
        while end_string not in self._buffer:
            data = self.blob_file.read(self.BUFFER_SIZE)
            self._buffer += data
            if len(data) < self.BUFFER_SIZE:
                # End of file.
                if end_string not in self._buffer:
                    # If the end string isn't present, we return
                    # everything.
                    buffer = self._buffer
                    self._buffer = ''
                    return buffer
                break
        end_index = self._buffer.index(end_string)
        bytes = self._buffer[:end_index+len(end_string)]
        self._buffer = self._buffer[end_index+len(end_string):]
        return bytes

    def readHeaders(self):
        """Read the next set of headers of the message."""
        header_text = self._consumeBytes('\n\n')
        # Use the email package to return a dict-like object of the
        # headers, so we don't have to parse the text ourselves.
        return message_from_string(header_text)

    def readLine(self):
        """Read a line of the message."""
        data = self._consumeBytes('\n')
        if data == '':
            raise AssertionError('End of file reached.')
        return data

    def _setDataFromHeaders(self, data, headers):
        """Set the data attributes from the message headers."""
        if 'Subject' in headers:
            data.initial_summary = unicode(headers['Subject'])
        if 'Tags' in headers:
            tags_string = unicode(headers['Tags'])
            data.initial_tags = tags_string.lower().split()
        if 'Private' in headers:
            private = headers['Private']
            if private.lower() == 'yes':
                data.private = True
            elif private.lower() == 'no':
                data.private = False
            else:
                # If the value is anything other than yes or no we just
                # ignore it as we cannot currently give the user an error
                pass
        if 'Subscribers' in headers:
            subscribers_string = unicode(headers['Subscribers'])
            data.subscribers = subscribers_string.lower().split()

    def parse(self):
        """Parse the message and  return a FileBugData instance.

            * The Subject header is the initial bug summary.
            * The Tags header specifies the initial bug tags.
            * The Private header sets the visibility of the bug.
            * The Subscribers header specifies additional initial subscribers
            * The first inline part will be added to the description.
            * All other inline parts will be added as separate comments.
            * All attachment parts will be added as attachment.

        When parsing each part of the message is stored in a temporary
        file on the file system. After using the returned data,
        removeTemporaryFiles() must be called.
        """
        headers = self.readHeaders()
        data = FileBugData()
        self._setDataFromHeaders(data, headers)

        # The headers is a Message instance.
        boundary = "--" + headers.get_param("boundary")
        line = self.readLine()
        while not line.startswith(boundary + '--'):
            part_file = tempfile.TemporaryFile()
            part_headers = self.readHeaders()
            content_encoding = part_headers.get('Content-Transfer-Encoding')
            if content_encoding is not None and content_encoding != 'base64':
                raise AssertionError(
                    "Unknown encoding: %r." % content_encoding)
            line = self.readLine()
            while not line.startswith(boundary):
                # Decode the file.
                if content_encoding is not None:
                    line = line.decode(content_encoding)
                part_file.write(line)
                line = self.readLine()
            # Prepare the file for reading.
            part_file.seek(0)
            disposition = part_headers['Content-Disposition']
            disposition = disposition.split(';')[0]
            disposition = disposition.strip()
            if disposition == 'inline':
                assert part_headers.get_content_type() == 'text/plain', (
                    "Inline parts have to be plain text.")
                charset = part_headers.get_content_charset()
                assert charset, (
                    "A charset has to be specified for text parts.")
                inline_content = part_file.read().rstrip()
                part_file.close()
                inline_content = inline_content.decode(charset)

                if data.extra_description is None:
                    # The first inline part is extra description.
                    data.extra_description = inline_content
                else:
                    data.comments.append(inline_content)
            elif disposition == 'attachment':
                attachment = dict(
                    filename=unicode(part_headers.get_filename().strip("'")),
                    content_type=unicode(part_headers['Content-type']),
                    content=part_file)
                if 'Content-Description' in part_headers:
                    attachment['description'] = unicode(
                        part_headers['Content-Description'])
                else:
                    attachment['description'] = attachment['filename']
                data.attachments.append(attachment)
            else:
                # If the message include other disposition types,
                # simply ignore them. We don't want to break just
                # because some extra information is included.
                continue
        return data


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
                       'bug_already_reported_as', 'filecontent', 'patch',
                       'attachment_description']
        if (IDistribution.providedBy(context) or
            IDistributionSourcePackage.providedBy(context)):
            field_names.append('packagename')
        elif IMaloneApplication.providedBy(context):
            field_names.append('bugtarget')
        elif IProject.providedBy(context):
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
                self.setFieldError("packagename", 
                                   "Please enter a package name")

        # If we've been called from the frontpage filebug forms we must check
        # that whatever product or distro is having a bug filed against it
        # actually uses Malone for its bug tracking.
        product_or_distro = self.getProductOrDistroFromContext()
        if (product_or_distro is not None and
            not product_or_distro.official_malone):
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

        # Tell everyone.
        notify(ObjectCreatedEvent(bug))

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
                bug.addAttachment(
                    owner=self.user, data=attachment['content'],
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
                    bug.subscribe(person, self.user)
                    notifications.append(
                        '%s has been subscribed to this bug.' %
                        person.displayname)

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

        if bug.isUserAffected(self.user):
            self.request.response.addNotification(
                "This bug is already marked as affecting you.")
        else:
            bug.markUserAffected(self.user)
            self.request.response.addNotification(
                "This bug has been marked as affecting you.")

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
            extra_bug_data.file_alias.open()
            self.data_parser = FileBugDataParser(extra_bug_data.file_alias)
            self.extra_data = self.data_parser.parse()
            extra_bug_data.file_alias.close()
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
        """Return the first bugtask from this bug that's relevant in the
        current context.

        This is a pragmatic function, not general purpose. It tries to
        find a bugtask that can be used to pretty-up the page, making
        it more user-friendly and informative. It's not concerned by
        total accuracy, and will return the first 'relevant' bugtask
        it finds even if there are other candidates. Be warned!
        """
        context = self.context

        if IProject.providedBy(context):
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
            # IProject can be considered the target of a bug during
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


class FilebugShowSimilarBugsView(FileBugViewBase):
    """A view for showing possible dupes for a bug.

    This view will only be used to populate asynchronously-driven parts
    of a page.
    """
    schema = IBugAddForm

    _MATCHING_BUGS_LIMIT = 10

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
        matching_bugs = []
        matching_bugs_limit = self._MATCHING_BUGS_LIMIT
        for bugtask in matching_bugtasks[:4*matching_bugs_limit]:
            bug = bugtask.bug
            duplicateof = bug.duplicateof
            if duplicateof is not None:
                bug = duplicateof
            if not check_permission('launchpad.View', bug):
                continue
            if bug not in matching_bugs:
                matching_bugs.append(bug)
                if len(matching_bugs) >= matching_bugs_limit:
                    break

        return matching_bugs


class FileBugGuidedView(FilebugShowSimilarBugsView):
    # XXX: Brad Bollenbach 2006-10-04: This assignment to actions is a
    # hack to make the action decorator Just Work across inheritance.
    actions = FileBugViewBase.actions
    custom_widget('title', TextWidget, displayWidth=40)
    custom_widget('tags', BugTagsWidget)

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

    @property
    def search_context(self):
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
    def most_common_bugs(self):
        """Return a list of the most duplicated bugs."""
        search_context = self.search_context
        if search_context is None:
            return []
        else:
            return search_context.getMostCommonBugs(
                self.user, limit=self._MATCHING_BUGS_LIMIT)

    @property
    def found_possible_duplicates(self):
        return self.similar_bugs or self.most_common_bugs

    @property
    def search_text(self):
        """Return the search string entered by the user."""
        try:
            return self.widgets['title'].getInputValue()
        except InputErrors:
            return None

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

    @property
    def bugtarget(self):
        """The bugtarget we're currently assuming.

        This needs to be obtained from form data because we're on the
        front page, and not already within a product/distro/etc
        context.
        """
        if self.widgets['bugtarget'].hasValidInput():
            return self.widgets['bugtarget'].getInputValue()
        else:
            return None

    def getProductOrDistroFromContext(self):
        """Return the product or distribution relative to the context.

        For instance, if the context is an IDistroSeries, return the
        distribution related to it. This method will return None if the
        context is not related to a product or a distro.
        """
        # We need to find a product or distribution from what we've had
        # submitted to us.
        context = self.bugtarget
        if context is None:
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


class FrontPageFileBugAdvancedView(FrontPageFileBugMixin,
                                   FileBugAdvancedView):
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
            self.setFieldError(
                'bugtarget',
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


class BugTargetBugsView(BugTaskSearchListingView, FeedsMixin):
    """View for the Bugs front page."""

    # Only include <link> tags for bug feeds when using this view.
    feed_types = (
        BugFeedLink,
        BugTargetLatestBugsFeedLink,
        PersonLatestBugsFeedLink,
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

    def initialize(self):
        BugTaskSearchListingView.initialize(self)
        bug_statuses_to_show = list(UNRESOLVED_BUGTASK_STATUSES)
        if IDistroSeries.providedBy(self.context):
            bug_statuses_to_show.append(BugTaskStatus.FIXRELEASED)
        bug_counts = sorted(self.context.getBugCounts(
            self.user, bug_statuses_to_show).items())
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

    @property
    def uses_launchpad_bugtracker(self):
        """Whether this distro or product tracks bugs in launchpad.

        :returns: boolean
        """
        launchpad_usage = ILaunchpadUsage(self.context)
        return launchpad_usage.official_malone

    @property
    def external_bugtracker(self):
        """External bug tracking system designated for the context.

        :returns: `IBugTracker` or None
        """
        has_external_bugtracker = IHasExternalBugTracker(self.context, None)
        if has_external_bugtracker is None:
            return None
        else:
            return has_external_bugtracker.getExternalBugTracker()

    @property
    def bugtracker(self):
        """Description of the context's bugtracker.

        :returns: str which may contain HTML.
        """
        if self.uses_launchpad_bugtracker:
            return 'Launchpad'
        elif self.external_bugtracker:
            return BugTrackerFormatterAPI(self.external_bugtracker).link(None)
        else:
            return 'None specified'


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
    def show_manage_tags_link(self):
        """Should a link to a "manage official tags" page be shown?"""
        return (IOfficialBugTagTargetRestricted.providedBy(self.context) and
                check_permission('launchpad.Edit', self.context))


class OfficialBugTagsManageView(LaunchpadEditFormView):
    """View class for management of official bug tags."""

    schema = IOfficialBugTagTargetPublic
    custom_widget('official_bug_tags', LargeBugTagsWidget)

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

