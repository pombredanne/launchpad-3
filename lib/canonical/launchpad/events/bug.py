from zope.interface import implements
from canonical.launchpad.interfaces import IBugEvent, IBugCommentAddedEvent

class BugEvent(object):
    implements(IBugEvent)
    def __init__(self, object, cause):
        self.object = object
        self.cause = cause

class BugCommentAddedEvent(BugEvent):
    implements(IBugCommentAddedEvent)
