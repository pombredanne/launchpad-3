from email.Utils import make_msgid
import string

# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IMessage, IMessageSet

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
    attachments = MultipleJoin('BugAttachment', joinColumn='bugmessage')
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
    bug = context.context.context.id # view.comments.bug
    msg = Message(
        parent=None, ownerID=context.request.principal.id,
        rfc822msgid=make_msgid('malone'), **kw)
    bmsg = BugMessage(bug=bug, message=msg.id)
    return bmsg
