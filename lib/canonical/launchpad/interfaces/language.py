# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute

class ILanguage(Interface):
    """A Language."""

    code = Attribute("""The ISO 639 code for this language.""")

    englishName = Attribute("The English name of this language.")

    nativeName = Attribute("The name of this language in the language itself.")

    pluralForms = Attribute("The number of plural forms this language has.")

    pluralExpression = Attribute("""The expression that relates a number of
        items to the appropriate plural form.""")

    # XXX: Review. Do you think this method is good for the interface?.
    def translateLabel():
        """The ILabel used to say that some is interested on ILanguage"""

    def translators():
        """The Persons that are interested on translate into this language."""


class ILanguageSet(Interface):
    """The collection of languages."""

    def __iter__():
        """Returns an iterator over all languages."""

    def __getitem__(code):
        """Get a language by its code."""

    def keys():
        """Return an iterator over the language codes."""
