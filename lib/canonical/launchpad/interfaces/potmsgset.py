# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.interface import Interface, Attribute
from zope.schema import Int, Object, Text

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

    id = Int(
        title=_("The identifier of this POTMsgSet."),
        readonly=True, required=True)

    context = Text(
        title=u"String used to disambiguate messages with identical msgids.")

    msgid_singular = Object(
        title=_("The singular msgid for this message."),
        description=_("""
            A message ID along with the context uniquely identifies the
            template message.
            """), readonly=True, required=True, schema=IPOMsgID)

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

    def getCurrentDummyTranslationMessage(language):
        """Return a DummyTranslationMessage for this message language.

        :param language: language we want a dummy translations for.

        We must not have already a TranslationMessage for this language.
        """

    def getCurrentTranslationMessage(language):
        """Returns a TranslationMessage marked as being currently used."""

    def getImportedTranslationMessage(language):
        """Returns a TranslationMessage as imported from the package."""

    def getLocalTranslationMessages(language):
        """Returns all the local unused translation messages for the POTMsgSet.
        Unused are those which are not current or imported, and local are
        those which are directly attached to this POTMsgSet.

        :param language: language we want translations for.
        """

    def getExternallyUsedTranslationMessages(pofile):
        """Returns all the local unused translation messages for the POTMsgSet.
        Unused are those which are not current or imported, and local are
        those which are directly attached to this POTMsgSet.

        :param language: language we want translations for.
        """

    def getExternallySuggestedTranslationMessages(pofile):
        """Returns all the local unused translation messages for the POTMsgSet.
        Unused are those which are not current or imported, and local are
        those which are directly attached to this POTMsgSet.

        :param language: language we want translations for.
        """

    def hasTranslationChangedInLaunchpad(language):
        """Whether an imported translation differs from the current one.

        :param language: language for which translations we are asking about.

        There has to be an imported translation: if there isn't, this is
        not a 'changed' translation, just a 'new' translation in Launchpad.
        """

    def isTranslationNewerThan(pofile, timestamp):
        """Whether a current translation is newer than the `timestamp`.

        :param pofile: translation file for which translations we are asking
            about.
        :param timestamp: a timestamp we are comparing to.

        Returns True if there is a current and newer translation, and False
        otherwise.
        """

    def updateTranslation(pofile, submitter, new_translations, is_fuzzy,
                          is_imported, lock_timestamp, ignore_errors=False,
                          force_edition_rights=False):
        """Update or create a translation message using `new_translations`.

        :param pofile: a `POFile` to add `new_translations` to.
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

        Returns a modified or newly created translation message.
        """

    def flags():
        """Return a list of flags on this set."""

    def applySanityFixes(unicode_text):
        """Return 'unicode_text' or None after doing some sanitization.

        The text is checked against the msgid using the following filters:

          self.convertDotToSpace
          self.normalizeWhitespaces
          self.normalizeNewLines

        If the resulting string after these operations is an empty string,
        it returns None.

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

    def makeHTMLID(suffix=None):
        """Unique name for this `POTMsgSet` for use in HTML element ids.

        The name is an underscore-separated sequence of:
         * the string 'msgset'
         * unpadded, numerical `id`
         * optional caller-supplied suffix.

        :param suffix: an optional suffix to be appended.  Must be suitable
            for use in HTML element ids.
        """

    def updatePluralForm(plural_form_text):
        """Update plural form text for this message.

        :param plural_form_text: Unicode string representing the plural form
            we want to store or None to unset current plural form.
        """
