# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import string
from email.Utils import make_msgid

from zope.interface import implements
from zope.component import getUtility

from sqlobject import DateTimeCol, ForeignKey, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IMessage, IMessageSet, \
    ILaunchBag

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC



class Message(SQLBase):
    """A message. This is an RFC822-style message, typically it would be
    coming into the bug system, or coming in from a mailing list."""

    implements(IMessage)

    _table = 'Message'
    _defaultOrder = '-id'
    datecreated = DateTimeCol(notNull=True, default=nowUTC)
    title = StringCol(notNull=True)
    contents = StringCol(notNull=True)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    parent = ForeignKey(foreignKey='Message', dbName='parent',
                        notNull=False, default=None)
    distribution = ForeignKey(foreignKey='Distribution',
                              dbName='distribution',
                              notNull=False, default=None)
    rfc822msgid = StringCol(unique=True, notNull=True)
    bugs = RelatedJoin('Bug', joinColumn='message', otherColumn='bug',
                       intermediateTable='BugMessage')

    def followup_title(self):
        if string.lower(self.title[:4])=='re: ':
            return self.title
        return 'Re: '+self.title

    def sender(self):
        return self.owner

    sender = property(sender)


class MessageSet:
    implements(IMessageSet)

    def get(self, rfc822msgid=None):
        if not rfc822msgid:
            raise KeyError, 'Need to search on at least an rfc822msgid'
        return Message.selectBy(rfc822msgid=rfc822msgid)[0]


def BugMessageFactory(context, **kw):
    from canonical.launchpad.database import BugMessage
    msg = Message(
        parent=None, ownerID = getUtility(ILaunchBag).user.id,
        rfc822msgid=make_msgid('malone'), **kw)
    bmsg = BugMessage(bug = getUtility(ILaunchBag).bug.id, message = msg.id)
    return bmsg
