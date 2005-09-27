# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugMessage', 'BugMessageSet']

from email.Utils import make_msgid

from zope.interface import implements
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IBugMessage, IBugMessageSet
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
            parent=bug.initial_message, owner=owner,
            rfc822msgid=make_msgid('malone'), subject=subject)
        chunk = MessageChunk(message=msg, content=content, sequence=1)
        bugmsg = BugMessage(bug=bug, message=msg)

        return bugmsg

    def get(self, bugmessageid):
        """See canonical.launchpad.interfaces.IBugMessageSet."""
        return BugMessage.get(bugmessageid)

    def getByBugAndMessage(self, bug, message):
        """See canonical.launchpad.interfaces.IBugMessageSet."""
        # XXX: selectOneBy(bug=bug, message=message) doesn't work.
        #      -- Bjorn Tillenius, 2005-07-18, Bug #1555
        return BugMessage.selectOneBy(bugID=bug.id, messageID=message.id)
