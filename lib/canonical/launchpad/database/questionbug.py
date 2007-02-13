# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""SQLBase implementation of ITicketBug."""

__metaclass__ = type

__all__ = ['TicketBug']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import ITicketBug

from canonical.database.sqlbase import SQLBase


class TicketBug(SQLBase):
    """A link between a ticket and a bug."""

    implements(ITicketBug)

    _table='TicketBug'

    ticket = ForeignKey(dbName='ticket', foreignKey='Ticket', notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)

    @property
    def target(self):
        """See IBugLink."""
        return self.ticket

