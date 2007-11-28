# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Language interfaces."""

__metaclass__ = type

__all__ = [
    'ILanguage',
    'ILanguageSet',
    'TextDirection',
    ]

from zope.schema import TextLine, Int, Choice, Bool, Field, Set
from zope.interface import Interface, Attribute

from canonical.lazr.enum import DBEnumeratedType, DBItem


class TextDirection(DBEnumeratedType):
    """The base text direction for a language."""

    LTR = DBItem(0, """
        Left to Right

        Text is normally written from left to right in this language.
        """)

    RTL = DBItem(1, """
        Right to Left

        Text is normally written from left to right in this language.
        """)


class ILanguage(Interface):
    """A Language."""

    id = Attribute("This Language ID.")

    code = TextLine(
        title=u'The ISO 639 code',
        required=True)

    englishname = TextLine(
        title=u'The English name',
        required=True)

    nativename = TextLine(
        title=u'Native name',
        description=u'The name of this language in the language itself.',
        required=False)

    pluralforms = Int(
        title=u'Number of plural forms',
        description=u'The number of plural forms this language has.',
        required=False)

    pluralexpression = TextLine(
        title=u'Plural form expression',
        description=(u'The expression that relates a number of items to the'
                     u' appropriate plural form.'),
        required=False)

    translators = Field(
        title=u'List of Person/Team that translate into this language.',
        required=True)

    translation_teams = Field(
        title=u'List of Teams that translate into this language.',
        required=True)

    countries = Set(
        title=u'Spoken in',
        description=u'List of countries this language is spoken in.',
        required=True,
        value_type=Choice(vocabulary="CountryName"))

    def addCountry(country):
        """Add a country to a list of countries this language is spoken in.

        Provided by SQLObject.
        """

    def removeCountry(country):
        """Remove a country from a list of countries this language is spoken in.

        Provided by SQLObject.
        """

    visible = Bool(
        title=u'Visible',
        description=(
            u'Whether this language should ususally be visible or not.'),
        required=True)

    direction = Choice(
        title=u'Text direction',
        description=u'The direction of text in this language.',
        required=True,
        vocabulary=TextDirection)

    displayname = TextLine(
        title=u'The displayname of the language',
        required=True,
        readonly=True)

    alt_suggestion_language = Attribute("A language which can reasonably "
        "be expected to have good suggestions for translations in this "
        "language.")

    dashedcode = TextLine(
        title=(u'The language code in a form suitable for use in HTML and'
               u' XML files.'),
        required=True,
        readonly=True)

    abbreviated_text_dir = TextLine(
        title=(u'The abbreviated form of the text direction, suitable for use'
               u' in HTML files.'),
        required=True,
        readonly=True)

class ILanguageSet(Interface):
    """The collection of languages."""

    common_languages = Attribute("An iterator over languages that are "
        "not hidden.")

    def __iter__():
        """Returns an iterator over all languages."""

    def __getitem__(code):
        """Return the language with the given code.

        If there is no language with the give code,
        raise NotFoundError exception.
        """

    def getLanguageByCode(code):
        """Return the language with the given code or None."""

    def keys():
        """Return an iterator over the language codes."""

    def canonicalise_language_code(code):
        """Convert a language code to standard xx_YY form."""

    def codes_to_languages(codes):
        """Convert a list of ISO language codes to language objects.

        Unrecognised language codes are ignored.
        """

    def getLanguageAndVariantFromString(language_string):
        """Return the ILanguage and variant that language_string represents.

        If language_string doesn't represent a know language, return None.
        """

    def createLanguage(code, englishname, nativename=None, pluralforms=None,
                       pluralexpression=None, visible=True,
                       direction=TextDirection.LTR):
        """Return a new created language.

        :arg code: ISO 639 language code.
        :arg englishname: English name for the new language.
        :arg nativename: Native language name.
        :arg pluralforms: Number of plural forms.
        :arg pluralexpression: Plural form expression.
        :arg visible: Whether this language should be showed by default.
        :arg direction: Text direction, either 'left to right' or 'right to
            left'.
        """

    def search(text):
        """Return a result set of ILanguage that match the search."""
