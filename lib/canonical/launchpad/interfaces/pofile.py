# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__metaclass__ = type

__all__ = [
    'ZeroLengthPOExportError',
    'IPOFileSet',
    'IPOFile',
    'IPOFileTranslator',
    'IPOFileAlternativeLanguage',
    ]

from zope.component import getUtility
from zope.interface import Attribute, implements, Interface
from zope.schema import (
    Bool, Choice, Datetime, Field, Int, List, Object, Text, TextLine)
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import (
    getVocabularyRegistry, SimpleTerm, SimpleVocabulary)

from canonical.launchpad import _
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces.potemplate import IPOTemplate
from canonical.launchpad.interfaces.rosettastats import IRosettaStats
from canonical.launchpad.interfaces.translationgroup import (
    TranslationPermission)


class ZeroLengthPOExportError(Exception):
    """An exception raised when a PO file export generated an empty file."""


class IPOFile(IRosettaStats):
    """A translation file."""

    id = Int(
        title=_('The translation file id.'), required=True, readonly=True)

    potemplate = Object(
        title=_('The translation file template.'),
        required=True, readonly=True, schema=IPOTemplate)

    language = Choice(
        title=_('Language of this PO file.'),
        vocabulary='Language', required=True)

    variant = TextLine(
        title=_('The language variant for this translation file.'))

    title = TextLine(
        title=_('The translation file title.'), required=True, readonly=True)

    description = Text(
        title=_('The translation file description.'), required=True)

    topcomment = Text(
        title=_('A comment about this translation file.'), required=True)

    header = Text(
        title=_('Header'),
        description=_(
            'The standard translation header in its native format.'),
        required=False)

    fuzzyheader = Bool(
        title=_('A flag indicating whether the header is fuzzy.'),
        required=True)

    lasttranslator = Object(
        title=_('Last person that translated a message.'), schema=IPerson)

    date_changed = Datetime(
        title=_('When this file was last changed.'), readonly=False,
        required=True)

    license = Int(title=_('The license under this translation is done.'))

    lastparsed = Datetime(title=_('Last time this pofile was parsed.'))

    owner = Choice(
        title=_('Translation file owner'),
        required=True,
        description=_('''
            The owner of the translation file in Launchpad can edit its
            translations and upload new versions.
            '''),
        vocabulary="ValidOwner")

    path = TextLine(
        title=_('The path to the file that was imported'),
        required=True)

    exportfile = Object(
        title=_('Last cached export file'),
        required=True, schema=ILibraryFileAlias)

    is_cached_export_valid = Bool(
        title=_(
            "Whether this translation file have an up to date cached export"),
        readonly=True, required=True)

    datecreated = Datetime(
        title=_('When this translation file was created.'), required=True)

    translators = List(
        title=_('Translators that have edit permissions.'),
        description=_('''
            Translators designated as having permission to edit these files
            in this language.
            '''), required=True, readonly=True)

    contributors = List(
        title=_('Translators who have made any contribution to this file.'),
        required=True, readonly=True)

    translationpermission = Choice(
        title=_('Translation permission'),
        required=True,
        description=_('''
            The permission system which is used for this translation file.
            This is inherited from the product, project and/or distro in which
            the pofile is found.
            '''),
        vocabulary=TranslationPermission)

    fuzzy_count = Int(
        title=_('The number of fuzzy messages in this po file.'),
        required=True, readonly=True)

    from_sourcepackagename = Field(
        title=_('The source package this pofile comes from.'),
        description=_('''
            The source package this pofile comes from (set it only if it\'s
            different from IPOFile.potemplate.sourcepackagename).
            '''),
        required=False)

    translation_messages = Attribute(_(
        'All `ITranslationMessage` objects related to this translation file.'
        ))

    plural_forms = Int(
        title=_('Number of plural forms for the language of this PO file.'),
        description=_('''
            Number of plural forms is a number of translations provided for
            each plural form message.  If `IPOFile.language` does not specify
            plural forms, it defaults to 2, which is the most common number
            of plural forms.
            '''),
        required=True, readonly=True)

    def translatedCount():
        """
        Returns the number of message sets which this PO file has current
        translations for.
        """

    def translated():
        """
        Return an iterator over translated message sets in this PO file.
        """

    def untranslatedCount():
        """
        Return the number of messages which this PO file has no translation
        for.
        """

    def untranslated():
        """
        Return an iterator over untranslated message sets in this PO file.
        """

    def __iter__():
        """Return an iterator over Current `IPOMessageSets` in this PO file."""

    def getHeader():
        """Return an `ITranslationHeaderData` representing its header."""

    def getCurrentTranslationMessage(msgid_text, context=None,
                                     ignore_obsolete=False):
        """Return the `ITranslationMessage` in this `IPOFile` by msgid_text.

        :param msgid_text: is an unicode string.
        :param context: Disambiguating context for the message set.
        :param ignore_obsolete: Whether we should ignore obsolete entries.
        :return: The `ITranslationMessage` for `msgid_text` or None.
        """

    def getCurrentTranslationMessageFromPOTMsgSet(potmsgset,
                                                  ignore_obsolete=False):
        """Return mapping between potmsgset and `ITranslationMessage`.

        :param potmsgset: An `IPOTMsgSet`.
        :param ignore_obsolete: Whether we should ignore obsolete messages
            when looking for the current translation message.
        :return: The translation message for this translation file and the
            given potmsgset or None.
        """

    def __getitem__(msgid_text):
        """Return the current `ITranslationMessage` by msgid_text.

        :param msgid_text: is an unicode string.

        Raise NotFoundError if it does not exist.
        """

    def getPOTMsgSetTranslated():
        """Get pot messages that are translated for this translation file."""

    def getPOTMsgSetFuzzy():
        """Get pot message sets with a translation that must be checked."""

    def getPOTMsgSetUntranslated():
        """Get pot message sets that are untranslated for this file."""

    def getPOTMsgSetWithNewSuggestions():
        """Get pot message sets with suggestions submitted after last review.
        """

    def getPOTMsgSetChangedInLaunchpad():
        """Get pot message sets changed through Launchpad in this PO file.

        'Changed in Launchpad' are only those which were translated when
        initially imported, but then got overridden in Launchpad.
        """

    def getPOTMsgSetWithErrors():
        """Get message sets that have translations imported with errors."""

    def updateExportCache(contents):
        """Update this PO file's export cache with a string."""

    def export():
        """Export this PO file as a string."""

    def uncachedExport(ignore_obsolete=False, export_utf8=False):
        """Export this PO file as string without using any cache.

        :param ignore_obsolete: Whether the exported PO file does not have
            obsolete entries.
        :param export_utf8: Whether the exported PO file should be exported as
            UTF-8.
        """

    def invalidateCache():
        """Invalidate the cached export."""

    def prepareTranslationCredits(potmsgset):
        """Add Launchpad contributors to translation credit strings.

        It adds to the translation for `potmsgset` if it exists, trying
        not to repeat same people who are already credited.
        """

    def canEditTranslations(person):
        """Whether the given person is able to add/edit translations."""

    def canAddSuggestions(person):
        """Whether the given person is able to add new suggestions."""

    def getStatistics():
        """Summarize this file's cached translation statistics.

        Returns tuple of (currentcount, updatescount, rosettacount,
        unreviewed_count).
        """

    def updateStatistics():
        """Update the statistics fields - rosettaCount, updatesCount and
        currentCount - from the messages currently known.
        Return a tuple (rosettaCount, updatesCount, currentCount)."""

    def updateHeader(new_header):
        """Update the header information.

        new_header is a POHeader object.
        """

    def isTranslationRevisionDateOlder(header):
        """Whether given header revision date is newer then self one."""

    def importFromQueue(entry_to_import, logger=None):
        """Import given queue entry.

        :param entry_to_import: `TranslationImportQueueEntry` specifying an
            approved import for this `POFile`
        :param logger: optional logger to report problems to.

        :return: a tuple of the subject line and body for a notification email
            to be sent to the uploader.
        """

    def getCurrentSuggestions(potmsgsets):
        """Return a dictionary with all suggestions per potmsgset.

        :param potmsgsets: A list of `IPOTMsgSet` objects.
        :param language: Language we are interested on for the suggestions.
        :return: A dictionary indexed by potmsgset of all suggestions that are
            done in other contexts and are used right now.
        """

    def getExternalSuggestions(potmsgsets):
        """Return a dictionary with all suggestions used per potmsgset.

        :param potmsgsets: A list of `IPOTMsgSet` objects.
        :param language: Language we are interested on for the suggestions.
        :return: A dictionary indexed by potmsgset of all suggestions that are
            done in other contexts but are not yet used.
        """


