
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
    contents = Text(
            title=_('Contents'), required=True, readonly=True,
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
    bugs = Attribute(_('Bug List'))

    def followup_title():
        """Return a candidate title for a followup message."""


class IMessageSet(Interface):

    def get(rfc822msgid=None):
        """Return a single IMessage matching the given criteria. Currently
        the only search criterion supported is an rfc822msgid."""
