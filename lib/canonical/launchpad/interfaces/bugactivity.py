
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine


class IBugActivity(Interface):
    """A log of all things that have happened to a bug."""

    bug = Int(title=_('Bug ID'))
    datechanged = Datetime(title=_('Date Changed'))
    person = Int(title=_('Person'))
    whatchanged = TextLine(title=_('What Changed'))
    oldvalue = TextLine(title=_('Old Value'))
    newvalue = TextLine(title=_('New Value'))
    message = Text(title=_('Message'))

