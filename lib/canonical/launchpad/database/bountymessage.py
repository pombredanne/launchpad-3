# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['BountyMessage', ]

from email.Utils import make_msgid

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad import _
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IBountyMessage
from canonical.launchpad.database.message import Message, MessageChunk


class BountyMessage(SQLBase):
    """A table linking bounties and messages."""

    implements(IBountyMessage)

    _table = 'BountyMessage'

    bounty = ForeignKey(dbName='bounty', foreignKey='Bounty', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)


