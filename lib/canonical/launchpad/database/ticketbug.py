# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['TicketBug']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import ITicketBug

from canonical.database.sqlbase import SQLBase


class TicketBug(SQLBase):
    """A link between a spec and a bug."""

    implements(ITicketBug)

    _table='TicketBug'

    ticket = ForeignKey(dbName='ticket', foreignKey='Ticket', notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)


