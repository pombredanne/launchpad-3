from zope.interface import implements
from canonical.launchpad.interfaces import IBugEvent, IBugAddedEvent, \
     IBugCommentAddedEvent, IBugAssignedProductAddedEvent

class BugEvent(object):
    implements(IBugEvent)
    def __init__(self, object, cause):
        self.object = object
        self.cause = cause

class BugAssignedProductAddedEvent(BugEvent):
    implements(IBugAssignedProductAddedEvent)

class BugCommentAddedEvent(BugEvent):
    implements(IBugCommentAddedEvent)

class BugAddedEvent(BugEvent):
    implements(IBugAddedEvent)
