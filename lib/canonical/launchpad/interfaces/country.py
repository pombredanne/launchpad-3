
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute, classImplements

from zope.schema import Choice, Datetime, Int, Text, TextLine, Float
from zope.schema.interfaces import IText, ITextLine

from canonical.launchpad.fields import Summary, Title, Description
from canonical.launchpad.validators.name import valid_name


class ICountry(Interface):
    """The country description."""

    id = Int(
            title=_('Country ID'), required=True, readonly=True,
            )
    iso3166code2 = TextLine( title=_('iso3166code2'), required=True,
                             readonly=True)
    iso3166code3 = TextLine( title=_('iso3166code3'), required=True,
                             readonly=True)
    name = TextLine(
            title=_('Country name'), required=True,
            constraint=valid_name,
            )
    title = Title(
            title=_('Country title'), required=True,
            )
    description = Description(
            title=_('Description'), required=True,
            )


# Interfaces for containers
class ICountrySet(Interface):
    """A container for countries."""

    def __getitem__(key):
        """Get a country."""

    def __iter__():
        """Iterate through the countries in this set."""

