# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POMsgSet', 'DummyPOMsgSet']

import gettextpo

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy
from sqlobject import (ForeignKey, IntCol, StringCol, BoolCol,
                       SQLMultipleJoin, SQLObjectNotFound)

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    flush_database_updates, quote, SQLBase, sqlvalues)
from canonical.launchpad import helpers
from canonical.launchpad.database.posubmission import POSubmission
from canonical.launchpad.database.potranslation import POTranslation
from canonical.launchpad.interfaces import (
    IPOMsgSet, TranslationConflict, IPOSubmissionSet,
    TranslationValidationStatus)
from canonical.lp.dbschema import RosettaTranslationOrigin


class POMsgSetMixIn:
    """This class is not designed to be used directly.

    You should inherite from it and implement full IPOMsgSet interface to use
    the methods and properties defined here.
    """

    # Cached submissions dict, mapping pluralform to list of POSubmissions,
    # ordered from new to old.
    attached_submissions = None

    # Cached active submissions dict, mapping pluralform to POSubmission.
    active_submissions = None
    # Cached published submissions dict, mapping pluralform to POSubmission.
    published_submissions = None

    @property
    def pluralforms(self):
        """See `IPOMsgSet`."""
        if self.potmsgset.plural_text is not None:
            if self.pofile.language.pluralforms is not None:
                entries = self.pofile.language.pluralforms
            else:
                # Don't know anything about plural forms for this
                # language, fallback to the most common case, 2
                entries = 2
        else:
            # It's a singular form
            entries = 1
        return entries

    def _getRelatedSubmissions(self):
        """Fetch all POSubmissions for self's submissions caches.

        This retrieves all POSubmissions that form useful suggestions for self
        from the database, as well as any POSubmissions that are already
        attached to self, all in new-to-old order of datecreated."""
        dummy_pomsgset = []
        stored_pomsgset = []
        if self.id is None:
            dummy_pomsgset = [self]
        else:
            stored_pomsgset = [self]

        subs = getUtility(IPOSubmissionSet).getSubmissionsFor(
            stored_pomsgset, dummy_pomsgset)

        assert len(subs) == 1, (
            "Received suggestions for unexpected POMsgSet.")
        return subs[self]

    def initializeSubmissionsCaches(self, related_submissions=None):
        """See `IPOMsgSet`."""
        if self._hasSubmissionsCaches():
            return

        self.active_submissions = {}
        self.published_submissions = {}
        self.suggestions = {}
        self.attached_submissions = {}

        # Retrieve all related POSubmissions, and use them to populate our
        # submissions caches.
        if related_submissions is None:
            related_submissions = self._getRelatedSubmissions()

        related_submissions = [
            removeSecurityProxy(submission)
            for submission in related_submissions]

        previous = None
        for submission in related_submissions:
            assert previous is None or submission.datecreated <= previous, (
                "POMsgSet's incoming submission cache data not ordered "
                "from newest to oldest")
            pluralform = submission.pluralform
            # Compare foreign-key value to our primary key, rather than
            # comparing objects, to avoid fetching submission.pomsgset from
            # database.
            if submission.pomsgsetID == self.id:
                self.attached_submissions.setdefault(pluralform, [])
                self.attached_submissions[pluralform].append(submission)
                if submission.active:
                    self.active_submissions[pluralform] = submission
                if submission.published:
                    self.published_submissions[pluralform] = submission
            else:
                self.suggestions.setdefault(pluralform, [])
                self.suggestions[pluralform].append(submission)
            previous = submission.datecreated

        # Now that we know what our active posubmissions are, filter out any
        # suggestions that refer to the same potranslations.
        for pluralform in self.suggestions.keys():
            active = self.getActiveSubmission(pluralform)
            if active is not None and active.potranslation is not None:
                active_translation = active.potranslationID
                self.suggestions[pluralform] = [
                    submission
                    for submission in self.suggestions.get(pluralform)
                    if submission.potranslationID != active.potranslationID]

        assert self._hasSubmissionsCaches(), (
            "Failed to set up POMsgSet's submission caches")

    def _invalidateSubmissionsCaches(self):
        """Drop our submissions caches."""
        self.active_submissions = None
        self.published_submissions = None
        self.suggestions = None
        self.attached_submissions = None
        assert not self._hasSubmissionsCaches(), (
            "Failed to initialize POMsgSet's submission caches")

    def _hasSubmissionsCaches(self):
        """Are this POMsgSet's submissions caches initialized?"""
        return self.attached_submissions is not None

    def getWikiSubmissions(self, pluralform):
        """See `IPOMsgSet`."""
        self.initializeSubmissionsCaches()
        suggestions = self.suggestions.get(pluralform)
        if suggestions is None:
            return []
        return suggestions

    def makeHTMLId(self, suffix=None):
        """See `IPOMsgSet`."""
        elements = [self.pofile.language.code]
        if suffix is not None:
            elements.append(suffix)
        return self.potmsgset.makeHTMLId('_'.join(elements))


