# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

import email

from zope.interface import implements
from zope.component import getUtility
from zope.security.proxy import isinstance

from sqlobject import DateTimeCol, ForeignKey, StringCol, IntCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces \
        import IMessage, IMessageSet, IMessageChunk

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
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    parent = ForeignKey(foreignKey='Message', dbName='parent',
                        notNull=False, default=None)
    distribution = ForeignKey(foreignKey='Distribution',
                              dbName='distribution',
                              notNull=False, default=None)
    rfc822msgid = StringCol(unique=True, notNull=True)
    bugs = RelatedJoin('Bug', joinColumn='message', otherColumn='bug',
                       intermediateTable='BugMessage')
    chunks = MultipleJoin('MessageChunk', joinColumn='message')
    raw = ForeignKey(foreignKey='LibraryFileAlias', dbName='raw', default=None)

    def __iter__(self):
        """Iterate over all chunks"""
        return iter(self.chunks)

    def followup_title(self):
        if self.title[:4].lower()=='re: ':
            return self.title
        return 'Re: '+self.title
    followup_title = property(followup_title)

    def sender(self):
        return self.owner
    sender = property(sender)

    def contents(self):
        bits = []
        for chunk in iter(self):
            bits.append(unicode(chunk))
        return '\n\n'.join(bits)
    contents = property(contents)

    def fromEmail(cls, msg):
        """Construct a Message from an email message.

        msg may be a string or an email.Message.Message instance.
        """
        # Handle being passed Unicode. Email messages passed as Unicode
        # strings may only be 7-bit encoded.
        if isinstance(msg, unicode):
            msg = msg.encode('US-ASCII')

        # Convert strings to email.Message instances
        if isinstance(msg, basestring):
            msg = email.message_from_string(msg)

        if not isinstance(msg, email.Message.Message):
            raise ValueError, 'Invalid parameter msg'

        raise NotImplementedError, 'Not finished'
    fromEmail = classmethod(fromEmail)


class MessageSet:
    implements(IMessageSet)

    def get(self, rfc822msgid=None):
        if not rfc822msgid:
            raise KeyError, 'Need to search on at least an rfc822msgid'
        return Message.selectBy(rfc822msgid=rfc822msgid)[0]


class MessageChunk(SQLBase):
    """One part of a possibly multipart Message"""
    implements(IMessageChunk)

    _table = 'MessageChunk'
    _defaultOrder = 'sequence'

    message = ForeignKey(
            foreignKey='Message', dbName='message', notNull=True)

    sequence = IntCol(notNull=True)

    content = StringCol(notNull=False, default=None)

    blob = ForeignKey(
            foreignKey='LibraryFileAlias', dbName='blob', notNull=False,
            default=None
            )

    def __unicode__(self):
        """Return a text representation of this chunk.
        
        This is either the content, or a link to the blob in a format
        suitable for use in a text only environment, such as an email
        """
        if self.content:
            return self.content
        else:
            blob = self.blob
            return (
                    "Attachment: %s\n"
                    "Type:       %s\n"
                    "URL:        %s" % (blob.filename, blob.mimetype, blob.url)
                    )

