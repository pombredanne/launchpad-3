from zope.interface import Interface, Attribute
from zope.schema import Int
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IBugMessage(Interface):
    """A link between a bug and a message."""

    bug = Int(title = _('Bug ID'), required = True, readonly = True)
    message = Int(title = _('Message ID'), required = True, readonly = True)
