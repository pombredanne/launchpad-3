# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.interface import Interface, Attribute
from zope.schema import Field, Int
from canonical.launchpad import _

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

    # The primary message ID is the same as the message ID with plural
    # form 0 -- i.e. it's redundant. However, it acts as a cached value.

    context = Attribute(
        "String used to disambiguate messages with identical msgids.")

    primemsgid_ID = Int(title=u'Key of primary msgid for this set.',
        required=True, readonly=True)

    sequence = Attribute("The ordering of this set within its file.")

    potemplate = Attribute("The template this set is associated with.")

    commenttext = Attribute("The manual comments this set has.")

    filereferences = Attribute("The files where this set appears.")

    sourcecomment = Attribute("The source code comments this set has.")

    flagscomment = Attribute("The flags this set has.")

    msgid = Field(
        title=_("The singular id for this message."), readonly=True)

    msgid_plural = Field(
        title=_("The plural id for this message or None."), readonly=True)

    singular_text = Field(
        title=_("The singular text for this message."), readonly=True)

    plural_text = Field(
        title=_("The plural text for this message or None."), readonly=True)

    def getCurrentSubmissions(language, pluralform):
        """Return a selectresults for the submissions that are currently
        published or active in any PO file for the same language and
        prime msgid.
        """

    def flags():
        """Return a list of flags on this set."""

    def translationsForLanguage(language):
        """Return an iterator over the active translation strings for this
        set in the given language.
        XXX very UI-specific, perhaps this should be elsewhere?
        """

    def getPOMsgSet(language, variant=None):
        """Return the IPOMsgSet corresponding to this IPOTMsgSet or None.

        :param language: The language associated with the IPOMsgSet that we
            want.
        :param variant: The language variant.
        """

    def getDummyPOMsgSet(language, variant=None):
        """Return a Dummy IPOMsgSet corresponding to this IPOTMsgSet.

        :param language: The language associated with the IPOMsgSet that we
            want.
        :param variant: The language variant.

        We should not have already a POMsgSet for the given arguments.
        """

    def makeMessageIDSighting(text, pluralForm, update=False):
        """Return a new message ID sighting that points back to us.

        If one already exists, behaviour depends on 'update'; if update
        is allowed, the existing one is 'touched' and returned.  If it
        is not, then a KeyError is raised.
        """

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
