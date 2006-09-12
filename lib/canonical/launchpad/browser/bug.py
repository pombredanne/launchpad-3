# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BugSetNavigation',
    'BugView',
    'BugSetView',
    'BugEditView',
    'BugRelatedObjectEditView',
    'BugAlsoReportInView',
    'BugContextMenu',
    'BugWithoutContextView',
    'DeprecatedAssignedBugsView',
    'BugTextView',
    'BugURL',
    'BugMarkAsDuplicateView',
    'BugSecrecyEditView']

import cgi
import operator

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import WidgetsError
from zope.app.form.browser import TextWidget
from zope.app.form.browser.itemswidgets import SelectWidget
from zope.app.form.interfaces import WidgetsError
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.webapp import (
    action, canonical_url, ContextMenu, LaunchpadFormView, LaunchpadView,
    Link, Navigation, structured)
from canonical.launchpad.interfaces import (
    IAddBugTaskForm, IBug, ILaunchBag, IBugSet, IBugTaskSet,
    IBugWatchSet, IDistroBugTask, IDistroReleaseBugTask,
    NotFoundError, UnexpectedFormData, valid_distrotask, valid_upstreamtask,
    ICanonicalUrlData)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import (
    action, custom_widget, GeneralFormView, LaunchpadEditFormView, stepthrough)
from canonical.lp.dbschema import BugTaskImportance, BugTaskStatus
from canonical.widgets.bug import BugTagsWidget

class BugSetNavigation(Navigation):

    usedfor = IBugSet

    # XXX
    # The browser:page declaration should be sufficient, but the traversal
    # takes priority. This is a workaround.
    # https://launchpad.net/products/launchpad/+bug/30238
    # -- Daf 2006/02/01

    @stepthrough('+text')
    def text(self, name):
        try:
            return getUtility(IBugSet).getByNameOrID(name)
        except (NotFoundError, ValueError):
            return None

    def traverse(self, name):
        try:
            return getUtility(IBugSet).getByNameOrID(name)
        except (NotFoundError, ValueError):
            # If the bug is not found, we expect a NotFoundError. If the
            # value of name is not a value that can be used to retrieve
            # a specific bug, we expect a ValueError.
            return None


class BugContextMenu(ContextMenu):
    usedfor = IBug
    links = ['editdescription', 'markduplicate', 'visibility', 'addupstream',
             'adddistro', 'subscription', 'addsubscriber', 'addcomment',
             'nominate', 'addbranch', 'linktocve', 'unlinkcve', 'filebug',
             'activitylog', 'backportfix']

    def __init__(self, context):
        # Always force the context to be the current bugtask, so that we don't
        # have to duplicate menu code.
        ContextMenu.__init__(self, getUtility(ILaunchBag).bugtask)

    def editdescription(self):
        text = 'Edit Description/Tags'
        return Link('+edit', text, icon='edit')

    def visibility(self):
        text = 'Visibility/Security'
        return Link('+secrecy', text, icon='edit')

    def markduplicate(self):
        text = 'Mark as Duplicate'
        return Link('+duplicate', text, icon='edit')

    def addupstream(self):
        text = 'Also Affects Upstream'
        return Link('+upstreamtask', text, icon='add')

    def adddistro(self):
        text = 'Also Affects Distribution'
        return Link('+distrotask', text, icon='add')

    def subscription(self):
        user = getUtility(ILaunchBag).user
        if user is None:
            text = 'Subscribe/Unsubscribe'
            icon = 'edit'
        elif user is not None and self.context.bug.isSubscribed(user):
            text = 'Unsubscribe'
            icon = 'remove'
        else:
            for team in user.teams_participated_in:
                if self.context.bug.isSubscribed(team):
                    text = 'Subscribe/Unsubscribe'
                    icon = 'edit'
                    break
            else:
                text = 'Subscribe'
                icon = 'add'
        return Link('+subscribe', text, icon=icon)

    def addsubscriber(self):
        text = 'Subscribe Someone Else'
        return Link('+addsubscriber', text, icon='add')

    def nominate(self):
        text = 'Nominate for release'
        return Link('+nominate', text, icon='milestone')

    def addcomment(self):
        text = 'Comment/Attach File'
        return Link('+addcomment', text, icon='add')

    def addbranch(self):
        text = 'Add Branch'
        return Link('+addbranch', text, icon='add')

    def linktocve(self):
        text = structured(
            'Link to '
            '<abbr title="Common Vulnerabilities and Exposures Index">'
            'CVE'
            '</abbr>')
        return Link('+linkcve', text, icon='add')

    def unlinkcve(self):
        enabled = bool(self.context.bug.cves)
        text = 'Remove CVE Link'
        return Link('+unlinkcve', text, icon='remove', enabled=enabled)

    def filebug(self):
        bugtarget = self.context.target
        linktarget = '%s/%s' % (canonical_url(bugtarget), '+filebug')
        text = 'Report a Bug in %s' % bugtarget.displayname
        return Link(linktarget, text, icon='add')

    def activitylog(self):
        text = 'Activity Log'
        return Link('+activity', text, icon='list')

    def backportfix(self):
        enabled = (
            IDistroBugTask.providedBy(self.context) or
            IDistroReleaseBugTask.providedBy(self.context))
        text = 'Backport Fix to Releases'
        return Link('+backport', text, icon='bug', enabled=enabled)


