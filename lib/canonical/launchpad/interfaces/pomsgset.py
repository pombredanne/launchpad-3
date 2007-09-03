# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.schema import Bool, Object, Datetime
from canonical.launchpad.interfaces.person import IPerson

__metaclass__ = type

__all__ = [
    'IPOMsgSet',
    'IPOMsgSetSuggestions',
    'TranslationConflict',
]


class TranslationConflict(Exception):
    """Someone updated the translation we are trying to update."""


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

    reviewer = Object(
        title=u'The person who did the review and accepted current active'
              u'translations.',
        required=False, schema=IPerson)

    date_reviewed = Datetime(
        title=u'The date when this message was reviewed for last time.',
        required=False)

    submissions = Attribute(
        """All IPOSubmissions associated with this IPOMsgSet.""")

    latest_change_date = Attribute(
        """Return the date of the latest change in the `IPOMsgSet`.""")

    latest_change_person = Attribute(
        """Return the person who did the latest change in the `IPOMsgSet`.""")

    language = Attribute(
        "The language this msgset is in, copied from `POFile`.")

    def isNewerThan(timestamp):
        """Whether the active translations are newer than the given timestamp.

        :param timestamp: A DateTime object with a timestamp.

        """

    def initializeSubmissionsCaches(related_submissions=None):
        """Initialize internal submission caches.

        These caches are used to find submissions attached to self, as well as
        specifically active or published submissions, or suggestions, and so
        on, without querying the database unnecessarily.

        The getter and setter methods for the Active Submissions and Published
        Submissions work on a subset of this cache; the active/published
        submissions caches can be populated separately to avoid the cost of
        fetching the full data set for the submissions cache.  When doing work
        on a POMsgSet that will require finding both the active/published
        submissions information and other information about submissions or
        suggestions, call initializeSubmissionsCaches first.  That will
        populate the full submissions caches without duplication of the effort
        to fetch the active/published submissions information.

        Note that the actual caches are private to this object, which is
        visible only in a single thread.  This is why no locking is needed.

        :param related_submissions: list or iterator of all submissions
            attached to this object, as well as all that should be presented
            as suggestions for its translation.  If related_submissions is not
            given, they will be fetched from the database.  Must yield
            `POSubmissions` in newest-to-oldest order.
        """

    def setActiveSubmission(pluralform, submission):
        """Set given submission as the active one.

        If submission is None, no submissions will be active.
        """

    def getActiveSubmission(pluralform):
        """Return the published translation submission for this po
        msgset and plural form or None.
        """

    def setPublishedSubmission(pluralform, submission):
        """Set given submission as the published one.

        If submission is None, no submissions will be published.
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
        """List of suggestions for given pluralform.

        A suggestion is a POSubmission for another POMsgSet in the same
        language, whose potmsgset shares the same primemsgid as self's, but
        which offers a translation that's not already selected for self.  In
        less formal terms, a suggestion is an existing translation that is
        likely to be a useful translation for self.
        """

    def getNewSubmissions(pluralfom):
        """Submissions for self that are more recent than active one, if any.

        Returns a list of POSubmissions, ordered from newest to oldest.
        """

    def getCurrentSubmissions(pluralform):
        """Return a list of submissions currently published or active.

        It will come from any PO file for the same language and prime msgid
        in our whole database.

        So, for example, this will include submissions that are current
        upstream, or in other distributions.
        """

    def updateTranslationSet(person, new_translations, fuzzy, published,
        lock_timestamp, ignore_errors=False, force_edition_rights=False):
        """Update a pomsgset using the set of translations provided.

        :arg person: is the author of the translations.
        :arg new_translations: is a dictionary of plural forms, with the
            integer plural form number as the key and the translation as the
            value.
        :arg fuzzy: A flag that tells us whether the translations are fuzzy.
        :arg published: indicates whether this update is coming from a
            published po file.
        :arg lock_timestamp: The timestamp when we checked the values we want
            to update.
        :arg ignore_errors: A flag that controlls whether the translations
            should be stored even when an error is detected.
        :arg force_edition_rights: A flag that 'forces' that this submition
            is handled as coming from an editor, no matter whether is really
            an editor.

        If there is an error with the translations and ignore_errors is not
        True or it's not a fuzzy submit, raises gettextpo.error
        """

    def updateFlags():
        """Update `iscomplete`, `isfuzzy`, and `isupdated` flags.

        The new values will reflect current status of this entry.
        """

    def updateReviewerInfo(reviewer):
        """Update a couple of fields to note there was an update.

        :param reviewer: The person who just reviewed this IPOMsgSet.

        The updated fields are:
            - `self.pofile.last_touched_pomsgset`: To cache which message was
              the last one updated so we can know when was an IPOFile last
               updated.
            - `self.reviewer`: To note who did last review for this message.
            - `self.date_reviewed`: To note when was done last review.
        """

    def makeHTMLId(suffix=None):
        """Unique name for this `POMsgSet` for use in HTML element ids.

        The name is an underscore-separated sequence of:
         * the string 'msgset'
         * unpadded, numerical `POTMsgSet.id` (not our own `id`!)
         * language code
         * caller-supplied suffix.

        :param suffix: an identifier to be appended.  Must be suitable for use
        in HTML element ids.
        """


class IPOMsgSetSuggestions(Interface):
    """Suggested `POSubmission`s for a `POMsgSet` in a particular plural form.

    When displaying `POMsgSet`s in `POMsgSetView` we display different types
    of suggestions: non-reviewer translations, translations that occur in
    other contexts, and translations in alternate languages. See
    `POMsgSetView._buildSuggestions` for details.
    """
    title = Attribute("The name displayed next to the suggestion, "
                      "indicating where it came from.")
    submissions = Attribute("An iterable of POSubmission objects")
    user_is_official_translator = Bool(
        title=(u'Whether the user is an official translator.'),
        required=True)