class AlternativeLanguageVocabularyFactory:
    """Gets vocab for user's preferred languages, or all languages if not set.

    This is an `IContextSourceBinder` returning a `Vocabulary`.  It's meant to
    present a short but complete list of languages a user might want to
    translate to or get suggestions from.

    Guessing based on browser languages is probably not a good idea: that list
    may easily be incomplete, and its origin is not obvious.  From the user's
    point of view it would be Launchpad behaviour that cannot be changed by
    pushing buttons in Launchpad.  And even in cases where a guess based on
    browser settings is reasonable, it would mask the need for a useful
    Preferred Languages setting.  We can't encourage people to manage their
    languages shortlist in Launchpad through their global browser
    configuration.

    Instead, if no preferred-languages setting is available (e.g. because the
    visitor is not logged in), this will fall back to a vocabulary containing
    all known translatable languages.
    """
    # XXX: JeroenVermeulen 2007-09-03: It doesn't seem right to define this
    # class in an interface, but it's needed from inside another interface
    # definition.  A factory is definitely the right approach though, since
    # the two kinds of vocabulary are completely different in implementation
    # and class derivation.  Also of course, the distinction applies unchanged
    # throughout the vocabulary object's lifetime.  See interfaces.buglink.py
    # for an example of the same implementation pattern.
    implements(IContextSourceBinder)

    def __call__(self, context):
        """See `IContextSourceBinder`."""
        user = getUtility(ILaunchBag).user
        if user is not None and user.languages:
            terms = [
                SimpleTerm(language, language.code, language.displayname)
                for language in user.translatable_languages]
            if terms:
                return SimpleVocabulary(terms)
        return getVocabularyRegistry().get(None, "TranslatableLanguage")