class BugView:
    """View class for presenting information about an IBug."""

    def __init__(self, context, request):
        self.context = IBug(context)
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def currentBugTask(self):
        """Return the current IBugTask.

        'current' is determined by simply looking in the ILaunchBag utility.
        """
        return getUtility(ILaunchBag).bugtask

    @property
    def subscription(self):
        """Return whether the current user is subscribed."""
        user = getUtility(ILaunchBag).user
        if user is None:
            return False
        return self.context.isSubscribed(user)

    def duplicates(self):
        """Return a list of dicts of duplicates.

        Each dict contains the title that should be shown and the bug
        object itself. This allows us to protect private bugs using a
        title like 'Private Bug'.
        """
        dupes = []
        for bug in self.context.duplicates:
            dupe = {}
            try:
                dupe['title'] = bug.title
            except Unauthorized:
                dupe['title'] = 'Private Bug'
            dupe['id'] = bug.id
            dupe['url'] = self.getDupeBugLink(bug)
            dupes.append(dupe)

        return dupes

    def getDupeBugLink(self, dupe):
        """Return a URL for a duplicate of this bug.

        The link will be in the current context if the dupe is also
        reported in this context, otherwise a default /bugs/$bug.id
        style URL will be returned.
        """
        current_task = self.currentBugTask()

        for task in dupe.bugtasks:
            if task.target == current_task.target:
                return canonical_url(task)

        return canonical_url(dupe)


class BugWithoutContextView:
    """View that redirects to the new bug page.

    The user is redirected, to the oldest IBugTask ('oldest' being
    defined as the IBugTask with the smallest ID.)
    """
    def redirectToNewBugPage(self):
        """Redirect the user to the 'first' report of this bug."""
        # An example of practicality beating purity.
        bugtasks = sorted(self.context.bugtasks, key=operator.attrgetter('id'))
        self.request.response.redirect(canonical_url(bugtasks[0]))


class BugTrackerWidget(SelectWidget):
    """Custom widget for selecting a bug tracker.

    This is needed since we don't want the bug tracker to be required,
    but you still shouldn't be abled to select "(no option)".
    """

    firstItem = True

    def renderItems(self, value):
        """We don't want the (no option) value to be rendered."""
        items = SelectWidget.renderItems(self, value)
        if not self.context.required:
            items = items[1:]
        return items


