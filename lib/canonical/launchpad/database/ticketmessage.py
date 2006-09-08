# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TicketMessage',
    ]

from email.Utils import make_msgid

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad import _
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.interfaces import ITicketMessage, IMessage

from canonical.lp.dbschema import EnumCol, TicketAction, TicketStatus

class TicketMessage(SQLBase):
    """A table linking tickets and messages."""

    implements(ITicketMessage)

    _table = 'TicketMessage'

    ticket = ForeignKey(dbName='ticket', foreignKey='Ticket', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)

    action = EnumCol(
        schema=TicketAction, notNull=True, default=TicketAction.COMMENT)

    newstatus = EnumCol(
        schema=TicketStatus, notNull=True, default=TicketStatus.OPEN)

    def __getattr__(self, name):
        """Proxy all attributes in IMessage to the linked message"""
        if name in IMessage.names(all=True):
            return getattr(self.message, name)
        raise AttributeError, name