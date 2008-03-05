# Copyright 2005-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Datetime, Int, List, Object, Text

from canonical.launchpad import _
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces.pofile import IPOFile
from canonical.launchpad.interfaces.potmsgset import IPOTMsgSet
from canonical.launchpad.interfaces.potranslation import IPOTranslation
from canonical.lazr import DBEnumeratedType, DBItem

__metaclass__ = type
__all__ = [
    'ITranslationMessage',
    'ITranslationMessageSet',
    'ITranslationMessageSuggestions',
    'RosettaTranslationOrigin',
    'TranslationConflict',
    'TranslationValidationStatus',
    ]


class TranslationConflict(Exception):
    """Someone updated the translation we are trying to update."""


class RosettaTranslationOrigin(DBEnumeratedType):
    """Rosetta Translation Origin

    Translation sightings in Rosetta can come from a variety
    of sources. We might see a translation for the first time
    in CVS, or we might get it through the web, for example.
    This schema documents those options.
    """

    SCM = DBItem(1, """
        Source Control Management Source

        This translation sighting came from a PO File we
        analysed in a source control managements sytem first.
        """)

    ROSETTAWEB = DBItem(2, """
        Rosetta Web Source

        This translation was presented to Rosetta via
        the community web site.
        """)


class TranslationValidationStatus(DBEnumeratedType):
    """Translation Validation Status

    Every time a translation is added to Rosetta we should checked that
    follows all rules to be a valid translation inside a .po file.
    This schema documents the status of that validation.
    """

    UNKNOWN = DBItem(0, """
        Unknown

        This translation has not been validated yet.
        """)

    OK = DBItem(1, """
        Ok

        This translation has been validated and no errors were discovered.
        """)

    UNKNOWNERROR = DBItem(2, """
        Unknown Error

        This translation has an unknown error.
        """)


class ITranslationMessage(Interface):
    """A translation message in a translation file."""

    id = Int(
        title=_("The ID for this translation message"),
        readonly=True, required=True)

    pofile = Object(
        title=_("The translation file from where this translation comes"),
        readonly=True, required=True, schema=IPOFile)

    potmsgset = Object(
        title=_("The template message that this translation is for"),
        readonly=True, required=True, schema=IPOTMsgSet)

    date_created = Datetime(
        title=_("The date we saw this translation first"),
        readonly=True, required=True)

    submitter = Object(
        title=_("The submitter of this translation"),
        readonly=True, required=True, schema=IPerson)

    date_reviewed = Datetime(
        title=_("The date when this message was reviewed for last time"),
        readonly=False, required=False)

    reviewer = Object(
        title=_(
            "The person who did the review and accepted current translations"
            ), readonly=False, required=False, schema=IPerson)

    # Message references for up to TranslationConstants.MAX_PLURAL_FORMS
    # plural forms.
    msgstr0 = Object(
        title=_("Translation for plural form 0 (if any)"),
        required=False, schema=IPOTranslation)

    msgstr1 = Object(
        title=_("Translation for plural form 1 (if any)"),
        required=False, schema=IPOTranslation)

    msgstr2 = Object(
        title=_("Translation for plural form 2 (if any)"),
        required=False, schema=IPOTranslation)

    msgstr3 = Object(
        title=_("Translation for plural form 3 (if any)"),
        required=False, schema=IPOTranslation)

    msgstr4 = Object(
        title=_("Translation for plural form 4 (if any)"),
        required=False, schema=IPOTranslation)

    msgstr5 = Object(
        title=_("Translation for plural form 5 (if any)"),
        required=False, schema=IPOTranslation)

    all_msgstrs = List(
        title=_("All msgstr attributes"),
        description=_("""
            All translations [msgstr0, msgstr1, ...] for this message,
            including any empty ones.
            """), readonly=True, required=True)

    translations = List(
        title=_("Translations for this message"),
        description=_("""
            All translations for this message, its number will depend on the
            number of plural forms available for its language.
            """), readonly=True, required=True)

    comment = Text(
        title=_("Text of translator comment from the translation file"),
        readonly=False, required=False)

    origin = Choice(
        title=_("Where the submission originally came from"),
        values=RosettaTranslationOrigin,
        readonly=True, required=True)

    validation_status = Choice(
        title=_("The status of the validation of the translation"),
        values=TranslationValidationStatus,
        readonly=False, required=True)

    is_current = Bool(
        title=_("Whether this translation is being used in Launchpad"),
        readonly=False, default=False, required=True)

    is_complete = Bool(
        title=_("Whether the translation has all needed plural forms or not"),
        readonly=True, required=True)

    is_fuzzy = Bool(
        title=_("Whether this translation must be checked before use it"),
        readonly=False, default=False, required=True)

    is_imported = Bool(
        title=_(
            "Whether this translation is being used in latest imported file"),
        readonly=False, default=False, required=True)

    was_obsolete_in_last_import = Bool(
        title=_(
            "Whether this translation was obsolete in last imported file"),
        readonly=False, default=False, required=True)

    was_fuzzy_in_last_import = Bool(
        title=_(
            "Whether this imported translation must be checked before use it"
            ), readonly=False, default=False, required=True)

    is_empty = Bool(
        title=_("Whether this message has any translation"),
        readonly=True, required=True)

    is_hidden = Bool(
        title=_("Whether this is an unused, hidden suggestion"),
        readonly=True, required=True)

    plural_forms = Int(
        title=_("Number of plural form translations in this translation."),
        readonly=True, required=True)

    # Used in a script to remove upstream translations.
    def destroySelf():
        """Remove this object.

        It must not be referenced by any other object.
        """

    # XXX CarlosPerelloMarin 20071022: We should move this into browser code.
    def makeHTMLID(description):
        """Unique identifier for self, suitable for use in HTML element ids.

        Constructs an identifier for use in HTML.  This identifier matches the
        format parsed by `BaseTranslationView`.

        :param description: a keyword to be embedded in the id string, e.g.
            "suggestion" or "translation."  Must be suitable for use in an
            HTML element id.
        """


class ITranslationMessageSuggestions(Interface):
    """Suggested `ITranslationMessage`s for a `POTMsgSet`.

    When displaying `POTMsgSet`s in `CurrentTranslationMessageView`
    we display different types of suggestions: non-reviewer translations,
    translations that occur in other contexts, and translations in
    alternate languages. See
    `CurrentTranslationMessageView._buildAllSuggestions` for details.
    """
    title = Attribute("The name displayed next to the suggestion, "
                      "indicating where it came from.")
    submissions = Attribute("An iterable of submissions.")
    user_is_official_translator = Bool(
        title=(u'Whether the user is an official translator.'),
        required=True)


class ITranslationMessageSet(Interface):
    """Getting to TranslationMessages from the view code."""

    def getByID(id):
        """Return the TranslationMessage with the given ID or None."""
