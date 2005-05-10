# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('IPOMsgSet', 'IEditPOMsgSet')

class IPOMsgSet(Interface):
    sequence = Attribute("The ordering of this set within its file.")

    pofile = Attribute("The PO file this set is associated with.")

    iscomplete = Attribute("""Whether the translation is complete or not. 
        (I.e. all message IDs have a translation.""")

    obsolete = Attribute("""Whether this set was marked as obsolete in the 
        PO file it came from.""")

    fuzzy = Attribute("""Whether this set was marked as fuzzy in the PO file 
        it came from.""")

    commenttext = Attribute("Text of translator comment from the PO file.")

    potmsgset = Attribute("The msgid set that is translating this set.")

    def pluralforms():
        """Number of translations that have to point to this message set
        for it to be complete."""

    def translations():
        """Return an iterator over this set's translations."""

    def getTranslationSighting(pluralForm, allowOld=False):
        """Return the translation sighting that is current and has the
        plural form provided.  If allowOld is True, include non-current."""

    def translationSightings():
        """Return an iterator over current translation sightings."""


class IEditPOMsgSet(IPOMsgSet):
    """Interface for editing a POMsgSet."""

    fuzzy = Attribute("""Whether this set was marked as fuzzy in the PO file 
        it came from.""")

    def updateTranslation(person, new_translations, fuzzy, fromPOFile=False):
        """foo"""

    def makeTranslationSighting(person, text, pluralForm, update=False,
                                fromPOFile=False):
        """Return a new translation sighting that points back to us.

        If one already exists, behaviour depends on 'update'; if update
        is allowed, the existing one is "touched" and returned.  If it
        is not, then a KeyError is raised.
        fromPOFile should be true when the sighting is coming from a POFile
        in the upstream source - so that the inLatestRevision field is
        set accordingly.
        """