class BugAlsoReportInView(LaunchpadFormView):
    """View class for reporting a bug in other contexts."""

    schema = IAddBugTaskForm
    custom_widget('bugtracker', BugTrackerWidget)

    index = ViewPageTemplateFile('../templates/bugtask-requestfix.pt')
    _confirm_new_task = False

    def __init__(self, context, request):
        LaunchpadFormView.__init__(self, context, request)
        self.notifications = []
        self.field_names = ['link_to_bugwatch', 'bugtracker', 'remotebug']

    def initializeAndRender(self, label, target_field_names):
        """Initialize the form and render it."""
        self.label = label
        self.field_names.extend(target_field_names)
        LaunchpadFormView.initialize(self)
        self.target_widgets = [
            self.widgets[field_name]
            for field_name in self.field_names
            if field_name in target_field_names]
        link_bug_widget = self.widgets['link_to_bugwatch']
        onkeypress_js = "selectWidget('%s', event);" % link_bug_widget.name
        self.widgets['remotebug'].extra = 'onkeypress="%s"' % onkeypress_js
        self.widgets['bugtracker'].extra = 'onchange="%s"' % onkeypress_js
        return self.render()

    def render_upstreamtask(self):
        return self.initializeAndRender(
            "Request fix in a product", ['product'])

    def render_distrotask(self):
        return self.initializeAndRender(
            "Request fix in a distribution",
            ['distribution', 'sourcepackagename'])

    def getBugTargetName(self):
        """Return the name of the fix target.

        This is either the chosen product or distribution.
        """
        if 'distribution' in self.field_names:
            target = self.widgets['distribution'].getInputValue()
        elif 'product' in self.field_names:
            target = self.widgets['product'].getInputValue()
        else:
            raise AssertionError(
                'Either a product or distribution widget should be present'
                ' in the form.')
        return target.displayname

    def validate(self, data):
        """Validate the form.

        Check that:
            * We have a unique upstream task
            * We have a unique distribution task
            * If bugtracker is not None, remotebug has to be not None
            * If the target uses Malone, a bug watch can't be added.
        """
        link_to_bugwatch = data.get('link_to_bugwatch')
        remotebug = data.get('remotebug')
        product = data.get('product')
        distribution = data.get('distribution')
        sourcepackagename = data.get('sourcepackagename')
        if product:
            target = product
            try:
                valid_upstreamtask(self.context.bug, product)
            except WidgetsError, errors:
                for error in errors:
                    self.setFieldError('product', error.snippet())
        elif distribution:
            target = distribution
            try:
                valid_distrotask(
                    self.context.bug, distribution, sourcepackagename,
                    on_create=True)
            except WidgetsError, errors:
                for error in errors:
                    self.setFieldError('sourcepackagename', error.snippet())
        else:
            # Validation failed for either the product or distribution,
            # no point in trying to validate further.
            return

        if link_to_bugwatch and target.official_malone:
            self.addError(
                "%s uses Malone as its bug tracker, and it can't at the"
                " same time be linked to a remote bug." % cgi.escape(
                    target.displayname))
        elif link_to_bugwatch and remotebug is None:
            #XXX: This should use setFieldError, but the widget isn't
            #     rendered in a way that allows the error to be
            #     displayed next to the widget.
            #     -- Bjorn Tillenius, 2006-09-12
            self.addError(
                "Please specify the remote bug number in the remote "
                "bug tracker.")
        if len(self.errors) > 0:
            # The checks below should be made only if the form doesn't
            # contain any errors.
            return

        confirm_action = self.confirm_action
        if confirm_action.submitted():
            # The user confirmed that he does want to add the task.
            return
        if not target.official_malone and not link_to_bugwatch:
            confirm_button = (
                '<input style="font-size: smaller" type="submit"'
                ' value="%s" name="%s" />' % (
                    confirm_action.label, confirm_action.__name__))
            #XXX: Rewrite this text to make it more compact.
            self.notifications.append(
                "%s doesn't use Malone as its bug tracker. If possible,"
                " you should link to a remote bug in order to keep track"
                " of the status of the fix. If you don't add a bug watch"
                " now you have to keep track of the status manually.  You"
                " can however link to an external bug tracker at a later"
                " stage in order to get automatic status updates. Are"
                " you sure you want to request a fix anyway?"
                " %s" % (cgi.escape(self.getBugTargetName()), confirm_button))
            self._confirm_new_task = True

    @action('Continue', name='request_fix')
    def continue_action(self, action, data):
        """Create new bug task.

        Only one of product and distribution may be not None, and
        if distribution is None, sourcepackagename has to be None.
        """
        if self._confirm_new_task:
            return
        product = data.get('product')
        distribution = data.get('distribution')
        sourcepackagename = data.get('sourcepackagename')
        bugtracker = data.get('bugtracker')
        remotebug = data.get('remotebug')
        link_to_bugwatch = data.get('link_to_bugwatch')

        if product is not None:
            target = product
        elif distribution is not None:
            target = distribution
        else:
            raise AssertionError(
                'validate() should ensure that a product or distribution'
                ' is present')

        taskadded = getUtility(IBugTaskSet).createTask(
            self.context.bug,
            getUtility(ILaunchBag).user,
            product=product,
            distribution=distribution, sourcepackagename=sourcepackagename)

        if link_to_bugwatch:
            user = getUtility(ILaunchBag).user
            bug_watch = getUtility(IBugWatchSet).createBugWatch(
                bug=taskadded.bug, owner=user, bugtracker=bugtracker,
                remotebug=remotebug)
            notify(SQLObjectCreatedEvent(bug_watch))
            if not target.official_malone:
                taskadded.bugwatch = bug_watch

        if not target.official_malone and taskadded.bugwatch is not None:
            # A remote bug task gets its from a bug watch, so we want
            # its status to be None when created.
            taskadded.transitionToStatus(BugTaskStatus.UNKNOWN)
            taskadded.importance = BugTaskImportance.UNKNOWN

        notify(SQLObjectCreatedEvent(taskadded))
        self.next_url = canonical_url(taskadded)

    @action('Yes, request fix anyway', name='confirm')
    def confirm_action(self, action, data):
        self.continue_action.success(data)

    def render(self):
        """Render the page with only one submit button."""
        # The confirmation button shouldn't be rendered automatically.
        self.actions = [self.continue_action]
        return LaunchpadFormView.render(self)

