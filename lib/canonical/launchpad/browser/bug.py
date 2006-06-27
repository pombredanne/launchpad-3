# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BugSetNavigation',
    'BugView',
    'BugSetView',
    'BugEditView',
    'BugLinkView',
    'BugUnlinkView',
    'BugRelatedObjectEditView',
    'BugAlsoReportInView',
    'BugContextMenu',
    'BugWithoutContextView',
    'DeprecatedAssignedBugsView',
    'BugTextView',
    'BugURL']

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import WidgetsError
from zope.app.form.browser.itemswidgets import SelectWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, structured, Navigation, LaunchpadView)
from canonical.launchpad.interfaces import (
    IAddBugTaskForm, IBug, ILaunchBag, IBugSet, IBugTaskSet,
    IBugLinkTarget, IBugWatchSet, IDistroBugTask, IDistroReleaseBugTask,
    NotFoundError, UnexpectedFormData, valid_distrotask, valid_upstreamtask,
    ICanonicalUrlData)
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.helpers import check_permission
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import GeneralFormView, stepthrough
from canonical.lp.dbschema import BugTaskImportance, BugTaskStatus

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
    links = ['editdescription', 'visibility', 'markduplicate', 'subscription',
             'addsubscriber', 'addattachment', 'addbranch', 'linktocve',
             'unlinkcve', 'filebug', 'activitylog', 'backportfix']

    def __init__(self, context):
        # Always force the context to be the current bugtask, so that we don't
        # have to duplicate menu code.
        ContextMenu.__init__(self, getUtility(ILaunchBag).bugtask)

    def editdescription(self):
        text = 'Edit Description'
        return Link('+edit', text, icon='edit')

    def visibility(self):
        text = 'Visibility/Security'
        return Link('+secrecy', text, icon='edit')

    def markduplicate(self):
        text = 'Mark as Duplicate'
        return Link('+duplicate', text, icon='edit')

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

    def addattachment(self):
        text = 'Add Attachment'
        return Link('+addattachment', text, icon='add')

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
        return Link('+unlinkcve', text, icon='edit', enabled=enabled)

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

    def taskLink(self, bugtask):
        """Return the proper link to the bugtask whether it's editable"""
        user = getUtility(ILaunchBag).user
        if check_permission('launchpad.Edit', user):
            return canonical_url(bugtask) + "/+editstatus"
        else:
            return canonical_url(bugtask) + "/+viewstatus"

    def getFixRequestRowCSSClassForBugTask(self, bugtask):
        """Return the fix request row CSS class for the bugtask.

        The class is used to style the bugtask's row in the "fix requested for"
        table on the bug page.
        """
        if bugtask == self.currentBugTask():
            # The "current" bugtask is highlighted.
            return 'highlight'
        else:
            # Anything other than the "current" bugtask gets no
            # special row styling.
            return ''

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
        bugtasks = sorted(self.context.bugtasks, key=lambda task: task.id)

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


