# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""IBug related view classes."""

__metaclass__ = type

__all__ = [
    'BugContextMenu',
    'BugEditView',
    'BugFacets',
    'BugMarkAsDuplicateView',
    'BugNavigation',
    'BugRelatedObjectEditView',
    'BugSecrecyEditView',
    'BugSetNavigation',
    'BugTextView',
    'BugURL',
    'BugView',
    'BugWithoutContextView',
    'DeprecatedAssignedBugsView',
    'MaloneView',
    ]

import operator

from zope.app.form.browser import TextWidget
from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    BugTaskStatus,
    BugTaskSearchParams,
    IBug,
    IBugSet,
    IBugTaskSet,
    IBugWatchSet,
    ICveSet,
    IFrontPageBugTaskSearch,
    ILaunchBag,
    NotFoundError,
    )
from canonical.launchpad.browser.editview import SQLObjectEditView

from canonical.launchpad.webapp import (
    custom_widget, action, canonical_url, ContextMenu,
    LaunchpadFormView, LaunchpadView,LaunchpadEditFormView, stepthrough,
    Link, Navigation, structured, StandardLaunchpadFacets)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

from canonical.widgets.bug import BugTagsWidget
from canonical.widgets.project import ProjectScopeWidget


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
    links = ['editdescription', 'markduplicate', 'visibility', 'addupstream',
             'adddistro', 'subscription', 'addsubscriber', 'addcomment',
             'nominate', 'addbranch', 'linktocve', 'unlinkcve',
             'offermentoring', 'retractmentoring', 'createquestion',
             'activitylog']

    def __init__(self, context):
        # Always force the context to be the current bugtask, so that we don't
        # have to duplicate menu code.
        ContextMenu.__init__(self, getUtility(ILaunchBag).bugtask)

    def editdescription(self):
        """Return the 'Edit description/tags' Link."""
        text = 'Edit description/tags'
        return Link('+edit', text, icon='edit')

    def visibility(self):
        """Return the 'Set privacy/security' Link."""
        text = 'Set privacy/security'
        return Link('+secrecy', text, icon='edit')

    def markduplicate(self):
        """Return the 'Mark as duplicate' Link."""
        text = 'Mark as duplicate'
        return Link('+duplicate', text, icon='edit')

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
            text = 'Unsubscribe'
            icon = 'remove'
        else:
            for team in user.teams_participated_in:
                if (self.context.bug.isSubscribed(team) or
                    self.context.bug.isSubscribedToDupes(team)):
                    text = 'Subscribe/Unsubscribe'
                    icon = 'edit'
                    break
            else:
                text = 'Subscribe'
                icon = 'add'
        return Link('+subscribe', text, icon=icon)

    def addsubscriber(self):
        """Return the 'Subscribe someone else' Link."""
        text = 'Subscribe someone else'
        return Link('+addsubscriber', text, icon='add')

    def nominate(self):
        """Return the 'Target/Nominate for release' Link."""
        launchbag = getUtility(ILaunchBag)
        target = launchbag.product or launchbag.distribution
        if check_permission("launchpad.Driver", target):
            text = "Target to release"
        else:
            text = 'Nominate for release'

        return Link('+nominate', text, icon='milestone')

    def addcomment(self):
        """Return the 'Comment or attach file' Link."""
        text = 'Comment or attach file'
        return Link('+addcomment', text, icon='add')

    def addbranch(self):
        """Return the 'Add branch' Link."""
        text = 'Add branch'
        return Link('+addbranch', text, icon='add')

    def linktocve(self):
        """Return the 'Link tp CVE' Link."""
        text = structured(
            'Link to '
            '<abbr title="Common Vulnerabilities and Exposures Index">'
            'CVE'
            '</abbr>')
        return Link('+linkcve', text, icon='add')

    def unlinkcve(self):
        """Return 'Remove CVE link' Link."""
        enabled = bool(self.context.bug.cves)
        text = 'Remove CVE link'
        return Link('+unlinkcve', text, icon='remove', enabled=enabled)

    def offermentoring(self):
        """Return the 'Offer mentorship' Link."""
        text = 'Offer mentorship'
        user = getUtility(ILaunchBag).user
        enabled = self.context.bug.canMentor(user)
        return Link('+mentor', text, icon='add', enabled=enabled)

    def retractmentoring(self):
        """Return the 'Retract mentorship' Link."""
        text = 'Retract mentorship'
        user = getUtility(ILaunchBag).user
        enabled = (self.context.bug.isMentor(user) and
                   not self.context.bug.is_complete and
                   user)
        return Link('+retractmentoring', text, icon='remove', enabled=enabled)

    def createquestion(self):
        """Create a question from this bug."""
        text = 'Is a question'
        enabled = self.context.bug.canBeAQuestion()
        return Link('+create-question', text, icon='edit', enabled=enabled)

    def activitylog(self):
        """Return the 'Activity log' Link."""
        text = 'View activity log'
        return Link('+activity', text, icon='list')


