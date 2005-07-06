# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Message', 'MessageSet', 'MessageChunk']

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

import email
from email.Utils import parseaddr, parsedate_tz, mktime_tz
from cStringIO import StringIO as cStringIO
from datetime import datetime

from zope.interface import implements
from zope.component import getUtility
from zope.security.proxy import isinstance
from zope.exceptions import NotFoundError

from sqlobject import ForeignKey, StringCol, IntCol
from sqlobject import MultipleJoin, RelatedJoin

import pytz

from canonical.lp.encoding import guess as ensure_unicode
from canonical.launchpad.helpers import get_filename_from_message_id
from canonical.launchpad.interfaces import \
    IMessage, IMessageSet, IMessageChunk, IPersonSet, \
    ILibraryFileAliasSet, UnknownSender, MissingSubject, \
    DuplicateMessageId, InvalidEmailMessage

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.foaf.nickname import NicknameGenerationError

# this is a hard limit on the size of email we will be willing to store in
# the database.
MAX_EMAIL_SIZE = 128*1024

class Message(SQLBase):
    """A message. This is an RFC822-style message, typically it would be
    coming into the bug system, or coming in from a mailing list.
    """

    implements(IMessage)

    _table = 'Message'
    _defaultOrder = '-id'
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    subject = StringCol(notNull=False, default=None)
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
        """See IMessage.__iter__"""
        return iter(self.chunks)

    @property
    def followup_title(self):
        """See IMessage."""
        if self.title.lower().startswith('re: '):
            return self.title
        return 'Re: '+self.title

    @property
    def title(self):
        """See IMessage."""
        return self.subject

    @property
    def sender(self):
        """See IMessage."""
        return self.owner

    @property
    def contents(self):
        """See IMessage."""
        bits = [unicode(chunk) for chunk in self]
        return '\n\n'.join(bits)


def get_parent_msgid(parsed_message):
    """Returns the message id the mail was a reply to.

    If it can't be identified, None is returned.

        >>> get_parent_msgid({'In-Reply-To': '<msgid1>'})
        '<msgid1>'

        >>> get_parent_msgid({'References': '<msgid1> <msgid2>'})
        '<msgid2>'

        >>> get_parent_msgid({'In-Reply-To': '<msgid1> <msgid2>'})
        '<msgid2>'

        >>> get_parent_msgid({'In-Reply-To': '', 'References': ''}) is None
        True

        >>> get_parent_msgid({}) is None
        True
    """
    for name in ['In-Reply-To', 'References']:
        if parsed_message.has_key(name):
            msgids = parsed_message[name].split()
            if len(msgids) > 0:
                return parsed_message.get(name).split()[-1]

    return None


