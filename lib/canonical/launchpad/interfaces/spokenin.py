
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute, classImplements

from zope.schema import Choice, Datetime, Int, Text, TextLine, Float
from zope.schema.interfaces import IText, ITextLine

from canonical.launchpad.fields import Summary, Title, TimeInterval
from canonical.launchpad.validators.name import valid_name


class ISpokenIn(Interface):
    """The SPokenIn description."""

    id = Int(
            title=_('SpokenInID'), required=True, readonly=True,
            )

    country = Int(title=_('Country'), required=True, readonly=True)

    language = Int(title=_('Language'), required=True, readonly=True)

