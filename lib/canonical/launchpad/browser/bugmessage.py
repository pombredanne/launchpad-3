
from zope.interface import implements

from canonical.launchpad.interfaces import IBugMessagesView

class BugMessagesView(object):
    implements(IBugMessagesView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    # TODO: Use IAbsoluteURL
    def nextURL(self):
        return '..'