class MessageSet:
    implements(IMessageSet)

    def get(self, rfc822msgid):
        messages = list(Message.selectBy(rfc822msgid=rfc822msgid))
        if len(messages) == 0:
            raise NotFoundError(rfc822msgid)
        return messages

    def _decode_header(self, header):
        """Decode an encoded header possibly containing Unicode."""
        bits = email.Header.decode_header(header)
        return unicode(email.Header.make_header(bits))

    def fromEmail(self, email_message, owner=None, filealias=None,
            parsed_message=None, distribution=None,
            create_missing_persons=False):
        """See IMessageSet.fromEmail."""
        # It does not make sense to handle Unicode strings, as email
        # messages may contain chunks encoded in differing character sets.
        # Passing Unicode in here indicates a bug.
        if not isinstance(email_message, str):
            raise TypeError(
                'email_message must be a normal string.  Got: %r'
                % email_message)

        # Parse the raw message into an email.Message.Message instance,
        # if we haven't been given one already.
        if parsed_message is None:
            parsed_message = email.message_from_string(email_message)

        # We could easily generate a default, but a missing message-id
        # almost certainly means a developer is using this method when
        # they shouldn't (by creating emails by hand and passing them here),
        # which is broken because they will almost certainly have Unicode
        # errors.
        rfc822msgid = parsed_message.get('message-id')
        if not rfc822msgid:
            raise InvalidEmailMessage('Missing Message-Id')

        # make sure we don't process anything too long
        if len(email_message) > MAX_EMAIL_SIZE:
            raise InvalidEmailMessage('Msg %s size %d exceeds limit %d' % (
                rfc822msgid, len(email_message), MAX_EMAIL_SIZE))

        # Handle duplicate Message-Id
        try:
            existing_msgs = self.get(rfc822msgid=rfc822msgid)
        except LookupError:
            pass
        else:
            # we are now allowing multiple msgs in the db with the same
            # rfc822 msg-id to allow for variations in headers and,
            # potentially, content. so we scan through the results to try
            # and find one that matches,
            for existing in existing_msgs:
                existing_raw = existing.raw.read()
                if email_message == existing_raw:
                    return existing
                # ok, this is an interesting situation. we have a new
                # message with the same rfc822 msg-id as an existing message
                # in the database, but the message headers and/or content
                # are different. For the moment, we have chosen to allow
                # this, but in future we may want to flag it in some way
                pass

        # Stuff a copy of the raw email into the Librarian, if it isn't
        # already in there.
        file_alias_set = getUtility(ILibraryFileAliasSet) # Reused later
        if filealias is None:
            # We generate a filename to avoid people guessing the URL.
            # We don't want URLs to private bug messages to be guessable
            # for example.
            raw_filename = get_filename_from_message_id(
                parsed_message['message-id'])
            raw_email_message = file_alias_set.create(
                    raw_filename, len(email_message),
                    cStringIO(email_message), 'message/rfc822')
        else:
            raw_email_message = filealias

        # Find the message subject
        subject = self._decode_header(parsed_message.get('subject', '')).strip()

        if owner is None:
            # Try and determine the owner. We raise a NotFoundError
            # if the sender does not exist, unless we were asked to
            # create_missing_persons.
            person_set = getUtility(IPersonSet)
            from_hdr = self._decode_header(
                parsed_message.get('from', '')).strip()
            replyto_hdr = self._decode_header(
                parsed_message.get('reply-to', '')).strip()
            from_addrs = [from_hdr, replyto_hdr]
            from_addrs = [parseaddr(addr) for addr in from_addrs if addr]
            if len(from_addrs) == 0:
                raise InvalidEmailMessage('No From: or Reply-To: header')
            for from_addr in from_addrs:
                owner = person_set.getByEmail(from_addr[1].lower().strip())
                if owner is not None:
                    break
            if owner is None:
                if not create_missing_persons:
                    raise UnknownSender(from_addrs[0][1])
                # autocreate a person
                sendername = ensure_unicode(from_addrs[0][0].strip())
                senderemail = from_addrs[0][1].lower().strip()
                owner = person_set.ensurePerson(senderemail, sendername)
                if owner is None:
                    raise UnknownSender(senderemail)

        # get the parent email, if needed and available in the db
        parent_msgid = get_parent_msgid(parsed_message)
        if parent_msgid is None:
            parent = None
        else:
            try:
                # we assume it's the first matching message
                parent = self.get(parent_msgid)[0]
            except NotFoundError:
                parent = None

        # figure out the date of the message
        try:
            datestr = parsed_message['date']
            thedate = parsedate_tz(datestr)
            timestamp = mktime_tz(thedate)
            datecreated = datetime.fromtimestamp(timestamp,
                tz=pytz.timezone('UTC'))
        except (TypeError, ValueError, OverflowError):
            raise InvalidEmailMessage('Invalid date %s' % datestr)
        # make sure we don't create an email with a datecreated in the
        # future. also make sure we don't create an ancient one
        now = datetime.now(pytz.timezone('UTC'))
        thedistantpast = datetime(1990, 1, 1, tzinfo=pytz.timezone('UTC'))
        if datecreated < thedistantpast or datecreated > now:
            datecreated = UTC_NOW

        # DOIT
        message = Message(subject=subject, ownerID=owner.id,
            rfc822msgid=rfc822msgid, parent=parent,
            rawID=raw_email_message.id, datecreated=datecreated,
            distribution=distribution)

        # Determine the encoding to use for non-multipart messages, and the
        # preamble and epilogue of multipart messages. We default to iso-8859-1
        # as it seems fairly harmless to cope with old, broken email clients
        # (The RFCs state US-ASCII as the default character set).
        default_charset = parsed_message.get_content_charset() or 'iso-8859-1'

        sequence = 1
        if getattr(parsed_message, 'preamble', None):
            # We strip a leading and trailing newline - the email parser
            # seems to arbitrarily add them :-/
            preamble = parsed_message.preamble.decode(
                    default_charset, 'replace')
            if preamble.strip():
                if preamble[0] == '\n':
                    preamble = preamble[1:]
                if preamble[-1] == '\n':
                    preamble = preamble[:-1]
                MessageChunk(
                    messageID=message.id, sequence=sequence, content=preamble
                    )
                sequence += 1

        for part in parsed_message.walk():
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
                    content = content.decode(charset, 'replace')
                if content.strip():
                    MessageChunk(
                        messageID=message.id, sequence=sequence,
                        content=content
                        )
                    sequence += 1
            else:
                filename = part.get_filename() or 'unnamed'
                # Note we use the Content-Type header instead of
                # part.get_content_type() here to ensure we keep
                # parameters as sent
                if len(content) > 0:
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

        if getattr(parsed_message, 'epilogue', None):
            epilogue = parsed_message.epilogue.decode(
                    default_charset, 'replace')
            if epilogue.strip():
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

