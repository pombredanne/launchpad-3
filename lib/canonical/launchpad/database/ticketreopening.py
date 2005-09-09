# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['TicketReopening']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import ITicketReopening

from canonical.lp.dbschema import EnumCol, TicketStatus


class TicketReopening(SQLBase):
    """A table recording each time a ticket is re-opened."""

    implements(ITicketReopening)

    _table = 'TicketReopening'

    ticket = ForeignKey(dbName='ticket', foreignKey='Ticket', notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    reopener = ForeignKey(dbName='reopener', foreignKey='Person',
        notNull=True)
    answerer = ForeignKey(dbName='answerer', foreignKey='Person',
        notNull=False, default=None)
    dateanswered = UtcDateTimeCol(notNull=False, default=None)
    priorstate = EnumCol(schema=TicketStatus, notNull=True)


