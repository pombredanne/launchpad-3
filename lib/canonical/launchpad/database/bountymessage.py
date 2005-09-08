# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BountyMessage', ]

from email.Utils import make_msgid

from zope.interface import implements
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IBountyMessage

from canonical.launchpad.database.message import Message, MessageChunk


class BountyMessage(SQLBase):
    """A table linking bounties and messages."""

    implements(IBountyMessage)

    _table = 'BountyMessage'

    bounty = ForeignKey(dbName='bounty', foreignKey='Bounty', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)


