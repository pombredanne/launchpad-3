
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


