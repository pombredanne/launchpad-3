# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugMessage', 'BugMessageSet']

from email.Utils import make_msgid

from zope.interface import implements
from zope.component import getUtility
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import (
    IBugMessage, IBugMessageSet, ILaunchBag)
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.message import Message, MessageChunk

class BugMessage(SQLBase):
    """A table linking bugs and messages."""

    implements(IBugMessage)

    _table = 'BugMessage'

    # db field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)

class BugMessageSet:
    """See canonical.launchpad.interfaces.IBugMessageSet."""

    implements(IBugMessageSet)

    def createMessage(self, subject, bug, owner, content=None):
        """See canonical.launchpad.interfaces.IBugMessageSet."""
        msg = Message(
            parent=None, ownerID=owner.id, rfc822msgid=make_msgid('malone'),
            subject=subject)
        chunk = MessageChunk(messageID=msg.id, content=content, sequence=1)
        bugmsg = BugMessage(bugID=bug.id, messageID=msg.id)

        return bugmsg

    def get(self, bugmessageid):
        """See canonical.launchpad.interfaces.IBugMessageSet."""
        return BugMessage.get(bugmessageid)
