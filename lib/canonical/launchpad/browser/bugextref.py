# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""External bug reference views."""

__metaclass__ = type
__all__ = [
    'BugExternalRefsView',
    'BugExtRefAddView']

from zope.app.form.utility import getWidgetsData
from zope.component import getUtility
from canonical.launchpad.interfaces import (
    IBugExternalRef, IBugExternalRefSet, ILaunchBag)
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.webapp import canonical_url

class BugExternalRefsView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'


class BugExtRefAddView(SQLObjectAddView):
    """Add view for adding a URL to a bug."""

    def create(self, url, title):
        bugtask = self.context
        user = getUtility(ILaunchBag).user

        return getUtility(IBugExternalRefSet).createBugExternalRef(
            bug=bugtask.bug, url=url, title=title, owner=user)

    def nextURL(self):
        return canonical_url(self.context)
