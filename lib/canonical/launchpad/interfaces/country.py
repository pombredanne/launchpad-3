# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute

class ICountry(Interface):
    """A Country."""

    iso3166code2 = Attribute("The ISO 3166 2 letter code for this country.")

    iso3166code3 = Attribute("The ISO 3166 3 letter code for this country.")

    name = Attribute("The name of this country.")

    title = Attribute("The title to use for this country.")

    description = Attribute("A description for this country.")

    languages = Attribute("A list of languages spoken in this country.")

