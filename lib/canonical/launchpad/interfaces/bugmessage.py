
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization


class IBugMessagesView(IAddFormCustomization):
    """BugMessage views"""

class IBugMessage(Interface):
    """A message about a bug."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    bug = Int(
            title=_('Bug ID'), required=True, readonly=True,
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
    personmsg = Int(
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
    attachments = Attribute('Bug Attachments')