class BugAlsoReportInView(GeneralFormView):
    """View class for reporting a bug in other contexts."""

    schema = IAddBugTaskForm
    fieldNames = None
    index = ViewPageTemplateFile('../templates/bugtask-requestfix.pt')
    confirmation_page = ViewPageTemplateFile(
        '../templates/bugtask-confirm-unlinked.pt')
    process_status = None
    saved_process_form = GeneralFormView.process_form
    show_confirmation = False
    _nextURL = None

    def __init__(self, context, request):
        """Override GeneralFormView.__init__() not to set up widgets."""
        self.context = context
        self.request = request
        self.fieldNames = ['link_to_bugwatch', 'bugtracker', 'remotebug']
        self.errors = {}

    def process_form(self):
        """Simply return the current status.

        We override it, since we need to do some setup before processing
        the form.
        """
        return self.process_status

    @property
    def _keyword_arguments(self):
        """All the fields should be given as keyword arguments."""
        return self.fieldNames

    def initializeAndRender(self):
        """Process the widgets and render the page."""
        self.bugtracker_widget = CustomWidgetFactory(BugTrackerWidget)
        self._setUpWidgets()
        # Add some javascript to make the bug watch widgets enabled only
        # when the checkbox is checked.
        self.disable_bugwatch_widgets_js = (
            "<!--\n"
            "setDisabled(!document.getElementById('%s').checked, '%s', '%s');"
            "\n-->" % (
                self.link_to_bugwatch_widget.name,
                self.bugtracker_widget.name,
                self.remotebug_widget.name))
        checkbox_onclick = (
            "onClick=\"setDisabled(!this.checked, '%s', '%s')\"" % (
                self.bugtracker_widget.name, self.remotebug_widget.name))
        self.link_to_bugwatch_widget.extra = checkbox_onclick

        self.saved_process_form()
        return self.index()

    def render_upstreamtask(self):
        self.label = "Request fix in a product"
        self.fieldNames.append('product')
        return self.initializeAndRender()

    def render_distrotask(self):
        self.label = "Request fix in a distribution"
        self.fieldNames.extend(['distribution', 'sourcepackagename'])
        return self.initializeAndRender()

    def getAllWidgets(self):
        """Return all the widgets used by this view."""
        return GeneralFormView.widgets(self)

    def widgets(self):
        """Return the widgets that should be rendered by the main macro.

        We will place the bug watch widgets ourself, so we don't want
        them rendered automatically.
        """
        bug_watch_widgets = [
            self.schema['bugtracker'],
            self.schema['remotebug'],
            self.schema['link_to_bugwatch'],
            ]
        return [
            widget for widget in GeneralFormView.widgets(self)
            if widget.context not in bug_watch_widgets
            ]

    def getBugTargetName(self):
        """Return the name of the fix target.

        This is either the chosen product or distribution.
        """
        if 'distribution' in self.fieldNames:
            target = self.distribution_widget.getInputValue()
        elif 'product' in self.fieldNames:
            target = self.product_widget.getInputValue()
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
        errors = []
        widgets_data = {}
        link_to_bugwatch = data.get('link_to_bugwatch')
        bugtracker = data.get('bugtracker')
        remotebug = data.get('remotebug')
        product = data.get('product')
        distribution = data.get('distribution')
        sourcepackagename = data.get('sourcepackagename')
        if product:
            target = product
            valid_upstreamtask(self.context.bug, product)
        elif distribution:
            target = distribution
            valid_distrotask(
                self.context.bug, distribution, sourcepackagename,
                on_create=True)
        else:
            raise UnexpectedFormData(
                'Neither product nor distribution was provided')
        if link_to_bugwatch and target.official_malone:
            errors.append(LaunchpadValidationError(
                "%s uses Malone as its bug tracker, and it can't at the"
                " same time be linked to a remote bug.",
                target.displayname))
        elif link_to_bugwatch and remotebug is None:
            errors.append(LaunchpadValidationError(
                "Please specify the remote bug number in the remote "
                "bug tracker."))
            widgets_data['bugtracker'] = bugtracker
            widgets_data['remotebug'] = remotebug

        if errors:
            raise WidgetsError(errors, widgetsData=widgets_data)

    def submitted(self):
        for submit_button in ['FORM_SUBMIT', 'CONFIRM', 'CANCEL']:
            if submit_button in self.request.form:
                return True
        else:
            return False

    def process(self, product=None, distribution=None, sourcepackagename=None,
                bugtracker=None, remotebug=None, link_to_bugwatch=False):
        """Create new bug task.

        Only one of product and distribution may be not None, and
        if distribution is None, sourcepackagename has to be None.
        """
        if product is not None:
            target = product
        elif distribution is not None:
            target = distribution
        else:
            raise AssertionError(
                'validate() should ensure that a product or distribution'
                ' is present')

        if not target.official_malone and not link_to_bugwatch:
            if 'CANCEL' in self.request.form:
                # The user chose not to add an unlinked bugtask, let
                # him edit the information before processing it.
                return
            elif 'FORM_SUBMIT' in self.request.form:
                # The user hasn't confirmed that he really wants to add an
                # unlinked task.
                self.show_confirmation = True
                self.index = self.confirmation_page
                return
            else:
                # The user confirmed adding the unlinked bugtask.
                assert 'CONFIRM' in self.request.form, (
                    'process() should be called only if CANCEL, CONFIRM,'
                    ' or FORM_SUBMIT is submitted.')

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
        self._nextURL = canonical_url(taskadded)
        return ''


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


class BugEditView(BugView, SQLObjectEditView):
    """The view for the edit bug page."""
    def __init__(self, context, request):
        self.current_bugtask = context
        context = IBug(context)
        BugView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)

    def changed(self):
        self.request.response.redirect(canonical_url(self.current_bugtask))


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


class BugLinkView(GeneralFormView):
    """This view will be used for objects that support IBugLinkTarget, and
    so can be linked and unlinked from bugs.
    """

    def process(self, bug):
        # we are not creating, but we need to find the bug from the bug num
        try:
            malone_bug = getUtility(IBugSet).get(bug)
        except NotFoundError:
            return 'No malone bug #%s' % str(bug)
        user = getUtility(ILaunchBag).user
        assert IBugLinkTarget.providedBy(self.context)
        self._nextURL = canonical_url(self.context)
        return self.context.linkBug(malone_bug, user)


class BugUnlinkView(GeneralFormView):
    """This view will be used for objects that support IBugLinkTarget, and
    thus can be unlinked from bugs.
    """

    def process(self, bug):
        try:
            malone_bug = getUtility(IBugSet).get(bug)
        except NotFoundError:
            return 'No malone bug #%s' % str(bug)
        user = getUtility(ILaunchBag).user
        self._nextURL = canonical_url(self.context)
        return self.context.unlinkBug(malone_bug, user)


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
