# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""IBug related view classes."""

__metaclass__ = type

__all__ = [
    'BugContextMenu',
    'BugEditView',
    'BugFacets',
    'BugMarkAsAffectingUserView',
    'BugMarkAsDuplicateView',
    'BugNavigation',
    'BugSecrecyEditView',
    'BugSetNavigation',
    'BugSubscriptionPortletDetails',
    'BugTextView',
    'BugURL',
    'BugView',
    'BugViewMixin',
    'BugWithoutContextView',
    'DeprecatedAssignedBugsView',
    'MaloneView',
    ]

from datetime import (
    datetime,
    timedelta,
    )
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import re

from lazr.enum import (
    EnumeratedType,
    Item,
    )
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lazr.restful import (
    EntryResource,
    ResourceJSONEncoder,
    )
from lazr.restful.interface import copy_field
from lazr.restful.interfaces import IJSONRequestCache
import pytz
from simplejson import dumps
from zope import formlib
from zope.app.form.browser import TextWidget
from zope.component import getUtility
from zope.event import notify
from zope.interface import (
    implements,
    Interface,
    providedBy,
    )
from zope.schema import Choice
from zope.security.interfaces import Unauthorized

from canonical.launchpad import _
from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.searchbuilder import (
    any,
    greater_than,
    )
from canonical.launchpad.webapp import (
    canonical_url,
    ContextMenu,
    LaunchpadView,
    Link,
    Navigation,
    StandardLaunchpadFacets,
    stepthrough,
    structured,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import (
    ICanonicalUrlData,
    ILaunchBag,
    )
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.app.errors import NotFoundError
from lp.app.widgets.itemswidgets import LaunchpadRadioWidgetWithDescription
from lp.app.widgets.project import ProjectScopeWidget
from lp.bugs.browser.widgets.bug import BugTagsWidget
from lp.bugs.enum import BugNotificationLevel
from lp.bugs.interfaces.bug import (
    IBug,
    IBugSet,
    )
from lp.bugs.interfaces.bugattachment import (
    BugAttachmentType,
    IBugAttachmentSet,
    )
from lp.bugs.interfaces.bugnomination import IBugNominationSet
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    BugTaskStatus,
    IFrontPageBugTaskSearch,
    )
from lp.bugs.interfaces.bugwatch import IBugWatchSet
from lp.bugs.interfaces.cve import ICveSet
from lp.bugs.mail.bugnotificationbuilder import format_rfc2822_date
from lp.bugs.model.structuralsubscription import (
    get_structural_subscriptions_for_bug,
    )
from lp.bugs.model.personsubscriptioninfo import PersonSubscriptions
from lp.services.fields import DuplicateBug
from lp.services.propertycache import cachedproperty


class BugNavigation(Navigation):
    """Navigation for the `IBug`."""
    # It would be easier, since there is no per-bug sequence for a BugWatch
    # and we have to leak the BugWatch.id anyway, to hang bugwatches off a
    # global /bugwatchs/nnnn

    # However, we want in future to have them at /bugs/nnn/+watch/p where p
    # is not the BugWatch.id but instead a per-bug sequence number (1, 2,
    # 3...) for the 1st, 2nd and 3rd watches added for this bug,
    # respectively. So we are going ahead and hanging this off the bug to
    # which it belongs as a first step towards getting the basic URL schema
    # correct.

    usedfor = IBug

    @stepthrough('+watch')
    def traverse_watches(self, name):
        """Retrieve a BugWatch by name."""
        if name.isdigit():
            # in future this should look up by (bug.id, watch.seqnum)
            return getUtility(IBugWatchSet)[name]

    @stepthrough('+subscription')
    def traverse_subscriptions(self, person_name):
        """Retrieve a BugSubscription by person name."""
        for subscription in self.context.subscriptions:
            if subscription.person.name == person_name:
                return subscription

    @stepthrough('attachments')
    def traverse_attachments(self, name):
        """Retrieve a BugAttachment by ID.

        If an attachment is found, redirect to its canonical URL.
        """
        if name.isdigit():
            attachment = getUtility(IBugAttachmentSet)[name]
            if attachment is not None and attachment.bug == self.context:
                return self.redirectSubTree(
                    canonical_url(attachment), status=301)

    @stepthrough('+attachment')
    def traverse_attachment(self, name):
        """Retrieve a BugAttachment by ID.

        Only return a attachment if it is related to this bug.
        """
        if name.isdigit():
            attachment = getUtility(IBugAttachmentSet)[name]
            if attachment is not None and attachment.bug == self.context:
                return attachment

    @stepthrough('nominations')
    def traverse_nominations(self, nomination_id):
        """Traverse to a nomination by id."""
        if nomination_id.isdigit():
            try:
                return getUtility(IBugNominationSet).get(nomination_id)
            except NotFoundError:
                return None


class BugFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an `IBug`.

    However, we never show this, but it does apply to things like
    bug nominations, by 'acquisition'.
    """

    usedfor = IBug

    enable_only = []


class BugSetNavigation(Navigation):
    """Navigation for the IBugSet."""
    usedfor = IBugSet

    @stepthrough('+text')
    def text(self, name):
        """Retrieve a bug by name."""
        try:
            return getUtility(IBugSet).getByNameOrID(name)
        except (NotFoundError, ValueError):
            return None


class BugContextMenu(ContextMenu):
    """Context menu of actions that can be performed upon a Bug."""
    usedfor = IBug
    links = [
        'editdescription', 'markduplicate', 'visibility', 'addupstream',
        'adddistro', 'subscription', 'addsubscriber', 'editsubscriptions',
        'addcomment', 'nominate', 'addbranch', 'linktocve', 'unlinkcve',
        'createquestion', 'mute_subscription', 'removequestion',
        'activitylog', 'affectsmetoo']

    def __init__(self, context):
        # Always force the context to be the current bugtask, so that we don't
        # have to duplicate menu code.
        ContextMenu.__init__(self, getUtility(ILaunchBag).bugtask)

    @cachedproperty
    def editdescription(self):
        """Return the 'Edit description/tags' Link."""
        text = 'Update description / tags'
        return Link('+edit', text, icon='edit')

    def visibility(self):
        """Return the 'Set privacy/security' Link."""
        text = 'Change privacy/security'
        return Link('+secrecy', text)

    def markduplicate(self):
        """Return the 'Mark as duplicate' Link."""
        return Link('+duplicate', 'Mark as duplicate')

    def addupstream(self):
        """Return the 'lso affects project' Link."""
        text = 'Also affects project'
        return Link('+choose-affected-product', text, icon='add')

    def adddistro(self):
        """Return the 'Also affects distribution' Link."""
        text = 'Also affects distribution'
        return Link('+distrotask', text, icon='add')

    def subscription(self):
        """Return the 'Subscribe/Unsubscribe' Link."""
        user = getUtility(ILaunchBag).user
        if user is None:
            text = 'Subscribe/Unsubscribe'
            icon = 'edit'
        elif user is not None and (
            self.context.bug.isSubscribed(user) or
            self.context.bug.isSubscribedToDupes(user)):
            if self.context.bug.isMuted(user):
                text = 'Subscribe'
                icon = 'add'
            else:
                text = 'Edit subscription'
                icon = 'edit'
        else:
            text = 'Subscribe'
            icon = 'add'
        return Link('+subscribe', text, icon=icon, summary=(
                'When you are subscribed, Launchpad will email you each time '
                'this bug changes'))

    def addsubscriber(self):
        """Return the 'Subscribe someone else' Link."""
        text = 'Subscribe someone else'
        return Link(
            '+addsubscriber', text, icon='add', summary=(
                'Launchpad will email that person whenever this bugs '
                'changes'))

    def editsubscriptions(self):
        """Return the 'Edit subscriptions' Link."""
        text = 'Edit bug mail'
        return Link(
            '+subscriptions', text, icon='edit', summary=(
                'View and change your subscriptions to this bug'))

    def mute_subscription(self):
        """Return the 'Mute subscription' Link."""
        user = getUtility(ILaunchBag).user
        if self.context.bug.isMuted(user):
            text = "Unmute bug mail"
            icon = 'unmute'
        else:
            text = "Mute bug mail"
            icon = 'mute'

        return Link(
            '+mute', text, icon=icon, summary=(
                "Mute this bug so that you will not receive emails "
                "about it."))

    def nominate(self):
        """Return the 'Target/Nominate for series' Link."""
        launchbag = getUtility(ILaunchBag)
        target = launchbag.product or launchbag.distribution
        if check_permission("launchpad.Driver", target):
            text = "Target to series"
            return Link('+nominate', text, icon='milestone')
        elif (check_permission("launchpad.BugSupervisor", target) or
            self.user is None):
            text = 'Nominate for series'
            return Link('+nominate', text, icon='milestone')
        else:
            return Link('+nominate', '', enabled=False, icon='milestone')

    def addcomment(self):
        """Return the 'Comment or attach file' Link."""
        text = 'Add attachment or patch'
        return Link('+addcomment', text, icon='add')

    def addbranch(self):
        """Return the 'Add branch' Link."""
        text = 'Link a related branch'
        return Link('+addbranch', text, icon='add')

    def linktocve(self):
        """Return the 'Link to CVE' Link."""
        text = structured(
            'Link to '
            '<abbr title="Common Vulnerabilities and Exposures Index">'
            'CVE'
            '</abbr>')
        return Link('+linkcve', text, icon='add')

    def unlinkcve(self):
        """Return 'Remove CVE link' Link."""
        enabled = self.context.bug.has_cves
        text = 'Remove CVE link'
        return Link('+unlinkcve', text, icon='remove', enabled=enabled)

    @property
    def _bug_question(self):
        return self.context.bug.getQuestionCreatedFromBug()

    def createquestion(self):
        """Create a question from this bug."""
        text = 'Convert to a question'
        enabled = self._bug_question is None
        return Link('+create-question', text, enabled=enabled, icon='add')

    def removequestion(self):
        """Remove the created question from this bug."""
        text = 'Convert back to a bug'
        enabled = self._bug_question is not None
        return Link('+remove-question', text, enabled=enabled, icon='remove')

    def activitylog(self):
        """Return the 'Activity log' Link."""
        text = 'See full activity log'
        return Link('+activity', text)

    def affectsmetoo(self):
        """Return the 'This bug affects me too' link."""
        enabled = getUtility(ILaunchBag).user is not None
        return Link('+affectsmetoo', 'change', enabled=enabled)


class MaloneView(LaunchpadFormView):
    """The Bugs front page."""

    custom_widget('searchtext', TextWidget, displayWidth=50)
    custom_widget('scope', ProjectScopeWidget)
    schema = IFrontPageBugTaskSearch
    field_names = ['searchtext', 'scope']

    # Test: standalone/xx-slash-malone-slash-bugs.txt
    error_message = None

    page_title = 'Launchpad Bugs'

    @property
    def target_css_class(self):
        """The CSS class for used in the target widget."""
        if self.target_error:
            return 'error'
        else:
            return None

    @property
    def target_error(self):
        """The error message for the target widget."""
        return self.getFieldError('scope')

    def initialize(self):
        """Initialize the view to handle the request."""
        LaunchpadFormView.initialize(self)
        bug_id = self.request.form.get("id")
        if bug_id:
            self._redirectToBug(bug_id)
        elif self.widgets['scope'].hasInput():
            self._validate(action=None, data={})

    def _redirectToBug(self, bug_id):
        """Redirect to the specified bug id."""
        if not isinstance(bug_id, basestring):
            self.error_message = "Bug %r is not registered." % bug_id
            return
        if bug_id.startswith("#"):
            # Be nice to users and chop off leading hashes
            bug_id = bug_id[1:]
        try:
            bug = getUtility(IBugSet).getByNameOrID(bug_id)
        except NotFoundError:
            self.error_message = "Bug %r is not registered." % bug_id
        else:
            return self.request.response.redirect(canonical_url(bug))

    def getMostRecentlyFixedBugs(self, limit=5, when=None):
        """Return the ten most recently fixed bugs."""
        if when is None:
            when = datetime.now(pytz.timezone('UTC'))
        date_closed_limits = [
            timedelta(days=1),
            timedelta(days=7),
            timedelta(days=30),
            None,
        ]
        for date_closed_limit in date_closed_limits:
            fixed_bugs = []
            search_params = BugTaskSearchParams(
                self.user, status=BugTaskStatus.FIXRELEASED,
                orderby='-date_closed')
            if date_closed_limit is not None:
                search_params.date_closed = greater_than(
                    when - date_closed_limit)
            fixed_bugtasks = self.context.searchTasks(search_params)
            # XXX: Bjorn Tillenius 2006-12-13:
            #      We might end up returning less than :limit: bugs, but in
            #      most cases we won't, and '4*limit' is here to prevent
            #      this page from timing out in production. Later I'll fix
            #      this properly by selecting bugs instead of bugtasks.
            #      If fixed_bugtasks isn't sliced, it will take a long time
            #      to iterate over it, even over just 10, because
            #      Transaction.iterSelect() listifies the result.
            for bugtask in fixed_bugtasks[:4 * limit]:
                if bugtask.bug not in fixed_bugs:
                    fixed_bugs.append(bugtask.bug)
                    if len(fixed_bugs) >= limit:
                        return fixed_bugs
        return fixed_bugs

    def getCveBugLinkCount(self):
        """Return the number of links between bugs and CVEs there are."""
        return getUtility(ICveSet).getBugCveCount()


class BugViewMixin:
    """Mix-in class to share methods between bug and portlet views."""

    @cachedproperty
    def subscription_info(self):
        return IBug(self.context).getSubscriptionInfo()

    @cachedproperty
    def direct_subscribers(self):
        """Return the list of direct subscribers."""
        return self.subscription_info.direct_subscribers

    @cachedproperty
    def duplicate_subscribers(self):
        """Return the list of subscribers from duplicates.

        This includes all subscribers who are also direct or indirect
        subscribers.
        """
        return self.subscription_info.duplicate_subscribers

    def getSubscriptionClassForUser(self, subscribed_person):
        """Return a set of CSS class names based on subscription status.

        For example, "subscribed-false dup-subscribed-true".
        """
        if subscribed_person in self.duplicate_subscribers:
            dup_class = 'dup-subscribed-true'
        else:
            dup_class = 'dup-subscribed-false'

        if subscribed_person in self.direct_subscribers:
            return 'subscribed-true %s' % dup_class
        else:
            return 'subscribed-false %s' % dup_class

    @cachedproperty
    def _bug_attachments(self):
        """Get a dict of attachment type -> attachments list."""
        # Note that this is duplicated with get_comments_for_bugtask
        # if you are looking to consolidate things.
        result = {
            BugAttachmentType.PATCH: [],
            'other': [],
            }
        for attachment in self.context.attachments_unpopulated:
            info = {
                'attachment': attachment,
                'file': ProxiedLibraryFileAlias(
                    attachment.libraryfile, attachment),
                }
            if attachment.type == BugAttachmentType.PATCH:
                key = attachment.type
            else:
                key = 'other'
            result[key].append(info)
        return result

    @property
    def regular_attachments(self):
        """The list of bug attachments that are not patches."""
        return self._bug_attachments['other']

    @property
    def patches(self):
        """The list of bug attachments that are patches."""
        return self._bug_attachments[BugAttachmentType.PATCH]

    @property
    def current_bugtask(self):
        """Return the current `IBugTask`.

        'current' is determined by simply looking in the ILaunchBag utility.
        """
        return getUtility(ILaunchBag).bugtask


class BugView(LaunchpadView, BugViewMixin):
    """View class for presenting information about an `IBug`.

    Since all bug pages are registered on IBugTask, the context will be
    adapted to IBug in order to make the security declarations work
    properly. This has the effect that the context in the pagetemplate
    changes as well, so the bugtask (which is often used in the pages)
    is available as `current_bugtask`. This may not be all that pretty,
    but it was the best solution we came up with when deciding to hang
    all the pages off IBugTask instead of IBug.
    """

    @property
    def subscription(self):
        """Return whether the current user is subscribed."""
        user = self.user
        if user is None:
            return False
        return self.context.isSubscribed(user)

    def duplicates(self):
        """Return a list of dicts of duplicates.

        Each dict contains the title that should be shown and the bug
        object itself. This allows us to protect private bugs using a
        title like 'Private Bug'.
        """
        duplicate_bugs = list(self.context.duplicates)
        current_task = self.current_bugtask
        dupes_in_current_context = dict(
            (bugtask.bug, bugtask)
            for bugtask in current_task.target.searchTasks(
                BugTaskSearchParams(self.user, bug=any(*duplicate_bugs))))
        dupes = []
        for bug in duplicate_bugs:
            dupe = {}
            try:
                dupe['title'] = bug.title
            except Unauthorized:
                dupe['title'] = 'Private Bug'
            dupe['id'] = bug.id
            # If the dupe has the same context as the one we're in, link
            # to that bug task directly.
            if bug in dupes_in_current_context:
                dupe['url'] = canonical_url(dupes_in_current_context[bug])
            else:
                dupe['url'] = canonical_url(bug)
            dupes.append(dupe)

        return dupes

    def proxiedUrlForLibraryFile(self, attachment):
        """Return the proxied download URL for a Librarian file."""
        return ProxiedLibraryFileAlias(
            attachment.libraryfile, attachment).http_url


class BugSubscriptionPortletDetails:
    """A mixin used to collate bug subscription details for a view."""

    def extractBugSubscriptionDetails(self, user, bug, cache):
        # We are using "direct" to represent both direct and personal
        # (not team).
        self.direct_notifications = False
        self.direct_all_notifications = False
        self.direct_metadata_notifications = False
        self.direct_lifecycle_notifications = False
        self.other_subscription_notifications = False
        self.only_other_subscription_notifications = False
        self.any_subscription_notifications = False
        self.muted = False
        if user is not None:
            has_structural_subscriptions = not (
                get_structural_subscriptions_for_bug(bug, user).is_empty())
            self.muted = bug.isMuted(user)
            psi = PersonSubscriptions(user, bug)
            if psi.direct.personal:
                self.direct_notifications = True
                direct = psi.direct.personal[0]
                cache['subscription'] = direct.subscription
                level = direct.subscription.bug_notification_level
                if level == BugNotificationLevel.COMMENTS:
                    self.direct_all_notifications = True
                elif level == BugNotificationLevel.METADATA:
                    self.direct_metadata_notifications = True
                else:
                    assert level == BugNotificationLevel.LIFECYCLE
                    self.direct_lifecycle_notifications = True
            self.other_subscription_notifications = bool(
                has_structural_subscriptions or
                psi.from_duplicate.count or
                psi.as_owner.count or
                psi.as_assignee.count or
                psi.direct.as_team_member or
                psi.direct.as_team_admin)
            cache['other_subscription_notifications'] = bool(
                self.other_subscription_notifications)
            self.only_other_subscription_notifications = (
                self.other_subscription_notifications and
                not self.direct_notifications)
            self.any_subscription_notifications = (
                self.other_subscription_notifications or
                self.direct_notifications)
        self.user_should_see_mute_link = (
            self.any_subscription_notifications or self.muted)


class BugSubscriptionPortletView(LaunchpadView,
                                 BugSubscriptionPortletDetails, BugViewMixin):
    """View class for the subscription portlet."""

    # We want these strings to be available for the template and for the
    # JavaScript.
    notifications_text = {
        'not_only_other_subscription': _('You are'),
        'only_other_subscription': _(
            'You have subscriptions that may cause you to receive '
            'notifications, but you are'),
        'direct_all': _('subscribed to all notifications for this bug.'),
        'direct_metadata': _(
            'subscribed to all notifications except comments for this bug.'),
        'direct_lifecycle': _(
            'subscribed to notifications when this bug is closed or '
            'reopened.'),
        'not_direct': _(
            "not directly subscribed to this bug's notifications."),
        'muted': _(
            'Your personal email notifications from this bug are muted.'),
        }

    def initialize(self):
        """Initialize the view to handle the request."""
        LaunchpadView.initialize(self)
        cache = IJSONRequestCache(self.request).objects
        self.extractBugSubscriptionDetails(self.user, self.context, cache)
        if self.user:
            cache['notifications_text'] = self.notifications_text


class BugWithoutContextView:
    """View that redirects to the new bug page.

    The user is redirected, to the oldest IBugTask ('oldest' being
    defined as the IBugTask with the smallest ID.)
    """
    # XXX: BradCrittenden 2009-04-28 This class can go away since the
    # publisher now takes care of the redirection to a bug task.
    def redirectToNewBugPage(self):
        """Redirect the user to the 'first' report of this bug."""
        # An example of practicality beating purity.
        self.request.response.redirect(
            canonical_url(self.context.default_bugtask))


class BugEditViewBase(LaunchpadEditFormView):
    """Base class for all bug edit pages."""

    schema = IBug

    def setUpWidgets(self):
        """Set up the widgets using the bug as the context."""
        LaunchpadEditFormView.setUpWidgets(self, context=self.context.bug)

    def updateBugFromData(self, data):
        """Update the bug using the values in the data dictionary."""
        LaunchpadEditFormView.updateContextFromData(
            self, data, context=self.context.bug)

    @property
    def next_url(self):
        """Return the next URL to call when this call completes."""
        return canonical_url(self.context)


class BugEditView(BugEditViewBase):
    """The view for the edit bug page."""

    field_names = ['title', 'description', 'tags']
    custom_widget('title', TextWidget, displayWidth=30)
    custom_widget('tags', BugTagsWidget)
    next_url = None

    _confirm_new_tags = False

    def __init__(self, context, request):
        """context is always an IBugTask."""
        BugEditViewBase.__init__(self, context, request)
        self.notifications = []

    @property
    def label(self):
        """The form label."""
        return 'Edit details for bug #%d' % self.context.bug.id

    @property
    def page_title(self):
        """The page title."""
        return self.label

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    def validate(self, data):
        """Make sure new tags are confirmed."""
        if 'tags' not in data:
            return
        confirm_action = self.confirm_tag_action
        if confirm_action.submitted():
            # Validation is needed only for the change action.
            return
        bugtarget = self.context.target
        newly_defined_tags = set(data['tags']).difference(
            bugtarget.getUsedBugTags() + bugtarget.official_bug_tags)
        # Display the confirm button in a notification message. We want
        # it to be slightly smaller than usual, so we can't simply let
        # it render itself.
        confirm_button = (
            '<input style="font-size: smaller" type="submit"'
            ' value="%s" name="%s" />' % (
                confirm_action.label, confirm_action.__name__))
        for new_tag in newly_defined_tags:
            self.notifications.append(
                'The tag "%s" hasn\'t been used by %s before. %s' % (
                    new_tag, bugtarget.bugtargetdisplayname, confirm_button))
            self._confirm_new_tags = True

    @action('Change', name='change')
    def edit_bug_action(self, action, data):
        """Update the bug with submitted changes."""
        if not self._confirm_new_tags:
            self.updateBugFromData(data)
            self.next_url = canonical_url(self.context)

    @action('Create the new tag', name='confirm_tag')
    def confirm_tag_action(self, action, data):
        """Define a new tag."""
        self.actions['field.actions.change'].success(data)

    def render(self):
        """Render the page with only one submit button."""
        # The confirmation button shouldn't be rendered automatically.
        self.actions = [self.edit_bug_action]
        return BugEditViewBase.render(self)


class BugMarkAsDuplicateView(BugEditViewBase):
    """Page for marking a bug as a duplicate."""

    field_names = ['duplicateof']
    label = "Mark bug report as a duplicate"

    def setUpFields(self):
        """Make the readonly version of duplicateof available."""
        super(BugMarkAsDuplicateView, self).setUpFields()

        duplicateof_field = DuplicateBug(
            __name__='duplicateof', title=_('Duplicate Of'), required=False)

        self.form_fields = self.form_fields.omit('duplicateof')
        self.form_fields = formlib.form.Fields(duplicateof_field)

    @property
    def initial_values(self):
        """See `LaunchpadFormView.`"""
        return {'duplicateof': self.context.bug.duplicateof}

    @action('Change', name='change')
    def change_action(self, action, data):
        """Update the bug."""
        data = dict(data)
        # We handle duplicate changes by hand instead of leaving it to
        # the usual machinery because we must use bug.markAsDuplicate().
        bug = self.context.bug
        bug_before_modification = Snapshot(
            bug, providing=providedBy(bug))
        duplicateof = data.pop('duplicateof')
        bug.markAsDuplicate(duplicateof)
        notify(
            ObjectModifiedEvent(bug, bug_before_modification, 'duplicateof'))
        # Apply other changes.
        self.updateBugFromData(data)


class BugSecrecyEditView(LaunchpadFormView, BugSubscriptionPortletDetails):
    """Form for marking a bug as a private/public."""

    @property
    def label(self):
        return 'Bug #%i - Set visibility and security' % self.context.bug.id

    page_title = label

    class schema(Interface):
        """Schema for editing secrecy info."""
        private_field = copy_field(IBug['private'], readonly=False)
        security_related_field = copy_field(
            IBug['security_related'], readonly=False)

    @property
    def next_url(self):
        """Return the next URL to call when this call completes."""
        if not self.request.is_ajax:
            return canonical_url(self.context)
        return None

    @property
    def initial_values(self):
        """See `LaunchpadFormView.`"""
        return {'private': self.context.bug.private,
                'security_related': self.context.bug.security_related}

    @action('Change', name='change')
    def change_action(self, action, data):
        """Update the bug."""
        # We will modify data later, so take a copy now.
        data = dict(data)

        # We handle privacy changes by hand instead of leaving it to
        # the usual machinery because we must use 
        # bug.setPrivacyAndSecurityRelated() to ensure auditing information is
        # recorded.
        bug = self.context.bug
        bug_before_modification = Snapshot(
            bug, providing=providedBy(bug))
        private = data.pop('private')
        user_will_be_subscribed = (
            private and bug.getSubscribersForPerson(self.user).is_empty())
        security_related = data.pop('security_related')
        user = getUtility(ILaunchBag).user
        (private_changed, security_related_changed) = (
            bug.setPrivacyAndSecurityRelated(private, security_related, user))
        if private_changed or security_related_changed:
            changed_fields = []
            if private_changed:
                changed_fields.append('private')
                self._handlePrivacyChanged(user_will_be_subscribed)
            if security_related_changed:
                changed_fields.append('security_related')
            notify(ObjectModifiedEvent(
                    bug, bug_before_modification, changed_fields))
        if self.request.is_ajax:
            if private_changed:
                return self._getSubscriptionDetails()
            else:
                return ''

    def _getSubscriptionDetails(self):
        cache = dict()
        self.extractBugSubscriptionDetails(self.user, self.context.bug, cache)
        return dumps(
            cache, cls=ResourceJSONEncoder,
            media_type=EntryResource.JSON_TYPE)

    def _handlePrivacyChanged(self, user_will_be_subscribed):
        """Handle the case where the privacy of the bug has been changed.

        If the bug has been made private and the user is not a direct
        subscriber, they will be subscribed. If the bug is being made
        public or the user is already directly subscribed, this is a
        no-op.
        """
        if user_will_be_subscribed:
            notification_text = (
                    "Since you marked this bug as private you have "
                    "automatically been subscribed to it. "
                    "If you don't want to receive email about "
                    "this bug you can <a href=\"%s\">mute your "
                    "subscription</a> or <a href=\"%s\">"
                    "unsubscribe</a>." % (
                    canonical_url(
                        self.context, view_name='+mute'),
                    canonical_url(
                        self.context, view_name='+subscribe')))
            self.request.response.addInfoNotification(
                structured(notification_text))


class DeprecatedAssignedBugsView:
    """Deprecate the /malone/assigned namespace.

    It's important to ensure that this namespace continues to work, to
    prevent linkrot, but since FOAF seems to be a more natural place
    to put the assigned bugs report, we'll redirect to the appropriate
    FOAF URL.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def redirect_to_assignedbugs(self):
        """Redirect the user to their assigned bugs report."""
        self.request.response.redirect(
            canonical_url(getUtility(ILaunchBag).user) +
            "/+assignedbugs")