class MaloneView(LaunchpadFormView):
    """The Bugs front page."""

    custom_widget('searchtext', TextWidget, displayWidth=50)
    custom_widget('scope', ProjectScopeWidget)
    schema = IFrontPageBugTaskSearch
    field_names = ['searchtext', 'scope']

    # Test: standalone/xx-slash-malone-slash-bugs.txt
    error_message = None

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
        return self.getWidgetError('scope')

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
        if bug_id.startswith("#"):
            # Be nice to users and chop off leading hashes
            bug_id = bug_id[1:]
        try:
            bug = getUtility(IBugSet).getByNameOrID(bug_id)
        except NotFoundError:
            self.error_message = "Bug %r is not registered." % bug_id
        else:
            return self.request.response.redirect(canonical_url(bug))

    def getMostRecentlyFixedBugs(self, limit=5):
        """Return the ten most recently fixed bugs."""
        fixed_bugs = []
        search_params = BugTaskSearchParams(
            self.user, status=BugTaskStatus.FIXRELEASED,
            orderby='-date_closed')
        fixed_bugtasks = getUtility(IBugTaskSet).search(search_params)
        # XXX: Bjorn Tillenius 2006-12-13:
        #      We might end up returning less than :limit: bugs, but in
        #      most cases we won't, and '4*limit' is here to prevent
        #      this page from timing out in production. Later I'll fix
        #      this properly by selecting bugs instead of bugtasks.
        #      If fixed_bugtasks isn't sliced, it will take a long time
        #      to iterate over it, even over just 10, because
        #      Transaction.iterSelect() listifies the result.
        for bugtask in fixed_bugtasks[:4*limit]:
            if bugtask.bug not in fixed_bugs:
                fixed_bugs.append(bugtask.bug)
                if len(fixed_bugs) >= limit:
                    break
        return fixed_bugs

    def getCveBugLinkCount(self):
        """Return the number of links between bugs and CVEs there are."""
        return getUtility(ICveSet).getBugCveCount()


class BugView(LaunchpadView):
    """View class for presenting information about an `IBug`.

    Since all bug pages are registered on IBugTask, the context will be
    adapted to IBug in order to make the security declarations work
    properly. This has the effect that the context in the pagetemplate
    changes as well, so the bugtask (which is often used in the pages)
    is available as currentBugTask(). This may not be all that pretty,
    but it was the best solution we came up with when deciding to hang
    all the pages off IBugTask instead of IBug.
    """

    def currentBugTask(self):
        """Return the current `IBugTask`.

        'current' is determined by simply looking in the ILaunchBag utility.
        """
        return getUtility(ILaunchBag).bugtask

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
        bugtasks = sorted(
            self.context.bugtasks, key=operator.attrgetter('id'))
        self.request.response.redirect(canonical_url(bugtasks[0]))


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
        if 'tags' not in data:
            return
        confirm_action = self.confirm_tag_action
        if confirm_action.submitted():
            # Validation is needed only for the change action.
            return
        bugtarget = self.context.target
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
                    new_tag, bugtarget.bugtargetdisplayname, confirm_button))
            self._confirm_new_tags = True

    @action('Change', name='change')
    def edit_bug_action(self, action, data):
        """Update the bug with submitted changes."""
        if not self._confirm_new_tags:
            self.updateBugFromData(data)
            self.next_url = canonical_url(self.context)

    @action('Yes, define new tag', name='confirm_tag')
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

    @action('Change', name='change')
    def change_action(self, action, data):
        """Update the bug."""
        self.updateBugFromData(data)


class BugSecrecyEditView(BugEditViewBase):
    """Page for marking a bug as a private/public."""

    field_names = ['private', 'security_related']
    label = "Bug visibility and security"

    @action('Change', name='change')
    def change_action(self, action, data):
        """Update the bug."""
        self.updateBugFromData(data)


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
        self.current_bugtask = getUtility(ILaunchBag).bugtask

    def changed(self):
        """Redirect to the bug page."""
        self.request.response.redirect(canonical_url(self.current_bugtask))


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


class BugTextView(LaunchpadView):
    """View for simple text page displaying information for a bug."""

    def person_text(self, person):
        """Return a Person for text display."""
        return '%s (%s)' % (person.displayname, person.name)

    def bug_text(self, bug):
        """Return the bug information for text display."""
        text = []
        text.append('bug: %d' % bug.id)
        text.append('title: %s' % bug.title)
        text.append('reporter: %s' % self.person_text(bug.owner))

        if bug.duplicateof:
            text.append('duplicate-of: %d' % bug.duplicateof.id)
        else:
            text.append('duplicate-of: ')

        if bug.duplicates:
            dupes = ' '.join(str(dupe.id) for dupe in bug.duplicates)
            text.append('duplicates: %s' % dupes)
        else:
            text.append('duplicates: ')

        text.append('subscribers: ')

        for subscription in bug.subscriptions:
            text.append(' %s' % self.person_text(subscription.person))

        return ''.join(line + '\n' for line in text)

    def bugtask_text(self, task):
        """Return a BugTask for text display."""
        text = []
        text.append('task: %s' % task.bugtargetname)
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
        """Return a text representation of the Bug."""
        self.request.response.setHeader('Content-type', 'text/plain')
        texts = (
            [self.bug_text(self.context)] +
            [self.bugtask_text(task) for task in self.context.bugtasks])
        return u'\n'.join(texts)


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

