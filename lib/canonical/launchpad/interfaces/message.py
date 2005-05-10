# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute
from zope.exceptions import NotFoundError
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

__all__ = [
    'IMessagesView', 'IMessage', 'IMessageSet', 'IMessageChunk',
    'IAddMessage', 'UnknownSender', 'MissingSubject', 'DuplicateMessageId',
    'InvalidEmailMessage',
    ]

class IMessagesView(IAddFormCustomization):
    """Message views"""


class IMessage(Interface):
    """A message. This is like an email (RFC822) message, though it could be
    created through the web as well."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    title = TextLine(
            title=_('Title'), required=True, readonly=True,
            )
    owner = Int(
            title=_('Person'), required=False, readonly=True,
            )
    parent = Int(
            title=_('Parent'), required=False, readonly=True,
            )
    distribution = Int(
            title=_('Distribution'), required=False, readonly=True,
            )
    rfc822msgid = TextLine(
            title=_('RFC822 Msg ID'), required=True, readonly=True,
            )
    raw = Int(
            title=_('Original unmodified email'), required=False,
            readonly=True
            )
    bugs = Attribute(_('Bug List'))
    chunks = Attribute(_('Message pieces'))
    contents = Attribute(_('Full message contents as plain text'))
    followup_title = Attribute(_("Candidate title for a followup message."))


class IMessageSet(Interface):
    """Set of IMessage"""

    def get(rfc822msgid=None):
        """Return a single IMessage matching the given criteria. Currently
        the only search criterion supported is an rfc822msgid."""

    def fromEmail(email_message, owner=None, filealias=None,
            parsed_message=None):
        """Construct a Message from an email message and return it.

        `email_message` should be the original email as a string.

        `owner` specifies the owner of the new Message. The default
        is calculated using the From: or Reply-To: headers, and will raise
        a UnknownSender error if they cannot be found.

        `filealias` is the LibraryFileAlias of the raw email if it has
        already been stuffed into the Librarian. Default is for this
        method to stuff it into the Librarian for you. It should be an
        ILibraryFileAlias.

        `parsed_message` may be an email.Message.Message instance. If given,
        it is used internally instead of building one from the raw
        email_message. This is purely an optimization step, significant
        in many places because the emails we are handling may contain huge
        attachments and we should avoid reparsing them if possible.

        Callers may want to explicitly handle the following exceptions:
            * UnknownSender
            * MissingSubject
            * DuplicateMessageId
            * InvalidEmailMessage
        """


class IMessageChunk(Interface):
    id = Int(title=_('ID'), required=True, readonly=True)
    message = Int(title=_('Message'), required=True, readonly=True)
    sequence = Int(title=_('Sequence order'), required=True, readonly=True)
    content = Text(title=_('Text content'), required=False, readonly=True)
    blob = Int(title=_('Binary content'), required=False, readonly=True)


class IAddMessage(Interface):
    """This schema is used to generate the add comment form"""
    title = TextLine(title=_("Subject"), required=True)
    content = Text(title=_("Body"), required=True)


class UnknownSender(NotFoundError):
    """Raised if we cannot lookup an email message's sender in the database"""


class MissingSubject(ValueError):
    """Raised if we get an email message with no Subject: header"""


class DuplicateMessageId(ValueError):
    """Raised if we attempt to store a new email with an existing Message-Id

    Indicates a broken mail client or MTA.
    """


class InvalidEmailMessage(ValueError):
    """Raised if the email message is too broken for us to deal with.

    This indicates broken mail clients or MTAs, and is raised on conditions
    such as missing Message-Id or missing From: headers.
    """
