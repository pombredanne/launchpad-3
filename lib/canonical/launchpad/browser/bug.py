# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BugSetNavigation',
    'BugView',
    'BugSetView',
    'BugEditView',
    'BugAddView',
    'BugAddingView',
    'BugLinkView',
    'BugUnlinkView',
    'BugRelatedObjectEditView',
    'BugAlsoReportInView',
    'BugContextMenu',
    'BugWithoutContextView',
    'DeprecatedAssignedBugsView']

from zope.component import getUtility

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, structured, Navigation)
from canonical.launchpad.interfaces import (
    IBug, ILaunchBag, IBugSet, IBugLinkTarget, IBugCve,
    IDistroBugTask, IDistroReleaseBugTask, NotFoundError)
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.form import FormView


class BugSetNavigation(Navigation):

    usedfor = IBugSet

    def traverse(self, name):
        # If the bug is not found, we expect a NotFoundError. If the
        # value of name is not a value that can be used to retrieve a
        # specific bug, we expect a ValueError.
        try:
            return getUtility(IBugSet).get(name)
        except (NotFoundError, ValueError):
            return None


class BugContextMenu(ContextMenu):
    usedfor = IBug
    links = ['editdescription', 'secrecy', 'markduplicate', 'subscription',
             'addsubscriber', 'addattachment', 'linktocve', 'addwatch',
             'filebug', 'activitylog', 'targetfix']

    def __init__(self, context):
        # Always force the context to be the current bugtask, so that we don't
        # have to duplicate menu code.
        ContextMenu.__init__(self, getUtility(ILaunchBag).bugtask)

    def editdescription(self):
        text = 'Edit Description'
        return Link('+edit', text, icon='edit')

    def secrecy(self):
        text = 'Bug Secrecy'
        return Link('+secrecy', text, icon='edit')

    def markduplicate(self):
        text = 'Mark as Duplicate'
        return Link('+duplicate', text, icon='edit')

    def subscription(self):
        user = getUtility(ILaunchBag).user
        
        if user is None:
            text = 'Your Subscription'
        elif user is not None and self.context.bug.isSubscribed(user):
            text = 'Unsubscribe'
        else:
            text = 'Subscribe'
        return Link('+subscribe', text, icon='add')

    def addsubscriber(self):
        text = 'Subscribe Someone Else'
        return Link('+addsubscriber', text, icon='add')

    def addattachment(self):
        text = 'Add Attachment'
        return Link('+addattachment', text, icon='add')

    def linktocve(self):
        text = structured(
            'Link to '
            '<abbr title="Common Vulnerabilities and Exposures Index">'
            'CVE'
            '</abbr>')
        return Link('+linkcve', text, icon='add')

    def unlinkcve(self):
        enabled = bool(self.context.bug.cves)
        text = 'Remove CVE link'
        return Link('+unlinkcve', text, icon='edit', enabled=enabled)

    def addwatch(self):
        text = 'Link To Other Bugtracker'
        return Link('+addwatch', text, icon='add')

    def filebug(self):
        bugtarget = self.context.target
        linktarget = '%s/%s' % (canonical_url(bugtarget), '+filebug')
        text = 'Report a Bug in %s' % bugtarget.displayname
        return Link(linktarget, text, icon='add')

    def activitylog(self):
        text = 'Activity Log'
        return Link('+activity', text, icon='list')

    def targetfix(self):
        enabled = (
            IDistroBugTask.providedBy(self.context) or
            IDistroReleaseBugTask.providedBy(self.context))
        text = 'Target Fix to Releases'
        return Link('+target', text, icon='milestone', enabled=enabled)


class BugView:
    """View class for presenting information about an IBug."""

    def __init__(self, context, request):
        self.context = IBug(context)
        self.request = request

    def currentBugTask(self):
        """Return the current IBugTask.

        'current' is determined by simply looking in the ILaunchBag utility.
        """
        return getUtility(ILaunchBag).bugtask

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

    @property
    def maintainers(self):
        """Return the set of maintainers associated with this IBug."""
        maintainers = set()
        for task in self.context.bugtasks:
            if task.maintainer:
                maintainers.add(task.maintainer)

        return maintainers


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


class BugAlsoReportInView(SQLObjectAddView):
    """View class for reporting a bug in other contexts."""

    def add(self, content):
        self.taskadded = content

    def nextURL(self):
        """Return the user to the URL of the task they just added."""
        return canonical_url(self.taskadded)


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


class BugAddView(SQLObjectAddView):
    """View for adding a bug."""

    def add(self, content):
        self.bugadded = content
        return content

    def create(self, **kw):
        """"Create a new bug."""
        return getUtility(IBugSet).createBug(**kw)

    def nextURL(self):
        bugtask = self.bugadded.bugtasks[0]
        return canonical_url(bugtask)


class BugAddingView(SQLObjectAddView):
    """A hack for browser:addform's that use IBug as their context.

    Use this class in the class="" of a browser:addform directive
    for IBug.
    """
    def add(self, content):
        return content

    def nextURL(self):
        return "."


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


class BugLinkView(FormView):
    """This view will be used for objects that support IBugLinkTarget, and
    so can be linked and unlinked from bugs.
    """

    schema = IBugCve
    fieldNames = ['bug']
    _arguments = ['bug']

    def process(self, bug):
        # we are not creating, but we need to find the bug from the bug num
        malone_bug = getUtility(IBugSet).get(bug)
        user = getUtility(ILaunchBag).user
        assert IBugLinkTarget.providedBy(self.context)
        return self.context.linkBug(malone_bug, user)

    def nextURL(self):
        return canonical_url(self.context)


class BugUnlinkView(FormView):
    """This view will be used for objects that support IBugLinkTarget, and
    thus can be unlinked from bugs.
    """

    schema = IBugCve
    fieldNames = ['bug']
    _arguments = ['bug']

    def process(self, bug):
        malone_bug = getUtility(IBugSet).get(bug)
        user = getUtility(ILaunchBag).user
        return self.context.unlinkBug(malone_bug, user)

    def nextURL(self):
        return canonical_url(self.context)


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


