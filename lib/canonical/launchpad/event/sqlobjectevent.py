from zope.interface import implements

from canonical.launchpad.event.interfaces import ISQLObjectModifiedEvent

class SQLObjectModifiedEvent(object):
    """An SQLObject has been modified."""

    implements(ISQLObjectModifiedEvent)

    def __init__(self, object, object_before_modification, edited_fields):
        self.object = object
        self.object_before_modification = object_before_modification
        self.edited_fields = edited_fields
