# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug tracker views."""

__metaclass__ = type

__all__ = [
    'BugTrackerSetNavigation',
    'BugTrackerContextMenu',
    'BugTrackerSetContextMenu',
    'BugTrackerAddView',
    'BugTrackerView',
    'BugTrackerNavigation',
    'IRemoteBug',
    'RemoteBug',
    ]

from zope.interface import Interface, Attribute, implements
from zope.schema import Choice, TextLine
from zope.component import getUtility

from canonical.lp.dbschema import BugTrackerType
from canonical.launchpad.interfaces import (
    IProject, IProjectBugTrackerSet, IBugTracker, IBugTrackerSet, ILaunchBag)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, Navigation, GetitemNavigation,
    redirection, LaunchpadView)
from zope.app.form.browser.editview import EditView

from canonical.launchpad import _


class BugTrackerSetNavigation(GetitemNavigation):

    usedfor = IBugTrackerSet


class BugTrackerContextMenu(ContextMenu):

    usedfor = IBugTracker

    links = ['edit']

    def edit(self):
        text = 'Edit Bug Tracker Details'
        return Link('+edit', text, icon='edit')


class BugTrackerSetContextMenu(ContextMenu):

    usedfor = IBugTrackerSet

    links = ['newbugtracker']

    def newbugtracker(self):
        text = 'Register Bug Tracker'
        return Link('+newbugtracker', text, icon='add')


class BugTrackerAddView:

    def create(self, name, bugtrackertype, title, summary, baseurl,
               contactdetails):
        """Create the IBugTracker."""
        btset = getUtility(IBugTrackerSet)
        bugtracker = btset.ensureBugTracker(
            name=name,
            bugtrackertype=bugtrackertype,
            title=title,
            summary=summary,
            baseurl=baseurl,
            contactdetails=contactdetails,
            owner=getUtility(ILaunchBag).user)
        # if we are creating this on a Project then we should link to it too
        if IProject.providedBy(self.context):
            projectbugtracker = getUtility(IProjectBugTrackerSet).new(
                project=self.context,
                bugtracker=bugtracker)
        # keep track of the new one
        self._newtracker_ = bugtracker
        return bugtracker

    def add(self, content):
        return content

    def nextURL(self):
        return canonical_url(self._newtracker_)


class BugTrackerView(EditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class BugTrackerNavigation(Navigation):

    usedfor = IBugTracker

    def breadcrumb(self):
        return self.context.name

    def traverse(self, remotebug):
        bugs = self.context.getBugsWatching(remotebug)
        if len(bugs) == 0:
            # no bugs watching => not found
            return None
        elif len(bugs) == 1:
            # one bug watching => redirect to that bug
            return redirection(canonical_url(bugs[0]))
        else:
            # else list the watching bugs
            return RemoteBug(self.context, remotebug, bugs)


class IRemoteBug(Interface):
    """A remote bug for a given bug tracker."""

    bugtracker = Choice(title=_('Bug System'), required=True,
        vocabulary='BugTracker', description=_("The bug tracker in which "
        "the remote bug is found."))

    remotebug = TextLine(title=_('Remote Bug'), required=True,
        readonly=False, description=_("The bug number of this bug in the "
        "remote bug system."))

    bugs = Attribute(_("A list of the Launchpad bugs watching the remote bug"))


class RemoteBug:

    implements(IRemoteBug)

    def __init__(self, bugtracker, remotebug, bugs):
        self.bugtracker = bugtracker
        self.remotebug = remotebug
        self.bugs = bugs
