
from zope.interface import implements

from canonical.launchpad.interfaces import IMessagesView

class MessagesView(object):
    implements(IMessagesView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    # TODO: Use IAbsoluteURL
    def nextURL(self):
        return '..'



