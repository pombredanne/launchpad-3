# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.event.interfaces import ISQLObjectModifiedEvent, \
    ISQLObjectToBeModifiedEvent, ISQLObjectCreatedEvent

class SQLObjectCreatedEvent:
    """See canonical.launchpad.event.interfaces.ISQLObjectCreatedEvent."""

    implements(ISQLObjectCreatedEvent)

    def __init__(self, object, request):
        self.object = object
        self.request = request


class SQLObjectModifiedEvent:
    """See canonical.launchpad.event.interfaces.ISQLObjectModifiedEvent."""

    implements(ISQLObjectModifiedEvent)

    def __init__(self, object, object_before_modification, edited_fields,
                 principal, request):
        self.object = object
        self.object_before_modification = object_before_modification
        self.edited_fields = edited_fields
        self.principal = principal
        self.request = request


class SQLObjectToBeModifiedEvent:
    """See canonical.launchpad.event.interfaces.ISQLObjectToBeModifiedEvent."""

    implements(ISQLObjectToBeModifiedEvent)

    def __init__(self, object, new_values):
        self.object = object
        self.new_values = new_values
