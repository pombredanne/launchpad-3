# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.schema import Bool

__metaclass__ = type

__all__ = [
    'IPOMsgSet',
    'IPOMsgSetSubmissions',
]

class IPOMsgSet(Interface):

    sequence = Attribute("The ordering of this set within its file.")

    pofile = Attribute("The PO file this set is associated with.")

    publishedcomplete = Bool(
        title=(u'Whether the translation was complete or not in the PO file'
            u'which is published.'),
        description=(u'It is considered complete if all message IDs have a'
            u' translation, or the full set of translations in the case of'
            u' plural forms.'),
        required=True)

    iscomplete = Bool(
        title=u'Whether the translation is complete or not.',
        description=(u'It is considered complete if all message IDs have a'
            u' translation, or the full set of translations in the case of'
            u' plural forms.'),
        required=True)

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

    selections = Attribute(
        """All IPOSelection associated with this IPOMsgSet.""")
    submissions = Attribute(
        """All IPOSubmissions associated with this IPOMsgSet.""")

    def getSelection(pluralform):
        """Return the IPOSelection for this PO msgset or None.

        :arg pluralform: The plural form that we want to get the selection
            from.
        """

    def getActiveSubmission(pluralform):
        """Return the published translation submission for this po
        msgset and plural form or None.
        """

    def getPublishedSubmission(pluralform):
        """Return the published translation submission for this po
        msgset and plural form or None.
        """

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

    def updateTranslationSet(person, new_translations, fuzzy, published,
        ignore_errors=False, force_edition_rights=False):
        """Update a pomsgset using the set of translations provided.

        person is the author of the translations.
        new_translations is a dictionary of plural forms, with the integer
        plural form number as the key and the translation as the value.
        fuzzy is a flag that tells us if the translations are fuzzy or not.
        published indicates whether this update is coming from a published po
        file.
        ignore_errors is a flag that controlls if the translations should be
        stored even when an error is detected.
        force_edition_rights is a flag that 'forces' that this submition
        is handled as coming from an editor, no matter if it's really an
        editor or not

        If there is an error with the translations and ignore_errors is not
        True or it's not a fuzzy submit, raises gettextpo.error
        """

    def updateFlags():
        """Update the complete and fuzzy flags for this IPOMsgSet.

        The new values will reflect current status of this entry.
        """


class IPOMsgSetSubmissions(Interface):
    """XXX"""
    title = Attribute("XXX")
    submissions = Attribute("XXX")

