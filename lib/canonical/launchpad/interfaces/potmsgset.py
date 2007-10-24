# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Attribute, Interface
from zope.schema import Field, Int, Object, Text
from canonical.launchpad import _

from canonical.launchpad.interfaces.pomsgid import IPOMsgID

__metaclass__ = type

__all__ = [
    'IPOTMsgSet',
    'BrokenTextError',
    ]

class BrokenTextError(ValueError):
    """Exception raised when we detect values on a text that aren't valid."""

class IPOTMsgSet(Interface):
    """A collection of message IDs."""

    id = Attribute("""An identifier for this POTMsgSet""")
    context = Text(
        title=u"String used to disambiguate messages with identical msgids.")

    msgid_singular = Object(
        title=u"The singular msgid for this message.",
        description=(u"A message ID along with the context uniquely identifies "
                     u"the template message."),
        required=True,
        readonly=True,
        schema=IPOMsgID)

    msgid_plural = Object(
        title=u"The plural msgid for this message.",
        description=(u"Provides a plural msgid for the message. "
                     u"If it's not a plural form message, this value"
                     u"should be None."),
        required=True,
        readonly=True,
        schema=IPOMsgID)

    sequence = Attribute("The ordering of this set within its file.")

    potemplate = Attribute("The template this set is associated with.")

    commenttext = Attribute("The manual comments this set has.")

    filereferences = Attribute("The files where this set appears.")

    sourcecomment = Attribute("The source code comments this set has.")

    flagscomment = Attribute("The flags this set has.")

    singular_text = Text(
        title=_("The singular text for this message."), readonly=True)

    plural_text = Text(
        title=_("The plural text for this message or None."), readonly=True)

    def getTranslationMessages(language):
        """Return all the translation messages for this IPOTMsgSet.

        :param language: language we want translations for.
        """

    def getDummyTranslationMessages(language):
        """Return an iterator containing a single DummyTranslationMessage.

        :param language: language we want a dummy translations for.

        We should not already have a TranslationMessage for this language.
        """

    def getCurrentTranslation(language):
        """Returns a TranslationMessage marked as being currently used."""

    def getImportedTranslation(language):
        """Returns a TranslationMessage as imported from the package."""

    def getLocalTranslationMessages(language):
        """Return all the local unused translation messages for this IPOTMsgSet.

        :param language: language we want translations for.
        """

    def getExternalTranslationMessages(language):
        """Get TranslationMessages for the same msgid in different templates.
        """

    def hasTranslationChangedInLaunchpad(language):
        """Whether an imported translation differs from the current one.

        :param language: language for which translations we are asking about.

        There has to be an imported translation: if there isn't, this is
        not a 'changed' translation, just a 'new' translation in Launchpad."""

    def updateTranslationSet(language, submitter, new_translations, is_fuzzy,
                             is_imported, lock_timestamp, ignore_errors=False,
                             force_edition_rights=False):
        """Update or create a translation message using `new_translations`.

        :param language: language `new_translations` are in.
        :param submitter: author of the translations.
        :param new_translations: a dictionary of plural forms, with the
            integer plural form number as the key and the translation as the
            value.
        :param is_fuzzy: Whether the translations are fuzzy.
        :param is_imported: indicates whether this update is imported from a
            packaged po file.
        :param lock_timestamp: The timestamp when we checked the values we
            want to update.
        :param ignore_errors: A flag that controls whether the translations
            should be stored even when an error is detected.
        :param force_edition_rights: A flag that 'forces' handling this
            submission as coming from an editor, even if `submitter` is not.

        If there is an error with the translations and ignore_errors is not
        True or it's not a fuzzy submit, raises gettextpo.error
        """

    def flags():
        """Return a list of flags on this set."""

    def applySanityFixes(unicode_text):
        """Return 'unicode_text' after doing some sanity checks and fixes.

        The text is checked against the msgid using the following filters:

          self.convertDotToSpace
          self.normalizeWhitespaces
          self.normalizeNewLines

        :param unicode_text: A unicode text that needs to be checked.
        """

    def convertDotToSpace(unicode_text):
        """Return 'unicode_text' with the u'\u2022' char exchanged with a
        normal space.

        If the self.singular_text contains that character, 'unicode_text' is
        returned without changes as it's a valid char instead of our way to
        represent a normal space to the user.
        """

    def normalizeWhitespaces(unicode_text):
        """Return 'unicode_text' with the same trailing and leading whitespaces
        that self.singular_text has.

        If 'unicode_text' has only whitespaces but self.singular_text has other
        characters, the empty string (u'') is returned to note it as an
        untranslated string.
        """

    def normalizeNewLines(unicode_text):
        """Return 'unicode_text' with new lines chars in sync with the msgid."""


    hide_translations_from_anonymous = Attribute(
        """Whether the translations for this message should be hidden.

        Messages that are likely to contain email addresses
        are shown only to logged-in users, and not to anonymous users.
        """)

    is_translation_credit = Attribute(
        """Whether this is a message set for crediting translators.""")

    def makeHTMLId(suffix=None):
        """Unique name for this `POTMsgSet` for use in HTML element ids.

        The name is an underscore-separated sequence of:
         * the string 'msgset'
         * unpadded, numerical `id`
         * optional caller-supplied suffix.

        :param suffix: an optional suffix to be appended.  Must be suitable
            for use in HTML element ids.
        """
