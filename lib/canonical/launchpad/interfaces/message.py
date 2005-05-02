# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

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

    def get(rfc822msgid=None):
        """Return a single IMessage matching the given criteria. Currently
        the only search criterion supported is an rfc822msgid."""

    def fromEmail(email_message):
        """Construct a Message from an email message and return it.

        `email_message` should be the original email as a string.
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

