# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute

class ILanguage(Interface):
    """A Language."""

    code = Attribute("""The ISO 639 code for this language.""")

    englishname = Attribute("The English name of this language.")

    nativename = Attribute("The name of this language in the language itself.")

    pluralforms = Attribute("The number of plural forms this language has.")

    pluralexpression = Attribute("""The expression that relates a number of
        items to the appropriate plural form.""")

    translators = Attribute("""A list of Persons that are interested on 
        translate into this language.""")


class ILanguageSet(Interface):
    """The collection of languages."""

    def __iter__():
        """Returns an iterator over all languages."""

    def __getitem__(code):
        """Get a language by its code."""

    def keys():
        """Return an iterator over the language codes."""
