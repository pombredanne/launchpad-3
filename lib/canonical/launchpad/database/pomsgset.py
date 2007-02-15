# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POMsgSet', 'DummyPOMsgSet']

import gettextpo

from zope.interface import implements
from sqlobject import (ForeignKey, IntCol, StringCol, BoolCol,
                       SQLMultipleJoin, SQLObjectNotFound)

from canonical.cachedproperty import cachedproperty
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (SQLBase, sqlvalues,
                                        flush_database_updates)
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import IPOMsgSet, TranslationConflict
from canonical.launchpad.database.posubmission import POSubmission
from canonical.launchpad.database.potranslation import POTranslation
from canonical.lp.dbschema import (RosettaTranslationOrigin,
    TranslationValidationStatus)


class POMsgSetMixIn:
    """This class is not designed to be used directly.

    You should inherite from it and implement full IPOMsgSet interface to use
    the methods and properties defined here.
    """

    @property
    def pluralforms(self):
        """See IPOMsgSet."""
        if self.potmsgset.getPOMsgIDs().count() > 1:
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

    def getWikiSubmissions(self, pluralform):
        """See IPOMsgSet."""
        filter_pomsgset_sql = ''
        if self.id is not None:
            # Filter out submissions coming from this POMsgSet.
            filter_pomsgset_sql = 'AND POMsgSet.id <> %s' % sqlvalues(self)

        replacements = sqlvalues(
            language=self.pofile.language, pluralform=pluralform,
            primemsgid=self.potmsgset.primemsgid_ID)
        replacements['filter_pomsgset'] = filter_pomsgset_sql
        query = """
            SELECT DISTINCT POSubmission.id
            FROM POSubmission
                JOIN POMsgSet ON (POSubmission.pomsgset = POMsgSet.id AND
                                  POMsgSet.isfuzzy = FALSE
                                  %(filter_pomsgset)s)
                JOIN POFile ON (POMsgSet.pofile = POFile.id AND
                                POFile.language = %(language)s)
                JOIN POTMsgSet ON (POMsgSet.potmsgset = POTMsgSet.id AND
                                   POTMsgSet.primemsgid = %(primemsgid)s)
            WHERE
                POSubmission.pluralform = %(pluralform)s
            """ % replacements

        posubmission_ids_list = POMsgSet._connection.queryAll(query)
        posubmission_ids = [id for [id] in posubmission_ids_list]

        active_submission = self.getActiveSubmission(pluralform)

        if (active_submission is not None):
            # We look for all the IPOSubmissions with the same translation.
            same_translation = POSubmission.select(
                "POSubmission.potranslation = %s" %
                    sqlvalues(active_submission.potranslation.id))

            # Remove it so we don't show as suggestion something that we
            # already have as active.
            for posubmission in same_translation:
                if posubmission.id in posubmission_ids:
                    posubmission_ids.remove(posubmission.id)

        if len(posubmission_ids) > 0:
            ids = [str(id) for id in posubmission_ids]
            return POSubmission.select(
                'POSubmission.id IN (%s)' % ', '.join(ids),
                orderBy='-datecreated')
        else:
            # Return an empty SelectResults object.
            return POSubmission.select("1 = 2")


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

    @property
    def active_texts(self):
        """See IPOMsgSet."""
        return [None] * self.pluralforms

    def getActiveSubmission(self, pluralform):
        """See IPOMsgSet."""
        return None

    def getPublishedSubmission(self, pluralform):
        """See IPOMsgSet."""
        return None

    def getSuggestedSubmissions(self, pluralform):
        """See IPOMsgSet."""
        # Return an empty SelectResults object.
        return POSubmission.select("1 = 2")

    def getCurrentSubmissions(self, pluralform):
        """See IPOMsgSet."""
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

    submissions = SQLMultipleJoin('POSubmission', joinColumn='pomsgset')

    @property
    def published_texts(self):
        pluralforms = self.pluralforms
        if pluralforms is None:
            raise RuntimeError(
                "Don't know the number of plural forms for this PO file!")
        results = list(POSubmission.select(
            "POSubmission.published AND "
            "POSubmission.pomsgset = %s" % sqlvalues(self),
            orderBy='pluralform'))
        translations = []
        for form in range(pluralforms):
            if results and results[0].pluralform == form:
                translations.append(results.pop(0).potranslation.translation)
            else:
                translations.append(None)
        return translations

    @property
    def active_texts(self):
        pluralforms = self.pluralforms
        if pluralforms is None:
            raise RuntimeError(
                "Don't know the number of plural forms for this PO file!")
        results = list(POSubmission.select(
            """POSubmission.active AND
               POSubmission.pomsgset = %s""" % sqlvalues(self),
            orderBy='pluralform'))
        translations = []
        for form in range(pluralforms):
            if results and results[0].pluralform == form:
                translations.append(results.pop(0).potranslation.translation)
            else:
                translations.append(None)
        return translations

    def isNewerThan(self, timestamp):
        """See IPOMsgSet."""
        if (self.date_reviewed is not None and
            self.date_reviewed > timestamp):
            return True
        else:
            return False

    def setActiveSubmission(self, pluralform, submission):
        """See IPOMsgSet."""
        if submission is not None and submission.active:
            return

        current_active = self.getActiveSubmission(pluralform)
        if current_active is not None:
            current_active.active = False
            # We need this syncUpdate so if the next submission.active change
            # is done we are sure that we will store this change first in the
            # database. This is because we can only have an IPOSubmission with
            # the active flag set to TRUE.
            current_active.syncUpdate()

        if submission is not None:
            submission.active = True

    def setPublishedSubmission(self, pluralform, submission):
        """See IPOMsgSet."""
        if submission is not None and submission.published:
            return

        current_published = self.getPublishedSubmission(pluralform)
        if current_published is not None:
            current_published.published = False
            # We need this syncUpdate so if the next submission.published change
            # is done we are sure that we will store this change first in the
            # database. This is because we can only have an IPOSubmission with
            # the published flag set to TRUE.
            current_published.syncUpdate()

        if submission is not None:
            submission.published = True

    def getActiveSubmission(self, pluralform):
        """See IPOMsgSet."""
        return POSubmission.selectOne("""
            POSubmission.pomsgset = %s AND
            POSubmission.pluralform = %s AND
            POSubmission.active
            """ % sqlvalues(self, pluralform))

    def getPublishedSubmission(self, pluralform):
        """See IPOMsgSet."""
        return POSubmission.selectOne("""
            POSubmission.pomsgset = %s AND
            POSubmission.pluralform = %s AND
            POSubmission.published
            """ % sqlvalues(self, pluralform))

    def _updateReviewerInfo(self):
        """Update a couple of fields to note there was an update.

        The updated fields are:
            - self.pofile.last_touched_pomsgset: To cache which message was
              the last one updated so we can know when was an IPOFile last
               updated.
            - self.reviewer: To note who did last review for this message.
            - self.date_reviewed: To note when was done last review.
        """
            self.pofile.last_touched_pomsgset = self
            self.reviewer = person
            self.date_reviewed = UTC_NOW
            self.sync()

    def updateTranslationSet(self, person, new_translations, fuzzy, published,
        lock_timestamp, ignore_errors=False, force_edition_rights=False):
        """See IPOMsgSet."""
        # Is the person allowed to edit translations?
        is_editor = (force_edition_rights or
                     self.pofile.canEditTranslations(person))

        # First, check that the translations are correct.
        potmsgset = self.potmsgset
        msgids_text = [messageid.msgid
                       for messageid in potmsgset.getPOMsgIDs()]

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
            helpers.validate_translation(msgids_text, fixed_new_translations,
                                         potmsgset.flags())
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

        # keep track of whether or not this msgset is complete. We assume
        # it's complete and then flag it during the process if it is not
        complete = True
        has_changed = False
        new_translation_count = len(fixed_new_translations)
        if new_translation_count < self.pluralforms and not force_suggestion:
            # it's definitely not complete if it has too few translations
            complete = False
            # And we should reset the active or published submissions for the
            # non updated plural forms.
            for pluralform in range(self.pluralforms)[new_translation_count:]:
                if published:
                    self.setPublishedSubmission(pluralform, None)
                elif self.getActiveSubmission(pluralform) is not None:
                    # Note that this submission did a change.
                    self.setActiveSubmission(pluralform, None)
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

            old_active_submission = self.getActiveSubmission(index)

            new_submission = self._makeSubmission(
                person=person,
                text=newtran,
                pluralform=index,
                published=published,
                validation_status=validation_status,
                force_edition_rights=is_editor,
                force_suggestion=force_suggestion)

            if new_submission != old_active_submission:
                has_changed = True

        if has_changed and is_editor:
            self._updateReviewerInfo()

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
                # Now is time to check if the fuzzy flag should be copied to
                # the web flag
                matches = 0
                for pluralform in range(self.pluralforms):
                    if (self.getActiveSubmission(pluralform) ==
                        self.getPublishedSubmission(pluralform)):
                        matches += 1
                if matches == self.pluralforms:
                    # The active submission is exactly the same as the
                    # published one, so the fuzzy and complete flags should be
                    # also the same.
                    self.isfuzzy = self.publishedfuzzy
                    self.iscomplete = self.publishedcomplete
            else:
                self.isfuzzy = fuzzy
                self.iscomplete = complete

        # update the pomsgset flags
        self.updateFlags()

    def _makeSubmission(self, person, text, pluralform, published,
            validation_status=TranslationValidationStatus.UNKNOWN,
            force_edition_rights=False, force_suggestion=False):
        """Record a translation submission by the given person.

        If "published" then this is a submission noticed in the published po
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

        The "validation_status" field is a value of
        TranslationValidationStatus that indicates the status of the
        translation.

        The "force_edition_rights" is a flag that 'forces' that this submition
        is handled as coming from an editor, no matter if it's really an
        editor or not
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

        # Try to get the submission from the suggestions one.
        submission = POSubmission.selectOneBy(
            pomsgset=self, pluralform=pluralform, potranslation=translation)

        if submission is None:
            # We need to create the submission, it's the first time we see
            # this translation.
            submission = POSubmission(
                pomsgset=self, pluralform=pluralform, potranslation=translation,
                origin=origin, person=person,
                validationstatus=validation_status)

        potemplate = self.pofile.potemplate
        if (not published and not is_editor and
            submission.person.id == person.id and
            submission.origin == RosettaTranslationOrigin.ROSETTAWEB):
            # We only give karma for adding suggestions to people that send
            # non published strings and aren't editors. Editors will get their
            # subbmissions automatically approved, and thus, will get karma
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

            if not force_suggestion:
                # Now that we assigned all karma, is time to update the active
                # submission, the person that reviewed it and when it was done.
                self.setActiveSubmission(pluralform, submission)

        # return the submission we have just made
        return submission

    def updateFlags(self):
        """See IPOMsgSet."""
        # make sure we are working with the very latest data
        flush_database_updates()

        # we only want to calculate the number of plural forms expected for
        # this pomsgset once
        pluralforms = self.pluralforms

        # calculate the number of published plural forms
        published_count = POSubmission.select("""
            POSubmission.pomsgset = %s AND
            POSubmission.published AND
            POSubmission.pluralform < %s
            """ % sqlvalues(self, pluralforms)).count()

        self.publishedcomplete = (published_count == pluralforms)

        if published_count == 0:
            # If we don't have translations, this entry cannot be fuzzy.
            self.publishedfuzzy = False

        # calculate the number of active plural forms
        active_count = POSubmission.select("""
            POSubmission.pomsgset = %s AND
            POSubmission.active AND
            POSubmission.pluralform < %s
            """ % sqlvalues(self, pluralforms)).count()

        self.iscomplete = (active_count == pluralforms)

        if active_count == 0:
            # If we don't have translations, this entry cannot be fuzzy.
            self.isfuzzy = False

        flush_database_updates()

        # Let's see if we got updates from Rosetta
        updated_pomsgset = POMsgSet.select("""
            POMsgSet.id = %s AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.publishedfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            POMsgSet.publishedcomplete = TRUE AND
            published_submission.pomsgset = POMsgSet.id AND
            published_submission.pluralform < %s AND
            published_submission.published AND
            active_submission.pomsgset = POMsgSet.id AND
            active_submission.pluralform = published_submission.pluralform AND
            active_submission.active AND
            POMsgSet.date_reviewed > published_submission.datecreated
            """ % sqlvalues(self, pluralforms),
            clauseTables=['POSubmission AS active_submission',
                          'POSubmission AS published_submission']).count()

        self.isupdated = (updated_pomsgset > 0)

        flush_database_updates()

    def getSuggestedSubmissions(self, pluralform):
        """See IPOMsgSet."""
        query = '''pomsgset = %s AND
                   pluralform = %s''' % sqlvalues(self, pluralform)
        active_submission = self.getActiveSubmission(pluralform)
        if active_submission is not None:
            # Don't show suggestions older than the current one.
            query += ''' AND datecreated > %s
                    ''' % sqlvalues(active_submission.datecreated)
        return POSubmission.select(query, orderBy=['-datecreated'])

    def getCurrentSubmissions(self, pluralform):
        """See IPOMsgSet."""
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

