# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('IPOTMsgSet', 'IEditPOTMsgSet')

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

    def getWikiSubmissions(language, pluralform):
        """Return an iterator over all the submissions in any PO file for
        this pluralform in this language, for the same msgid."""

    def getCurrentSubmissions(language, pluralform):
        """Return an iterator over each of the submissions out there that
        are currently published or active in any PO file for the same
        language and prime msgid."""
        

    def flags():
        """Return a list of flags on this set."""

    def messageIDs():
        """Return an iterator over this set's message IDs.

        The maximum number of items this iterator returns is 2.
        """

    def getMessageIDSighting(pluralForm):
        """Return the message ID sighting that is current and has the
        plural form provided."""

    def translationsForLanguage(language):
        """Return an iterator over the active translation strings for this
        set in the given language.
        XXX very UI-specific, perhaps this should be elsewhere?
        """

    def poMsgSet(language, variant=None):
        """Retrieve the POMsgSet corresposponding to this POTMsgSet.

        The concrete POMsgSet is choosed by the language and variant
        arguments, being language a Language object and variant a string.
        If there is not POMsgSet for that language + variant convination, the
        NotFoundError exception is raised.
        """

class IEditPOTMsgSet(IPOTMsgSet):
    """Interface for editing a MessageSet."""

    def makeMessageIDSighting(text, pluralForm, update=False):
        """Return a new message ID sighting that points back to us.
        If one already exists, behaviour depends on 'update'; if update
        is allowed, the existing one is "touched" and returned.  If it
        is not, then a KeyError is raised."""

