# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""External bug reference views."""

__metaclass__ = type

__all__ = ['BugExternalRefsView']

class BugExternalRefsView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'
