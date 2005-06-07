# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('IPOMsgSet', 'IEditPOMsgSet')

class IPOMsgSet(Interface):
    sequence = Attribute("The ordering of this set within its file.")

    pofile = Attribute("The PO file this set is associated with.")

    publishedcomplete = Attribute("""Whether the translation was complete or
        not. in the PO file which is published. It is considered complete
        if all message IDs have a translation, or the full set of
        translations in the case of plural forms.""")

    iscomplete = Attribute("""Whether the translation is complete or not in
        the Rosetta db. It is considered complete if all message IDs
        have a translation, or the full set of translations in the case
        of plural forms.""")

    publishedfuzzy = Attribute("""Whether this set was marked as fuzzy in
        the PO file it came from.""")

    isfuzzy = Attribute("""Whether this set was marked as fuzzy in the PO file 
        it came from.""")

    isupdated = Attribute("""Whether or not this set includes any
        translations that are newer than those published in the po
        file.""")

    obsolete = Attribute("""Whether this set was marked as obsolete in the 
        PO file it came from.""")

    commenttext = Attribute("Text of translator comment from the PO file.")

    potmsgset = Attribute("The msgid set that is translating this set.")

    active_texts = Attribute(
        """Return an iterator over this set's active translation texts.
        Each text is for a different plural form, in order.""")

    published_texts = Attribute(
        """Return an iterator over this set's published translation
        texts. Each text string (or None) is for a different plural form,
        in order.""")

    pluralforms = Attribute(
        """The number of translations that have to point to this message set
        for it to be complete, in the case of a translation that includes
        plurals. This depends on the language and in some cases even the
        specific text being translated per po-file.""")

    def selection(pluralform):
        "Returns the POSelection for this po msgset and "
        "plural form or None if there is no selection."

    def activeSubmission(pluralform):
        "Returns the published translation submission for this po msgset and "
        "plural form or None if there is no currently active submission."

    def publishedSubmission(pluralform):
        "Returns the published translation submission for this po msgset and "
        "plural form or None if there is no currently published submission."

    def getSuggestedTexts(pluralform):
        """Return an iterator over any suggestions Rosetta might have for
        this plural form on the messageset. The suggestions would not
        include the current active and published texts, because those can be
        represented and accessed differently through this API."""

    def getWikiSubmissions(pluralform):
        """Return an iterator over all the submissions in any PO file for
        this pluralform in this language, for the same msgid."""

    def getSuggestedSubmissions(pluralfom):
        """Return an iterator over any submissions that have come in for
        this pomsgset and pluralform that were sent in since the last active
        one was submitted."""

    def getCurrentSubmissions(pluralform):
        """Return an iterator over each of the submissions out there that
        are currently published or active in any PO file for the same
        language and prime msgid.
        
        So, for example, this will include submissions that are current
        upstream, or in other distributions."""


class IEditPOMsgSet(IPOMsgSet):
    """Interface for editing a POMsgSet."""

    def updateTranslationSet(person, new_translations, fuzzy, published,
        is_editor):
        """Update a pomsgset using the set of translations provided in
        new_translations. The "published" field indicates whether this
        update is coming from a published po file. "new_translations" is a
        dictionary of plural forms, with the integer plural form number as
        the key and the translation as the value. The "is_editor" flag
        indicates whether or not the person making the submission has
        permission to edit this pofile. If not, their submissions will be
        recorded but not activated."""

    def makeSubmission(person, text, pluralform, published, is_editor):
        """Record a translation submission by the given person. If
        "published" then this is a submission noticed in the published po
        file, otherwise it is a rosetta submission. It is assumed that any
        new submission will become the active translation (branding?), and
        if published is true then it will also become the published
        submission.
        
        This is THE KEY method in the whole of rosetta. It deals with the
        sighting or submission of a translation for a pomsgset and plural
        form, either online or in the published po file. It has to decide
        exactly what to do with that submission or sighting: whether to
        record it or ignore it, whether to make it the active or published
        translation, etc.

        It takes all the key information in the sighting/submission and
        records that in the db. It returns either the record of the
        submission, a POSubmission, or None if it decided to record
        nothing at all. Note that it may return a submission that was
        created previously, if it decides that there is not enough new
        information in this submission to justify recording it.

        The "published" field indicates whether or not this has come from
        the published po file. It should NOT be set for an arbitrary po
        file upload, it should ONLY be set if this is genuinely the
        published po file.

        The "is_editor" field indicates whether or not this person is
        allowed to edit the active translation in Rosetta. If not, we will
        still create a submission if needed, but we won't make it active.
        """
