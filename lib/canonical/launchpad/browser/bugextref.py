# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""External bug reference views."""

__metaclass__ = type

__all__ = [
    'BugExternalRefsView',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import IBugExternalRefsView

class BugExternalRefsView(object):
    implements(IBugExternalRefsView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'


