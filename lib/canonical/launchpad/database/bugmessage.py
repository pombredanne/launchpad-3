# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from email.Utils import make_msgid

# Zope
from zope.interface import implements
from zope.app import zapi

# SQL imports
from sqlobject import ForeignKey

from canonical.launchpad.interfaces import IBugMessage, ILaunchBag
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.message import Message, MessageChunk

class BugMessage(SQLBase):
    """A table linking bugs and messages."""

    implements(IBugMessage)

    _table = 'BugMessage'

    # db field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)


def BugMessageFactory(addview=None, title=None, content=None):
    """Create a BugMessage.

    This factory depends on ILaunchBag.user to figure out the message
    owner and the bug on which to add the message. addview is not used
    inside this factory.

    Returns an IBugMessage
    """
    msg = Message(
        parent=None, ownerID=zapi.getUtility(ILaunchBag).user.id,
        rfc822msgid=make_msgid('malone'), title=title)
    chunk = MessageChunk(
            messageID=msg.id, content=content, sequence=1,
            )
    bmsg = BugMessage(
        bug=zapi.getUtility(ILaunchBag).bug.id, message=msg.id)

    return bmsg
