# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug tracker views."""

__metaclass__ = type

__all__ = [
    'BugTrackerSetNavigation',
    'BugTrackerContextMenu',
    'BugTrackerSetContextMenu',
    'BugTrackerAddView',
    'BugTrackerView',
    ]

from zope.component import getUtility

from canonical.lp.dbschema import BugTrackerType
from canonical.launchpad.interfaces import (
    IProject, IProjectBugTrackerSet, IBugTracker, IBugTrackerSet, ILaunchBag)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, Navigation)
from zope.app.form.browser.editview import EditView


class BugTrackerSetNavigation(Navigation):

    usedfor = IBugTrackerSet

    def traverse(self, name):
        return self.context[name]


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