normalize_mime_type = re.compile(r'\s+')


class BugTextView(LaunchpadView):
    """View for simple text page displaying information for a bug."""

    @cachedproperty
    def bugtasks(self):
        """Cache bugtasks and avoid hitting the DB twice."""
        return list(self.context.bugtasks)

    def bug_text(self):

        """Return the bug information for text display."""
        bug = self.context

        text = []
        text.append('bug: %d' % bug.id)
        text.append('title: %s' % bug.title)
        text.append('date-reported: %s' %
            format_rfc2822_date(bug.datecreated))
        text.append('date-updated: %s' %
            format_rfc2822_date(bug.date_last_updated))
        text.append('reporter: %s' % bug.owner.unique_displayname)

        if bug.duplicateof:
            text.append('duplicate-of: %d' % bug.duplicateof.id)
        else:
            text.append('duplicate-of: ')

        if bug.duplicates:
            dupes = ' '.join(str(dupe.id) for dupe in bug.duplicates)
            text.append('duplicates: %s' % dupes)
        else:
            text.append('duplicates: ')

        if bug.private:
            # XXX kiko 2007-10-31: this could include date_made_private and
            # who_made_private but Bjorn doesn't let me.
            text.append('private: yes')

        if bug.security_related:
            text.append('security: yes')

        patches = []
        text.append('attachments: ')
        for attachment in bug.attachments_unpopulated:
            if attachment.type != BugAttachmentType.PATCH:
                text.append(' %s' % self.attachment_text(attachment))
            else:
                patches.append(attachment)

        text.append('patches: ')
        for attachment in patches:
            text.append(' %s' % self.attachment_text(attachment))

        text.append('tags: %s' % ' '.join(bug.tags))

        text.append('subscribers: ')
        for subscription in bug.subscriptions:
            text.append(' %s' % subscription.person.unique_displayname)

        return ''.join(line + '\n' for line in text)

    def bugtask_text(self, task):
        """Return a BugTask for text display."""
        text = []
        text.append('task: %s' % task.bugtargetname)
        text.append('status: %s' % task.status.title)
        text.append('date-created: %s' %
            format_rfc2822_date(task.datecreated))

        for status in ["left_new", "confirmed", "triaged", "assigned",
                       "inprogress", "closed", "incomplete",
                       "fix_committed", "fix_released", "left_closed"]:
            date = getattr(task, "date_%s" % status)
            if date:
                text.append("date-%s: %s" % (
                    status.replace('_', '-'), format_rfc2822_date(date)))

        text.append('reporter: %s' % task.owner.unique_displayname)

        if task.bugwatch:
            text.append('watch: %s' % task.bugwatch.url)

        text.append('importance: %s' % task.importance.title)

        component = task.getPackageComponent()
        if component:
            text.append('component: %s' % component.name)

        if task.assignee:
            text.append('assignee: %s' % task.assignee.unique_displayname)
        else:
            text.append('assignee: ')

        if task.milestone:
            text.append('milestone: %s' % task.milestone.name)
        else:
            text.append('milestone: ')

        return ''.join(line + '\n' for line in text)

    def attachment_text(self, attachment):
        """Return a text representation of a bug attachment."""
        mime_type = normalize_mime_type.sub(
            ' ', attachment.libraryfile.mimetype)
        download_url = ProxiedLibraryFileAlias(
            attachment.libraryfile, attachment).http_url
        return "%s %s" % (download_url, mime_type)

    def comment_text(self):
        """Return a text representation of bug comments."""

        def build_message(text):
            mailwrapper = MailWrapper(width=72)
            text = mailwrapper.format(text)
            message = MIMEText(text.encode('utf-8'),
                'plain', 'utf-8')
            # This is redundant and makes the template noisy
            del message['MIME-Version']
            return message

        from lp.bugs.browser.bugtask import (
            get_visible_comments, get_comments_for_bugtask)

        # XXX: kiko 2007-10-31: for some reason, get_comments_for_bugtask
        # takes a task, not a bug. For now live with it.
        first_task = self.bugtasks[0]
        all_comments = get_comments_for_bugtask(first_task)
        comments = get_visible_comments(all_comments[1:])

        comment_mime = MIMEMultipart()
        message = build_message(self.context.description)
        comment_mime.attach(message)

        for comment in comments:
            message = build_message(comment.text_for_display)
            message['Author'] = comment.owner.unique_displayname.encode(
                'utf-8')
            message['Date'] = format_rfc2822_date(comment.datecreated)
            message['Message-Id'] = comment.rfc822msgid
            comment_mime.attach(message)

        return comment_mime.as_string().decode('utf-8')

    def render(self):
        """Return a text representation of the bug."""
        self.request.response.setHeader('Content-type', 'text/plain')
        texts = [self.bug_text()]
        texts.extend(self.bugtask_text(task) for task in self.bugtasks)
        texts.append(self.comment_text())
        return "\n".join(texts)


