# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

from lazr.enum import (
    EnumeratedType,
    Item,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Int,
    List,
    Object,
    Text,
    )

from canonical.launchpad import _
from lp.translations.interfaces.pomsgid import IPOMsgID


__metaclass__ = type

__all__ = [
    'IPOTMsgSet',
    'BrokenTextError',
    'POTMsgSetInIncompatibleTemplatesError',
    'TranslationCreditsType',
    ]


class TranslationCreditsType(EnumeratedType):
    """Identify a POTMsgSet as translation credits."""

    NOT_CREDITS = Item("""
        Not a translation credits message

        This is a standard msgid and not translation credits.
        """)

    GNOME = Item("""
        Gnome credits message

        How they do them in Gnome.
        """)

    KDE_EMAILS = Item("""
        KDE emails credits message

        How they do them in KDE for translator emails.
        """)

    KDE_NAMES = Item("""
        KDE names credits message

        How they do them in KDE for translator names.
        """)


class BrokenTextError(ValueError):
    """Exception raised when we detect values on a text that aren't valid."""


class POTMsgSetInIncompatibleTemplatesError(Exception):
    """Raised when a POTMsgSet appears in multiple incompatible templates.

    Two PO templates are incompatible if one uses English strings for msgids,
    and another doesn't (i.e. it uses English translation instead).
    """


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

    commenttext = Attribute("The manual comments this set has.")

    filereferences = Attribute("The files where this set appears.")

    sourcecomment = Attribute("The source code comments this set has.")

    flagscomment = Attribute("The flags this set has.")

    flags = Attribute("List of flags that apply to this message.")

    singular_text = Text(
        title=_("The singular text for this message."), readonly=True)

    plural_text = Text(
        title=_("The plural text for this message or None."), readonly=True)

    uses_english_msgids = Bool(
        title=_("Uses English strings as msgids"), readonly=True,
        description=_("""
            Some formats, such as Mozilla's XPI, use symbolic msgids where
            gettext uses the original English strings to identify messages.
            """))

    credits_message_ids = List(
        title=_("List of possible msgids for translation credits"),
        readonly=True,
        description=_("""
            This class attribute is intended to be used to construct database
            queries that search for credits messages.
            """))

    def getCurrentTranslationMessageOrDummy(pofile):
        """Return the current `TranslationMessage`, or a dummy.

        :param pofile: PO template you want a translation message for.
        :return: The current translation for `self` in `pofile`, if
            there is one.  Otherwise, a `DummyTranslationMessage` for
            `self` in `pofile`.
        """

    def getCurrentTranslationMessage(potemplate, language):
        """Returns a TranslationMessage marked as being currently used.

        Diverged messages are preferred.
        """

    def getImportedTranslationMessage(potemplate, language):
        """Returns a TranslationMessage as imported from the package.

        Diverged messages are preferred.
        """

    def getSharedTranslationMessage(language):
        """Returns a shared TranslationMessage."""

    def getLocalTranslationMessages(potemplate, language,
                                    include_dismissed=False,
                                    include_unreviewed=True):
        """Return all local unused translation messages for the POTMsgSet.

        Unused are those which are not current or imported, and local are
        those which are directly attached to this POTMsgSet.

        :param language: language we want translations for.
        :param include_dismissed: Also return those translation messages
          that have a creation date older than the review date of the current
          message (== have been dismissed).
        :param include_unreviewed: Also return those translation messages
          that have a creation date newer than the review date of the current
          message (== that are unreviewed). This is the default.
        """

    def getExternallyUsedTranslationMessages(language):
        """Find externally used translations for the same message.

        This is used to find suggestions for translating this
        `POTMsgSet` that are actually used (i.e. current or imported) in
        other templates.

        The suggestions are read-only; they come from the slave store.

        :param language: language we want translations for.
        """

    def getExternallySuggestedTranslationMessages(language):
        """Find externally suggested translations for the same message.

        This is used to find suggestions for translating this
        `POTMsgSet` that were entered in another context, but for the
        same English text, and are not in actual use.

        The suggestions are read-only; they come from the slave store.

        :param language: language we want translations for.
        """

    def hasTranslationChangedInLaunchpad(potemplate, language):
        """Whether an imported translation differs from the current one.

        :param potemplate: potemplate we are asking about.
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

    def updateTranslation(pofile, submitter, new_translations, is_imported,
                          lock_timestamp, force_suggestion=False,
                          ignore_errors=False, force_edition_rights=False,
                          allow_credits=False):
        """Update or create a translation message using `new_translations`.

        :param pofile: a `POFile` to add `new_translations` to.
        :param submitter: author of the translations.
        :param new_translations: a dictionary of plural forms, with the
            integer plural form number as the key and the translation as the
            value.
        :param is_imported: indicates whether this update is imported from a
            packaged po file.
        :param lock_timestamp: The timestamp when we checked the values we
            want to update.
        :param force_suggestion: Whether to force translation to be
            a suggestion, even if submitted by an editor.
        :param ignore_errors: A flag that controls whether the translations
            should be stored even when an error is detected.
        :param force_edition_rights: A flag that 'forces' handling this
            submission as coming from an editor, even if `submitter` is not.
        :param allow_credits: Override the protection of translation credits
            message.

        If there is an error with the translations and ignore_errors is not
        True or it's not a fuzzy submit, raises gettextpo.error

        :return: a modified or newly created translation message; or None if
            no message is to be updated.  This can happen when updating a
            translation credits message without the is_imported parameter set.
        """

    def dismissAllSuggestions(pofile, reviewer, lock_timestamp):
        """Dismiss all suggestions for the given pofile.

        :param pofile: a `POFile` to dismiss suggestions from.
        :param reviewer: the person that is doing the dismissal.
        :param lock_timestamp: the timestamp when we checked the values we
            want to update.

        If a translation conflict is detected, TranslationConflict is raised.
        """

    def resetCurrentTranslation(pofile, lock_timestamp):
        """Reset the currently used translation.

        This will set the "is_current" attribute to False and if the message
        is diverge, will try to converge it.
        :param pofile: a `POFile` to dismiss suggestions from.
        :param lock_timestamp: the timestamp when we checked the values we
            want to update.

        If a translation conflict is detected, TranslationConflict is raised.
        """

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
        """Return 'unicode_text' with the same trailing and leading
        whitespaces that self.singular_text has.

        If 'unicode_text' has only whitespaces but self.singular_text has
        other characters, the empty string (u'') is returned to note it as an
        untranslated string.
        """

    def normalizeNewLines(unicode_text):
        """Return 'unicode_text' with new lines chars in sync with the msgid.
        """


    hide_translations_from_anonymous = Attribute(
        """Whether the translations for this message should be hidden.

        Messages that are likely to contain email addresses
        are shown only to logged-in users, and not to anonymous users.
        """)

    is_translation_credit = Attribute(
        """Whether this is a message set for crediting translators.""")

    translation_credits_type = Choice(
        title=u"The type of translation credit of this message.",
        required=True,
        vocabulary = TranslationCreditsType)

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

    def getSequence(potemplate):
        """Return the sequence number for this potmsgset in potemplate.

        :param potemplate: `IPOTemplate` where the sequence number applies.
        """

    def setSequence(potemplate, sequence):
        """Set the sequence number for this potmsgset in potemplate.

        :param potemplate: `IPOTemplate` where the sequence number applies.
        :param sequence: The sequence number of this `IPOTMsgSet` in the given
            `IPOTemplate`.
        """

    def setTranslationCreditsToTranslated(pofile):
        """Set the current translation for this translation credits message.

        Sets a fixed dummy string as the current translation, if this is a
        translation credits message, so that these get counted as
        'translated', too.
        Credits messages that already have a translation, imported messages
        and normal messages are left untouched.
        :param pofile: the POFile to set this translation in.
        """

    def getAllTranslationMessages():
        """Retrieve all `TranslationMessage`s for this `POTMsgSet`."""

    def getAllTranslationTemplateItems():
        """Retrieve all `TranslationTemplateItem`s for this `POTMsgSet`."""
