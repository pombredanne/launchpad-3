from zope.interface import implements
from canonical.launchpad.interfaces import IBugEvent, IBugAddedEvent, \
     IBugCommentAddedEvent, IBugAssignedProductAddedEvent, \
     IBugAssignedPackageAddedEvent, IBugProductInfestationAddedEvent, \
     IBugPackageInfestationAddedEvent, IBugExternalRefAddedEvent, \
     IBugWatchAdded

class BugEvent(object):
    implements(IBugEvent)
    def __init__(self, object, cause):
        self.object = object
        self.cause = cause

class BugAssignedProductAddedEvent(BugEvent):
    implements(IBugAssignedProductAddedEvent)

class BugAssignedPackageAddedEvent(BugEvent):
    implements(IBugAssignedPackageAddedEvent)

class BugProductInfestationAddedEvent(BugEvent):
    implements(IBugProductInfestationAddedEvent)

class BugPackageInfestationAddedEvent(BugEvent):
    implements(IBugPackageInfestationAddedEvent)

class BugCommentAddedEvent(BugEvent):
    implements(IBugCommentAddedEvent)

class BugAddedEvent(BugEvent):
    implements(IBugAddedEvent)

class BugExternalRefAddedEvent(BugEvent):
    implements(IBugExternalRefAddedEvent)

class BugWatchAddedEvent(BugEvent):
    implements(IBugWatchAdded)