class BugURL:
    """Bug URL creation rules."""
    implements(ICanonicalUrlData)

    inside = None
    rootsite = 'bugs'

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        """Return the path component of the URL."""
        return u"bugs/%d" % self.context.id


class BugAffectingUserChoice(EnumeratedType):
    """The choices for a bug affecting a user."""

    YES = Item("""
        Yes

        This bug affects me.
        """)

    NO = Item("""
        No

        This bug doesn't affect me.
        """)


class BugMarkAsAffectingUserForm(Interface):
    """Form schema for marking the bug as affecting the user."""
    affects = Choice(
        title=_('Does this bug affect you?'),
        vocabulary=BugAffectingUserChoice)


class BugMarkAsAffectingUserView(LaunchpadFormView):
    """Page for marking a bug as affecting the user."""

    schema = BugMarkAsAffectingUserForm

    field_names = ['affects']
    label = "Does this bug affect you?"

    custom_widget('affects', LaunchpadRadioWidgetWithDescription)

    @property
    def initial_values(self):
        """See `LaunchpadFormView.`"""
        affected = self.context.bug.isUserAffected(self.user)
        if affected or affected is None:
            affects = BugAffectingUserChoice.YES
        else:
            affects = BugAffectingUserChoice.NO

        return {'affects': affects}

    @action('Change', name='change')
    def change_action(self, action, data):
        """Mark the bug according to the selection."""
        self.context.bug.markUserAffected(
            self.user, data['affects'] == BugAffectingUserChoice.YES)
        self.request.response.redirect(canonical_url(self.context.bug))