class IPOFileAlternativeLanguage(Interface):
    """A PO File's alternative language."""

    alternative_language = Choice(
        title=u'Alternative language',
        description=(u'Language from where we could get alternative'
                     u' translations for this PO file.'),
        source=AlternativeLanguageVocabularyFactory(),
        required=False)


class IPOFileSet(Interface):
    """A set of POFiles."""

    def getPOFilesPendingImport():
        """Return a list of PO files that have data to be imported."""

    def getDummy(potemplate, language):
        """Return a dummy pofile for the given po template and language."""

    def getPOFileByPathAndOrigin(path, productseries=None,
        distroseries=None, sourcepackagename=None):
        """Return an `IPOFile` that is stored at 'path' in source code.

        We filter the `IPOFile` objects to check only the ones related to the
        given arguments 'productseries', 'distroseries' and
        'sourcepackagename'.

        Return None if there is not such IPOFile.
        """

    def getBatch(starting_id, batch_size):
        """Read up to batch_size `POFile`s, starting at given id.

        Returns a sequence of consecutive `POFile`s (ordered by id), starting
        the smallest id that is no greater than starting_id.

        The number of items in the sequence will only be less than batch_size
        if the end of the table has been reached.
        """

class IPOFileTranslator(Interface):
    """Represents contributions from people to POFiles."""

    person = Object(
        title=_('The Person this record represents'), required=True,
        schema=IPerson)

    pofile = Object(
        title=_('The `IPOFile` modified by the translator'), required=True,
        schema=IPOFile)

    latest_message = Attribute(
        _("Latest translation message added to the translation file."))

    date_last_touched = Datetime(
        title=_('When was added latest translation message'), required=True)
