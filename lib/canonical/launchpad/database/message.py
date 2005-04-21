# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

import email
from email.Utils import parseaddr
from cStringIO import StringIO as cStringIO

from zope.interface import implements
from zope.component import getUtility
from zope.security.proxy import isinstance
from zope.exceptions import NotFoundError

from sqlobject import DateTimeCol, ForeignKey, StringCol, IntCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import \
        IMessage, IMessageSet, IMessageChunk, IPersonSet, ILibraryFileAliasSet

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

class MessageSet:
    implements(IMessageSet)

    def get(self, rfc822msgid=None):
        if not rfc822msgid:
            raise KeyError, 'Need to search on at least an rfc822msgid'
        try:
            return Message.selectBy(rfc822msgid=rfc822msgid)[0]
        except IndexError:
            raise NotFoundError('rfc822msgid=%s' % (rfc822msgid,))

    def _decode_header(self, header):
        """Decode an encoded header possibly containing Unicode"""
        bits = email.Header.decode_header(header)
        return unicode(email.Header.make_header(bits))

    def fromEmail(self, email_message):
        """See IMessageSet.fromEmail"""
        # It does not make sense to handle Unicode strings, as email
        # messages may contain chunks encoded in differing character sets.
        # Passing Unicode in here indicates a bug.
        if not isinstance(email_message, str):
            raise TypeError('email_message must be a normal string')

        # Stuff a copy of the raw email into the Librarian
        file_alias_set = getUtility(ILibraryFileAliasSet)
        raw_email_message = file_alias_set.create(
                'raw.msg', len(email_message), cStringIO(email_message),
                'message/rfc822'
                )

        email_message = email.message_from_string(email_message)

        title = self._decode_header(email_message.get('subject', ''))
        if not title:
            raise ValueError('No Subject')
        
        # We could easily generate a default, but a missing message-id
        # almost certainly means a developer is using this method when
        # they shouldn't (by creating emails by hand and passing them here),
        # which is broken because they will almost certainly have Unicode
        # errors.
        rfc822msgid = email_message.get('message-id')
        if not rfc822msgid:
            raise ValueError('No Message-Id')

        # Try and determine the owner. We raise a NotFoundError
        # if the sender does not exist.
        person_set = getUtility(IPersonSet)
        owner = None
        from_addrs = [email_message['from'], email_message['reply-to']]
        from_addrs = [parseaddr(addr) for addr in from_addrs if addr]
        from_addrs = [addr for name, addr in from_addrs if addr]
        if len(from_addrs) == 0:
            raise ValueError, 'No From: or Reply-To: header'
        owner = None
        for from_addr in from_addrs:
            owner = person_set.getByEmail(from_addr)
            if owner is not None:
                break
        # TODO: Should we autocreate a Person if the From:
        # address does not exist in the EmailAddres table?
        # -- StuartBishop 20050419
        if owner is None:
            raise NotFoundError(from_addrs[0])

        message = Message(
            title=title,
            ownerID=owner.id,
            rfc822msgid=rfc822msgid,
            rawID=raw_email_message.id
            )

        # Determine the encoding to use for non-multipart messages, and the
        # preamble and epilogue of multipart messages.
        default_charset = email_message.get_content_charset() or 'us-ascii'

        sequence = 1
        if getattr(email_message, 'preamble', None):
            # We strip a leading and trailing newline - the email parser
            # seems to arbitrarily add them :-/
            preamble = email_message.preamble.decode(default_charset)
            if preamble[0] == '\n':
                preamble = preamble[1:]
            if preamble[-1] == '\n':
                preamble = preamble[:-1]
            MessageChunk(
                    messageID=message.id, sequence=sequence, content=preamble
                    )
            sequence += 1

        for part in email_message.walk():
            mime_type = part.get_content_type()

            # Skip the multipart section that walk gives us. This part
            # is the entire message.
            if mime_type.startswith('multipart/'):
                continue

            # Decode the content of this part.
            content = part.get_payload(decode=True)

            # Store the part as a MessageChunk
            if mime_type == 'text/plain':
                charset = part.get_content_charset()
                if charset:
                    content = content.decode(charset)
                MessageChunk(
                        messageID=message.id, sequence=sequence,
                        content=content
                        )
            else:
                filename = part.get_filename() or 'unnamed'
                # Note we use the Content-Type header instead of
                # part.get_content_type() here to ensure we keep
                # parameters as sent
                blob = file_alias_set.create(
                        name=filename,
                        size=len(content),
                        file=cStringIO(content),
                        contentType=part['content-type']
                        )
                MessageChunk(
                        messageID=message.id, sequence=sequence,
                        blobID=blob.id
                        )
            sequence += 1

        if getattr(email_message, 'epilogue', None):
            epilogue = email_message.epilogue.decode(default_charset)
            if epilogue[0] == '\n':
                epilogue = epilogue[1:]
            if epilogue[-1] == '\n':
                epilogue = epilogue[:-1]
            MessageChunk(
                    messageID=message.id, sequence=sequence, content=epilogue
                    )

        return message


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

