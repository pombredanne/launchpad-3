
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

class IBugAttachment(Interface):
    """A file attachment to an IMessage."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    messageID = Int(
            title=_('Message ID'), required=True, readonly=True,
            )
    message = Attribute('Message')
    name = TextLine(
            title=_('Name'), required=False, readonly=False,
            )
    description = Text(
            title=_('Description'), required=True, readonly=False,
            )
    libraryfile = Int(
            title=_('Library File'), required=True, readonly=False,
            )
    datedeactivated = Datetime(
            title=_('Date deactivated'), required=False, readonly=False,
            )

class IBugAttachmentSet(IAddFormCustomization):
    """A set for IBugAttachment objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get an Attachment."""

    def __iter__():
        """Iterate through BugAttachments for a given bug."""