class DummyPOMsgSet(POMsgSetMixIn):
    """Represents a POMsgSet where we do not yet actually HAVE a POMsgSet for
    that POFile and POTMsgSet.
    """
    implements(IPOMsgSet)

    def __init__(self, pofile, potmsgset):
        self.id = None
        self.pofile = pofile
        self.potmsgset = potmsgset
        self.isfuzzy = False
        self.commenttext = None
        self.language = pofile.language

    @property
    def active_texts(self):
        """See `IPOMsgSet`."""
        return [None] * self.pluralforms

    @property
    def published_texts(self):
        """See IPOMsgSet."""
        return [None] * self.pluralforms

    def getActiveSubmission(self, pluralform):
        """See `IPOMsgSet`."""
        return None

    def getPublishedSubmission(self, pluralform):
        """See `IPOMsgSet`."""
        return None

    def getNewSubmissions(self, pluralform):
        """See `IPOMsgSet`."""
        return []

    def getCurrentSubmissions(self, pluralform):
        """See `IPOMsgSet`."""
        return []


class POMsgSet(SQLBase, POMsgSetMixIn):
    implements(IPOMsgSet)

    _table = 'POMsgSet'

    sequence = IntCol(dbName='sequence', notNull=True)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile', notNull=True)
    iscomplete = BoolCol(dbName='iscomplete', notNull=True, default=False)
    publishedcomplete = BoolCol(dbName='publishedcomplete', notNull=True,
        default=False)
    isfuzzy = BoolCol(dbName='isfuzzy', notNull=True, default=False)
    publishedfuzzy = BoolCol(dbName='publishedfuzzy', notNull=True,
        default=False)
    isupdated = BoolCol(notNull=True, default=False)
    commenttext = StringCol(dbName='commenttext', notNull=False, default=None)
    potmsgset = ForeignKey(foreignKey='POTMsgSet', dbName='potmsgset',
        notNull=True)
    obsolete = BoolCol(dbName='obsolete', notNull=True)
    reviewer = ForeignKey(
        foreignKey='Person', dbName='reviewer', notNull=False, default=None)
    date_reviewed = UtcDateTimeCol(dbName='date_reviewed', notNull=False,
        default=None)
    language = ForeignKey(foreignKey='Language', dbName='language')

    submissions = SQLMultipleJoin('POSubmission', joinColumn='pomsgset')

    def _extractTranslations(self, from_dict):
        """Extract translations from pluralform-to-POSubmission dict.

        Helper for published_texts and active_texts.  Returns a list of one
        translation string per pluralform, or None for pluralforms that are
        not represented in from_dict.  Any translations with unexpected
        pluralform numbers are ignored.
        """
        pluralforms = self.pluralforms
        if pluralforms is None:
            raise RuntimeError(
                "Don't know the number of plural forms for this PO file!")

        result = [None] * pluralforms
        for pluralform, submission in from_dict.items():
            if pluralform < pluralforms:
                result[pluralform] = submission.potranslation.translation

        return result

    @property
    def published_texts(self):
        """See `IPOMsgSet`."""
        if self.published_submissions is None:
            self._fetchActiveAndPublishedSubmissions()
        return self._extractTranslations(self.published_submissions)

    @property
    def active_texts(self):
        """See `IPOMsgSet`."""
        if self.active_submissions is None:
            self._fetchActiveAndPublishedSubmissions()
        return self._extractTranslations(self.active_submissions)

    def isNewerThan(self, timestamp):
        """See `IPOMsgSet`."""
        date_updated = self.date_reviewed
        for pluralform in range(self.pluralforms):
            submission = self.getActiveSubmission(pluralform)
            if submission is not None and (
                not date_updated or submission.datecreated > date_updated):
                date_updated = submission.datecreated

        if (date_updated is not None and date_updated > timestamp):
            return True
        else:
            return False

    def getLatestChangeInfo(self):
        """Return a tuple of person, date for latest change to `IPOMsgSet`."""
        if self.reviewer and self.date_reviewed:
            return (self.reviewer, self.date_reviewed)

        last_submission = None
        for pluralform in range(self.pluralforms):
            submission = self.getActiveSubmission(pluralform)
            if (last_submission is None or
                submission.datecreated > last_submission.datecreated):
                last_submission = submission
        if last_submission:
            return (last_submission.person, last_submission.datecreated)
        else:
            return (None, None)

    @property
    def latest_change_date(self):
        """See `IPOMsgSet`."""
        person, date = self.getLatestChangeInfo()
        return date

    @property
    def latest_change_person(self):
        """See `IPOMsgSet`."""
        person, date = self.getLatestChangeInfo()
        return person

    def setActiveSubmission(self, pluralform, submission):
        """See `IPOMsgSet`."""

        assert submission is None or submission.pomsgset == self, (
            'Submission made "active" in the wrong POMsgSet')

        if submission is not None and submission.active:
            return

        current_active = self.getActiveSubmission(pluralform)
        if current_active is not None:
            current_active.active = False
            del self.active_submissions[pluralform]
            # We need this syncUpdate so if the next submission.active change
            # is done we are sure that we will store this change first in the
            # database. This is because we can only have an IPOSubmission with
            # the active flag set to TRUE.
            current_active.syncUpdate()

        if submission is not None:
            submission.active = True

            # Update cache.
            self.active_submissions[pluralform] = submission

    def setPublishedSubmission(self, pluralform, submission):
        """See `IPOMsgSet`."""

        assert submission is None or submission.pomsgset == self, (
            "Submission set as published in wrong POMsgSet")

        if submission is not None and submission.published:
            return

        current_published = self.getPublishedSubmission(pluralform)
        if current_published is not None:
            current_published.published = False
            del(self.published_submissions[pluralform])
            # We need this syncUpdate so if the next submission.published change
            # is done we are sure that we will store this change first in the
            # database. This is because we can only have an IPOSubmission with
            # the published flag set to TRUE.
            current_published.syncUpdate()

        if submission is not None:
            submission.published = True

            # Update cache.
            self.published_submissions[pluralform] = submission

    def _fetchActiveAndPublishedSubmissions(self):
        """Populate active/published submissions caches from database.

        Creates self.active_submissions and self.published_submissions as
        dicts, each mapping pluralform to that pluralform's active or
        published submission, respectively.

        This cache is a subset of the submissions cache; populating that will
        also populate this one.  So another way of achieving the same thing
        (and more) is to initialize the POMsgSet's caches, but that is a much
        bigger job with lots of other byproducts that may not turn out to be
        needed.
        """
        active = {}
        published = {}

        query = "pomsgset = %s AND (active OR published)" % quote(self)
        for submission in POSubmission.select(query):
            pluralform = submission.pluralform
            if submission.active:
                assert not pluralform in active, (
                    "Multiple active submissions for pluralform %d"
                    % pluralform)
                active[pluralform] = submission
            if submission.published:
                assert not pluralform in published, (
                    "Multiple published submissions for pluralform %d"
                    % pluralform)
                published[pluralform] = submission
        self.active_submissions = active
        self.published_submissions = published

    def getActiveSubmission(self, pluralform):
        """See `IPOMsgSet`."""
        if self.active_submissions is None:
            if self.id is None:
                return None
            self._fetchActiveAndPublishedSubmissions()
        return self.active_submissions.get(pluralform)

    def getPublishedSubmission(self, pluralform):
        """See `IPOMsgSet`."""
        if self.published_submissions is None:
            if self.id is None:
                return None
            self._fetchActiveAndPublishedSubmissions()
        return self.published_submissions.get(pluralform)

    def updateReviewerInfo(self, reviewer):
        """See `IPOMsgSet`."""
        self.pofile.last_touched_pomsgset = self
        self.reviewer = reviewer
        self.date_reviewed = UTC_NOW
        self.sync()

    def updateTranslationSet(self, person, new_translations, fuzzy, published,
        lock_timestamp, ignore_errors=False, force_edition_rights=False):
        """See `IPOMsgSet`."""
        # Is the person allowed to edit translations?
        is_editor = (force_edition_rights or
                     self.pofile.canEditTranslations(person))

        assert (published or is_editor or
                self.pofile.canAddSuggestions(person)), (
            '%s cannot add translations nor can add suggestions' % (
                person.displayname))

        # First, check that the translations are correct.
        potmsgset = self.potmsgset
        original_texts = [potmsgset.singular_text]
        if potmsgset.plural_text is not None:
            original_texts.append(potmsgset.plural_text)

        # If the update is on the translation credits message, yet
        # update is not published, silently return
        # XXX 2007-06-26 Danilo: Do we want to raise an exception here?
        if potmsgset.is_translation_credit and not published:
            return

        # By default all translations are correct.
        validation_status = TranslationValidationStatus.OK

        # And we allow changes to translations by default, we don't force
        # submissions as suggestions.
        force_suggestion = False

        # Fix the trailing and leading whitespaces
        fixed_new_translations = {}
        for index, value in new_translations.items():
            fixed_new_translations[index] = potmsgset.applySanityFixes(value)

        # Validate the translation we got from the translation form
        # to know if gettext is unhappy with the input.
        try:
            helpers.validate_translation(
                original_texts, fixed_new_translations, potmsgset.flags())
        except gettextpo.error:
            if fuzzy or ignore_errors:
                # The translations are stored anyway, but we set them as
                # broken.
                validation_status = TranslationValidationStatus.UNKNOWNERROR
            else:
                # Check to know if there is any translation.
                has_translations = False
                for key in fixed_new_translations.keys():
                    if fixed_new_translations[key] != '':
                        has_translations = True
                        break

                if has_translations:
                    # Partial translations cannot be stored unless the fuzzy
                    # flag is set, the exception is raised again and handled
                    # outside this method.
                    raise

        if not published and not fuzzy and self.isNewerThan(lock_timestamp):
            # Latest active submission in self is newer than 'lock_timestamp'
            # and we try to change it.
            force_suggestion = True

        # Cache existing active submissions since we use them a lot
        active_submissions = []
        for pluralform in range(self.pluralforms):
            active_submissions.append(self.getActiveSubmission(pluralform))

        # keep track of whether or not this msgset is complete. We assume
        # it's complete and then flag it during the process if it is not
        complete = True
        has_changed = False
        new_translation_count = len(fixed_new_translations)
        if new_translation_count < self.pluralforms and not force_suggestion:
            # it's definitely not complete if it has too few translations
            complete = False
            # And we should reset the active or published submissions for the
            # non updated plural forms. We have entries to reset when:
            #     1. The number of plural forms is changed in current
            #     language since the user loaded the translation form or
            #     downloaded the .po file that he imported.
            #     2. An imported .po file comming from upstream or package
            #     translations has less plural forms than the ones defined in
            #     Rosetta for that language.
            for pluralform in range(self.pluralforms)[new_translation_count:]:
                if published:
                    self.setPublishedSubmission(pluralform, None)
                elif active_submissions[pluralform] is not None:
                    # Note that this submission did a change.
                    self.setActiveSubmission(pluralform, None)
                    while pluralform >= len(active_submissions):
                        active_submissions.append(None)
                    has_changed = True

        # now loop through the translations and submit them one by one
        for index in fixed_new_translations.keys():
            newtran = fixed_new_translations[index]
            # replace any '' with None until we figure out
            # ResettingTranslations
            if newtran == '':
                newtran = None
            # see if this affects completeness
            if newtran is None:
                complete = False
            # make the new sighting or submission. note that this may not in
            # fact create a whole new submission
            if index < len(active_submissions):
                old_active_submission = active_submissions[index]
            else:
                old_active_submission = None

            new_submission = self._makeSubmission(
                person=person,
                text=newtran,
                is_fuzzy=fuzzy,
                pluralform=index,
                published=published,
                validation_status=validation_status,
                force_edition_rights=is_editor,
                force_suggestion=force_suggestion,
                active_submission=old_active_submission)

            if (new_submission != old_active_submission and
                new_submission and new_submission.active):
                has_changed = True
                while index >= len(active_submissions):
                    active_submissions.append(None)
                active_submissions[index] = new_submission

        if has_changed and is_editor:
            if published:
                # When update for a submission is published, nobody has
                # actually reviewed the new submission in Launchpad, so
                # we don't set the reviewer and date_reviewed
                self.pofile.last_touched_pomsgset = self
            else:
                self.updateReviewerInfo(person)

        if force_suggestion:
            # We already stored the suggestions, so we don't have anything
            # else to do. Raise a TranslationConflict exception to notify
            # that the changes were saved as suggestions only.
            raise TranslationConflict(
                'The new translations were saved as suggestions to avoid '
                'possible conflicts. Please review them.')

        # We set the fuzzy flag first, and completeness flags as needed:
        if is_editor:
            if published:
                self.publishedfuzzy = fuzzy
                self.publishedcomplete = complete
                if has_changed or self.isfuzzy:
                    # If the upstream translation has changed or we don't have
                    # a valid translation in Launchpad, then we need to update
                    # the status flags because we can get some improved
                    # information from upstream.
                    matches = 0
                    updated = 0
                    for pluralform in range(self.pluralforms):
                        active = active_submissions[pluralform]
                        published = self.getPublishedSubmission(pluralform)
                        if active:
                            if published and active != published:
                                updated += 1
                            else:
                                matches += 1
                    if matches == self.pluralforms and self.publishedcomplete:
                        # The active submission is exactly the same as the
                        # published one, so the fuzzy and complete flags
                        # should be also the same.
                        self.isfuzzy = self.publishedfuzzy
                        self.iscomplete = self.publishedcomplete
                    if updated > 0:
                        # There are some active translations different from
                        # published ones, so the message has been updated
                        self.isupdated = True
                active_count = 0
                for pluralform in range(self.pluralforms):
                    if active_submissions[pluralform]:
                        active_count += 1
                self.iscomplete = (active_count == self.pluralforms)
            else:
                self.isfuzzy = fuzzy
                self.iscomplete = complete
                updated = 0
                for pluralform in range(self.pluralforms):
                    active = active_submissions[pluralform]
                    published = self.getPublishedSubmission(pluralform)
                    if active and published and active != published:
                        updated += 1
                if updated > 0:
                    self.isupdated = True

    def _makeSubmission(self, person, text, is_fuzzy, pluralform, published,
            validation_status=TranslationValidationStatus.UNKNOWN,
            force_edition_rights=False, force_suggestion=False,
            active_submission=None):
        """Record a translation submission by the given person.

        :arg person: Who submitted this entry.
        :arg text: The translation submitted or None if there is no
            translation.
        :arg is_fuzzy: Whether this translation has the fuzzy flag set.
        :arg pluralform: The plural form number that this translation is for.
        :arg published: Whether this is a submission noticed in the published
            po file, otherwise it is a launchpad submission. It should NOT be
            set for an arbitrary po file upload, it should ONLY be set if this
            is genuinely the published po file.
        :arg validation_status: A value of TranslationValidationStatus that
            indicates the status of the translation.
        :arg force_edition_rights: A flag that 'forces' that this submition is
            handled as coming from an editor, no matter whether it's really
            from an editor.
        :arg force_suggestion: Whether this translation must not change the
            active translation in Launchpad and just be added as a suggestion.

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
        """
        # Is the person allowed to edit translations?
        is_editor = (force_edition_rights or
                     self.pofile.canEditTranslations(person))

        # It makes no sense to have a "published" submission from someone
        # who is not an editor, so let's sanity check that first
        if published and not is_editor:
            raise AssertionError(
                'published translations are ALWAYS from an editor')

        # first we must deal with the situation where someone has submitted
        # a NULL translation. This only affects the published or active data
        # set, there is no crossover. So, for example, if upstream loses a
        # translation, we do not remove it from the rosetta active set.

        # we should also be certain that we don't get an empty string. that
        # should be None by this stage
        assert text != u'', 'Empty string received, should be None'

        # We'll be needing our full submissions cache for this.
        self.initializeSubmissionsCaches()

        active_submission = self.getActiveSubmission(pluralform)
        published_submission = self.getPublishedSubmission(pluralform)

        # submitting an empty (None) translation gets rid of the published
        # or active submissions for that translation. But a null published
        # translation does not remove the active submission.
        if text is None:
            # Remove the existing active/published submissions
            if published:
                self.setPublishedSubmission(pluralform, None)
            elif (is_editor and
                  validation_status == TranslationValidationStatus.OK and
                  not force_suggestion):
                self.setActiveSubmission(pluralform, None)

            # we return because there is nothing further to do.
            return None

        # Find or create a POTranslation for the specified text
        try:
            translation = POTranslation.byTranslation(text)
        except SQLObjectNotFound:
            translation = POTranslation(translation=text)

        # find or create the relevant submission. We always create a
        # translation submission, unless this translation is already active
        # (or published in the case of one coming in from a po file).

        # start by trying to see if the existing one is active or if
        # needed, published. If so, we can return, because the db already
        # reflects this selection in all the right ways and does not need to
        # be updated. Note that this will result in a submission for a new
        # person ("Joe") returning a POSubmission created in the name of
        # someone else, the person who first made this translation the
        # active / published one.

        # test if we are working with the published pofile, and if this
        # translation is already published
        if (published and
            published_submission is not None and
            published_submission.potranslation == translation):
            # Sets the validation status to the current status.
            # We do it always so the changes in our validation code will
            # apply automatically.
            published_submission.validationstatus = validation_status

            # return the existing submission that made this translation
            # the published one in the db
            return published_submission

        if (not published and
            active_submission is not None and
            active_submission.potranslation == translation):
            # Sets the validation status to the current status.
            # If our validation code has been improved since the last
            # import we might detect new errors in previously validated
            # strings, so we always do this, regardless of the status in
            # the database.
            active_submission.validationstatus = validation_status
            # and return the active submission
            return active_submission

        # let's make a record of whether this translation was published
        # complete, was actively complete, and was an updated one

        # get the right origin for this translation submission
        if published:
            origin = RosettaTranslationOrigin.SCM
        else:
            origin = RosettaTranslationOrigin.ROSETTAWEB

        # Try to find the submission belonging to translation back in our
        # submissions cache.  There should be at most one match.
        submission = None
        if self.attached_submissions.get(pluralform) is not None:
            for candidate in self.attached_submissions[pluralform]:
                if candidate.potranslation == translation:
                    assert submission is None, (
                        "Duplicate translations in POMsgSet")
                    submission = candidate

        if submission is None:
            # We need to create the submission, it's the first time we see
            # this translation.
            submission = POSubmission(
                pomsgset=self, pluralform=pluralform,
                potranslation=translation, origin=origin, person=person,
                validationstatus=validation_status)
            # Add the new submission to our cache.
            self.attached_submissions.setdefault(pluralform, [])
            self.attached_submissions[pluralform].insert(0, submission)

        potemplate = self.pofile.potemplate
        if (not published and not is_editor and
            submission.person.id == person.id and
            submission.origin == RosettaTranslationOrigin.ROSETTAWEB):
            # We only give karma for adding suggestions to people that send
            # non published strings and aren't editors. Editors will get their
            # submissions automatically approved, and thus, will get karma
            # just when they get their submission autoapproved.
            # The Rosetta Experts team never gets karma.
            person.assignKarma(
                'translationsuggestionadded',
                product=potemplate.product,
                distribution=potemplate.distribution,
                sourcepackagename=potemplate.sourcepackagename)

        # next, we need to update the existing active and possibly also
        # published submissions.
        if published:
            self.setPublishedSubmission(pluralform, submission)

        if is_editor and validation_status == TranslationValidationStatus.OK:
            # activesubmission is updated only if the translation is valid and
            # it's an editor.
            if (not published and
                (active_submission is None or
                 active_submission.id != submission.id)):
                # The active submission changed and is not published, that
                # means that the submission came from Rosetta UI instead of
                # upstream imports and we should give Karma.
                if submission.origin == RosettaTranslationOrigin.ROSETTAWEB:
                    # The submitted translation came from our UI, we should
                    # give karma to the submitter of that translation.
                    submission.person.assignKarma(
                        'translationsuggestionapproved',
                        product=potemplate.product,
                        distribution=potemplate.distribution,
                        sourcepackagename=potemplate.sourcepackagename)

                if person.id != submission.person.id:
                    # The submitter is different from the owner of the
                    # selected translation, that means that a reviewer
                    # approved a translation from someone else, he should get
                    # Karma for that action.
                    person.assignKarma(
                        'translationreview',
                        product=potemplate.product,
                        distribution=potemplate.distribution,
                        sourcepackagename=potemplate.sourcepackagename)

            if published:
                if (self.isfuzzy or active_submission is None or
                    (not is_fuzzy and
                     published_submission == active_submission and
                     self.isfuzzy == self.publishedfuzzy)):
                    # Either we lack or don't use the active translation in
                    # Launchpad, or the new published translation we got could
                    # be used as a valid one, and previous active translation
                    # in Launchpad matches with previous published translation.
                    self.setActiveSubmission(pluralform, submission)
            elif not force_suggestion:
                # It's not a published submission and we are not forcing the
                # submission to be a suggestion, so we should apply the active
                # submission change.
                self.setActiveSubmission(pluralform, submission)
            else:
                # We are forcing the submission as as a suggestion, and thus,
                # the active submission is not changed.
                pass

        # We need this syncUpdate so we don't set self.isfuzzy to the wrong
        # value because cache problems. See bug #102382 as an example of what
        # happened without having this flag + broken code. Our tests were not
        # able to find the problem.
        submission.syncUpdate()

        # return the submission we have just made
        return submission

    def updateFlags(self):
        """See `IPOMsgSet`."""

        # Make sure we are working with the very latest data.
        flush_database_updates()
        self.initializeSubmissionsCaches()

        # Avoid re-evaluation of self.pluralforms.
        pluralforms = self.pluralforms

        # Calculate the number of published plural forms.
        # Since every POFile may have its own plural expression, it's possible
        # for submissions to have plural-form numbers that the language itself
        # does not define.  That's fine, and people have used it for some edge
        # cases, but they must not count towards the msgset's completeness.
        published_count = 0
        for (plural, published) in self.published_submissions.items():
            if plural < pluralforms and published.id is not None:
                published_count += 1

        self.publishedcomplete = (published_count == pluralforms)

        if published_count == 0:
            # If we don't have translations, this entry cannot be fuzzy.
            self.publishedfuzzy = False

        # Calculate the number of active plural forms.
        active_count = 0
        for (plural, active) in self.active_submissions.items():
            if plural < pluralforms and active.id is not None:
                active_count += 1

        self.iscomplete = (active_count == pluralforms)

        if active_count == 0:
            # If we don't have translations, this entry cannot be fuzzy.
            self.isfuzzy = False

        flush_database_updates()

        # Let's see if we got updates from Rosetta
        # XXX: JeroenVermeulen 2007-06-13: does this really work?
        updated_pomsgset = POMsgSet.select("""
            POMsgSet.id = %s AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.publishedfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            POMsgSet.publishedcomplete = TRUE AND
            published_submission.pomsgset = POMsgSet.id AND
            published_submission.pluralform < %s AND
            published_submission.published IS TRUE AND
            active_submission.pomsgset = POMsgSet.id AND
            active_submission.pluralform = published_submission.pluralform AND
            active_submission.active IS TRUE AND
            POMsgSet.date_reviewed > published_submission.datecreated
            """ % sqlvalues(self, pluralforms),
            clauseTables=['POSubmission AS active_submission',
                          'POSubmission AS published_submission']).count()

        self.isupdated = (updated_pomsgset > 0)

        flush_database_updates()

    def getNewSubmissions(self, pluralform):
        """See `IPOMsgSet`."""
        self.initializeSubmissionsCaches()

        applicable_submissions = self.attached_submissions.get(pluralform)
        if applicable_submissions is None:
            return []

        active = self.getActiveSubmission(pluralform)
        if active is None:
            return applicable_submissions

        # Return only submissions that are newer than the active one.
        active_date = active.datecreated
        return [
            submission
            for submission in applicable_submissions
            if submission.datecreated > active_date]

    def getCurrentSubmissions(self, pluralform):
        """See `IPOMsgSet`."""
        subs = self.potmsgset.getCurrentSubmissions(self.pofile.language,
                                                    pluralform)
        # While getCurrentSubmissions itself does prejoining and
        # optimizes the process considerably, we do one additional query
        # below; if this query becomes a performance problem we can
        # modify getCurrentSubmissions to include query text that
        # excludes the active submission.
        #   -- kiko, 2006-06-22
        active = self.getActiveSubmission(pluralform)
        sub_list = helpers.shortlist(subs)
        if active is not None and active in sub_list:
            sub_list.remove(active)
        return sub_list

