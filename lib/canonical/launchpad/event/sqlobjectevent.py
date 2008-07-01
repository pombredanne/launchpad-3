# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['SQLObjectCreatedEvent',
           'SQLObjectDeletedEvent',
           'SQLObjectModifiedEvent',
           ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.event.interfaces import (
    ISQLObjectModifiedEvent, ISQLObjectCreatedEvent,
    ISQLObjectDeletedEvent)


class SQLObjectEventBase:
    """Base class for all SQLObject event."""

    def __init__(self, object, user=None):
        self.object = object
        if user is not None:
            self.user = user
        else:
            # Prevent a circular import between launchpadform and
            # this module.
            from canonical.launchpad.webapp.interfaces import ILaunchBag
            self.user = getUtility(ILaunchBag).user


class SQLObjectCreatedEvent(SQLObjectEventBase):
    """See canonical.launchpad.event.interfaces.ISQLObjectCreatedEvent."""

    implements(ISQLObjectCreatedEvent)


class SQLObjectDeletedEvent(SQLObjectEventBase):
    """See ISQLObjectDeletedEvent."""

    implements(ISQLObjectDeletedEvent)


class SQLObjectModifiedEvent(SQLObjectEventBase):
    """See canonical.launchpad.event.interfaces.ISQLObjectModifiedEvent."""

    implements(ISQLObjectModifiedEvent)

    def __init__(self, object, object_before_modification, edited_fields,
                 user=None):
        SQLObjectEventBase.__init__(self, object, user=user)
        self.object_before_modification = object_before_modification
        self.edited_fields = edited_fields
