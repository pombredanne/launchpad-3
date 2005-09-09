# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['TicketSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import ITicketSubscription

from canonical.database.sqlbase import SQLBase


class TicketSubscription(SQLBase):
    """A subscription for person to a support ticket."""

    implements(ITicketSubscription)

    _table='TicketSubscription'

    ticket = ForeignKey(dbName='ticket', foreignKey='Ticket', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


