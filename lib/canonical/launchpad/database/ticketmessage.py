# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TicketMessage',
    ]

from email.Utils import make_msgid

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ITicketMessage
from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad import _


class TicketMessage(SQLBase):
    """A table linking tickets and messages."""

    implements(ITicketMessage)

    _table = 'TicketMessage'

    ticket = ForeignKey(dbName='ticket', foreignKey='Ticket', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)


