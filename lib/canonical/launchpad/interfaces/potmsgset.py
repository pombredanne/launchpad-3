# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = [
    'IPOTMsgSet',
    ]

class IPOTMsgSet(Interface):
    """A collection of message IDs."""

    id = Attribute("""An identifier for this POTMsgSet""")

    # The primary message ID is the same as the message ID with plural
    # form 0 -- i.e. it's redundant. However, it acts as a cached value.

    primemsgid_ = Attribute("The primary msgid for this set.")

    sequence = Attribute("The ordering of this set within its file.")

    potemplate = Attribute("The template this set is associated with.")

    commenttext = Attribute("The manual comments this set has.")

    filereferences = Attribute("The files where this set appears.")

    sourcecomment = Attribute("The source code comments this set has.")

    flagscomment = Attribute("The flags this set has.")

    def getCurrentSubmissionsIDs(language, pluralform):
        """Return a list of IPOSubmission IDs that are currently published or
        active in any PO file for the same language and prime msgid.
        """

    def getCurrentSubmissions(language, pluralform):
        """Return an iterator over each of the submissions out there that are
        currently published or active in any PO file for the same language and
        prime msgid.
        """

    def flags():
        """Return a list of flags on this set."""

    def getPOMsgIDs():
        """Return an iterator over this set's IPOMsgID.

        The maximum number of items this iterator returns is 2.
        """

    def getPOMsgIDSighting(pluralForm):
        """Return the IPOMsgIDSighting that is current and has the plural
        form provided.
        """

    def translationsForLanguage(language):
        """Return an iterator over the active translation strings for this
        set in the given language.
        XXX very UI-specific, perhaps this should be elsewhere?
        """

    def getPOMsgSet(language, variant=None):
        """Return the IPOMsgSet corresponding to this IPOTMsgSet or None.

        :language: The language associated with the IPOMsgSet that we want.
        :variant: The language variant.
        """

    def makeMessageIDSighting(text, pluralForm, update=False):
        """Return a new message ID sighting that points back to us.

        If one already exists, behaviour depends on 'update'; if update
        is allowed, the existing one is 'touched' and returned.  If it
        is not, then a KeyError is raised.
        """

    def applySanityFixes(unicode_text):
        """Return 'unicode_text' after doing some sanity checks and fixes
        against the msgid improving its value in case the user made any mistake.

        :arg unicode_text: A unicode or string that needs to be checked.

        This method calls self.convertDotToSpace, self.normalizeWhitespaces
        and self.normalizeNewLines to do the fixes.
        """

    def convertDotToSpace(unicode_text):
        """Return 'unicode_text' with the u'\u2022' char exchanged with a
        normal space.

        If the self.primemsgid contains that character, 'unicode_text' is
        returned without changes as it's a valid char instead of our way to
        represent a normal space to the user.
        """

    def normalizeWhitespaces(unicode_text):
        """Return 'unicode_text' with the same trailing and leading whitespaces
        that self.primemsgid has.

        If 'unicode_text' has only whitespaces but self.primemsgid has other
        characters, the empty string (u'') is returned to note it as an
        untranslated string.
        """

    def normalizeNewLines(unicode_text):
        """Return 'unicode_text' with new lines chars in sync with the msgid."""
