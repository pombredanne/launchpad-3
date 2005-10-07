# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugWatch-related browser views."""

__metaclass__ = type
__all__ = ['BugWatchAddView', 'BugWatchSetNavigation']

from zope.app.form.utility import getWidgetsData
from zope.component import getUtility
from canonical.launchpad.interfaces import (
    IBugWatch, IBugWatchSet, ILaunchBag)
from canonical.launchpad.webapp import canonical_url, Navigation
from canonical.launchpad.browser.addview import SQLObjectAddView


class BugWatchAddView(SQLObjectAddView):
    """View class for adding an IBugWatch to an IBug."""

    def create(self, bugtracker, remotebug):
        bugtask = self.context
        user = getUtility(ILaunchBag).user
        return getUtility(IBugWatchSet).createBugWatch(
            bug=bugtask.bug, owner=user, bugtracker=bugtracker,
            remotebug=remotebug)

    def nextURL(self):
        return canonical_url(self.context)


class BugWatchSetNavigation(Navigation):

    usedfor = IBugWatchSet

    def traverse(self, name):
        return self.context[name]

