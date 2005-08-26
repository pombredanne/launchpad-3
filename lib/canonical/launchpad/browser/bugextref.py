# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""External bug reference views."""

__metaclass__ = type

__all__ = [
    'BugExternalRefsView',
    'BugExternalRefAddView']

from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.browser.addview import SQLObjectAddView

class BugExternalRefsView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'


class BugExternalRefAddView(SQLObjectAddView):

    def __init__(self, context, request):
        SQLObjectAddView.__init__(self, context, request)
        self.bug = getUtility(ILaunchBag).bug