class BugSetView:
    """The default view for /malone/bugs.

    Essentially, this exists only to allow forms to post IDs here and be
    redirected to the right place.
    """

    def redirectToBug(self):
        bug_id = self.request.form.get("id")
        if bug_id:
            return self.request.response.redirect(bug_id)
        return self.request.response.redirect("/malone")


class BugEditViewBase(LaunchpadEditFormView):
    """Base class for all bug edit pages."""

    schema = IBug

    def __init__(self, context, request):
        self.current_bugtask = context
        context = IBug(context)
        LaunchpadEditFormView.__init__(self, context, request)

    @property
    def next_url(self):
        return canonical_url(self.current_bugtask)


class BugEditView(BugEditViewBase):
    """The view for the edit bug page."""

    field_names = ['title', 'description', 'tags', 'name']
    custom_widget('title', TextWidget, displayWidth=30)
    custom_widget('tags', BugTagsWidget)
    next_url = None

    _confirm_new_tags = False

    def __init__(self, context, request):
        BugEditViewBase.__init__(self, context, request)
        self.notifications = []

    def validate(self, data):
        """Make sure new tags are confirmed."""
        confirm_action = self.confirm_tag_action
        if confirm_action.submitted():
            # Validation is needed only for the change action.
            return
        bugtarget = self.current_bugtask.target
        newly_defined_tags = set(data['tags']).difference(
            bugtarget.getUsedBugTags())
        # Display the confirm button in a notification message. We want
        # it to be slightly smaller than usual, so we can't simply let
        # it render itself.
        confirm_button = (
            '<input style="font-size: smaller" type="submit"'
            ' value="%s" name="%s" />' % (
                confirm_action.label, confirm_action.__name__))
        for new_tag in newly_defined_tags:
            self.notifications.append(
                'The tag "%s" hasn\'t yet been used by %s before.'
                ' Is this a new tag? %s' % (
                    new_tag, bugtarget.bugtargetname, confirm_button))
            self._confirm_new_tags = True

    @action('Change', name='change')
    def edit_bug_action(self, action, data):
        if not self._confirm_new_tags:
            self.updateContextFromData(data)
            self.next_url = canonical_url(self.current_bugtask)

    @action('Yes, define new tag', name='confirm_tag')
    def confirm_tag_action(self, action, data):
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

    @action('Change', name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class BugSecrecyEditView(BugEditViewBase):
    """Page for marking a bug as a private/public."""

    field_names = ['private', 'security_related']
    label = "Bug visibility and security"

    @action('Change', name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class BugRelatedObjectEditView(SQLObjectEditView):
    """View class for edit views of bug-related object.

    Examples would include the edit cve page, edit subscription page,
    etc.
    """
    def __init__(self, context, request):
        SQLObjectEditView.__init__(self, context, request)
        # Store the current bug in an attribute of the view, so that
        # ZPT rendering code can access it.
        self.bug = getUtility(ILaunchBag).bug

    def changed(self):
        """Redirect to the bug page."""
        bugtask = getUtility(ILaunchBag).bugtask
        self.request.response.redirect(canonical_url(bugtask))


class DeprecatedAssignedBugsView:
    """Deprecate the /malone/assigned namespace.

    It's important to ensure that this namespace continues to work, to
    prevent linkrot, but since FOAF seems to be a more natural place
    to put the assigned bugs report, we'll redirect to the appropriate
    FOAF URL.
    """
    def __init__(self, context, request):
        """Redirect the user to their assigned bugs report."""
        self.context = context
        self.request = request

    def redirect_to_assignedbugs(self):
        self.request.response.redirect(
            canonical_url(getUtility(ILaunchBag).user) +
            "/+assignedbugs")


class BugTextView(LaunchpadView):
    """View for simple text page displaying information for a bug."""

    def person_text(self, person):
        return '%s (%s)' % (person.displayname, person.name)

    def bug_text(self, bug):
        text = []
        text.append('bug: %d' % bug.id)
        text.append('title: %s' % bug.title)
        text.append('reporter: %s' % self.person_text(bug.owner))

        if bug.duplicateof:
            text.append('duplicate-of: %d' % bug.duplicateof.id)
        else:
            text.append('duplicate-of: ')

        text.append('subscribers: ')

        for subscription in bug.subscriptions:
            text.append(' %s' % self.person_text(subscription.person))

        return ''.join(line + '\n' for line in text)

    def bugtask_text(self, task):
        text = []
        text.append('task: %s' % task.targetname)
        text.append('status: %s' % task.status.title)
        text.append('reporter: %s' % self.person_text(task.owner))

        text.append('importance: %s' % task.importance.title)

        if task.assignee:
            text.append('assignee: %s' % self.person_text(task.assignee))
        else:
            text.append('assignee: ')

        if task.milestone:
            text.append('milestone: %s' % task.milestone.name)
        else:
            text.append('milestone: ')

        return ''.join(line + '\n' for line in text)

    def render(self):
        self.request.response.setHeader('Content-type', 'text/plain')
        texts = (
            [self.bug_text(self.context)] +
            [self.bugtask_text(task) for task in self.context.bugtasks])
        return u'\n'.join(texts)


class BugURL:
    implements(ICanonicalUrlData)

    inside = None
    rootsite = 'launchpad'

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        return u"bugs/%d" % self.context.id
