# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Country interfaces."""

__metaclass__ = type

__all__ = [
    'ICountry',
    'ICountrySet',
    'IContinent'
    ]

from zope.interface import Interface, Attribute
from zope.schema import Int, TextLine

from canonical.launchpad.fields import Title, Description
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad import _

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

    continent = Attribute("The Continent where this country is located.")
    languages = Attribute("An iterator over languages that are spoken in "
                          "that country.")


class ICountrySet(Interface):
    """A container for countries."""

    def __getitem__(key):
        """Get a country."""

    def __iter__():
        """Iterate through the countries in this set."""


class IContinent(Interface):
    """See IContinent."""

    id = Int(title=_('ID'), required=True, readonly=True)
    code = TextLine(title=_("Continent's code"), required=True, readonly=True)
    name = TextLine(title=_("Continent's name"), required=True, readonly=True)

