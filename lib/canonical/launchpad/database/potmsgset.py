# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POTMsgSet']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey, IntCol, StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote, sqlvalues

from canonical.launchpad.interfaces import (
    BrokenTextError, ILanguageSet, IPOTMsgSet, ITranslationImporter,
    TranslationConstants)
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.pomsgset import POMsgSet, DummyPOMsgSet
from canonical.launchpad.database.pomsgidsighting import POMsgIDSighting
from canonical.launchpad.database.posubmission import POSubmission


class POTMsgSet(SQLBase):
    implements(IPOTMsgSet)

    _table = 'POTMsgSet'

    context = StringCol(dbName='context', notNull=False)
    msgid_singular = ForeignKey(foreignKey='POMsgID', dbName='msgid_singular',
        notNull=True)
    msgid_plural = ForeignKey(foreignKey='POMsgID', dbName='msgid_plural',
        notNull=True)
    sequence = IntCol(dbName='sequence', notNull=True)
    potemplate = ForeignKey(foreignKey='POTemplate', dbName='potemplate',
        notNull=True)
    commenttext = StringCol(dbName='commenttext', notNull=False)
    filereferences = StringCol(dbName='filereferences', notNull=False)
    sourcecomment = StringCol(dbName='sourcecomment', notNull=False)
    flagscomment = StringCol(dbName='flagscomment', notNull=False)

    @property
    def singular_text(self):
        """See `IPOTMsgSet`."""
        format_importer = getUtility(
            ITranslationImporter).getTranslationFormatImporter(
                self.potemplate.source_file_format)
        if format_importer.uses_source_string_msgids:
            # This format uses English translations as the way to store the
            # singular_text.
            english_language = getUtility(ILanguageSet)['en']
            translation_message = self.getCurrentTranslationMessage(
                english_language)
            if (translation_message is not None and
                translation_message.msgstr0 is not None):
                return translation_message.msgstr0.translation

        # By default, singular text is the msgid_singular.
        return self.msgid_singular.msgid

    @property
    def plural_text(self):
        """See `IPOTMsgSet`."""
        return self.msgid_plural.msgid

    def getCurrentTranslationMessage(self, language):
        """See `IPOTMsgSet`."""
        return TranslationMessage.selectOne("""
            potmsgset = %s AND is_current IS TRUE AND language = %s
            """ % sqlvalues(self, language))

    def getImportedTranslationMessage(self, language):
        """See `IPOTMsgSet`."""
        return TranslationMessage.selectOne("""
            potmsgset = %s AND is_imported IS TRUE AND language = %s
            """ % sqlvalues(self, language))

    def flags(self):
        if self.flagscomment is None:
            return []
        else:
            return [flag
                    for flag in self.flagscomment.replace(' ', '').split(',')
                    if flag != '']


    def getTranslationMessages(self, language):
        # XXX: do we really need this one?
        pass

    def getLocalTranslationMessages(self, language):
        """See `IPOTMsgSet`."""
        return TranslationMessage.select("""
            is_current IS NOT TRUE AND
            is_imported IS NOT TRUE AND
            potmsgset = %s AND
            language = %s""" % sqlvalues(self, language))

    def getExternalTranslationMessages(self, language):
        """See `IPOTMsgSet`."""
        pass

    def hasTranslationChangedInLaunchpad(self, language):
        """See `IPOTMsgSet`."""
        imported_translation = self.getImportedTranslationMessage(language)
        if (imported_translation is not None and
            not imported_translation.is_current):
            return True
        else:
            return False

    def _list_of_msgids(self):
        """Return a list of [singular_text, plural_text] if the message
        is using plural forms, or just [singular_text] if it's not.
        """
        original_texts = [self.singular_text]
        if self.plural_text is not None:
            original_texts.append(plural_text)
        return original_texts

    def _validate_translations(self, translations, fuzzy, ignore_errors):
        """Validate all the `translations` and return a pair of
        (validation_status, sanitized_translations).
        """
        # By default all translations are correct.
        validation_status = TranslationValidationStatus.OK

        # Fix the trailing and leading whitespaces
        sanitized_translations = {}
        for index, value in translations.items():
            sanitized_translations[index] = self.applySanityFixes(value)

        # Cache the list of singular_text and plural_text
        original_texts = self._list_of_msgids()

        # Validate the translation we got from the translation form
        # to know if gettext is unhappy with the input.
        try:
            helpers.validate_translation(
                original_texts, sanitized_translations, self.flags())
        except gettextpo.error:
            if fuzzy or ignore_errors:
                # The translations are stored anyway, but we set them as
                # broken.
                validation_status = TranslationValidationStatus.UNKNOWNERROR
            else:
                # Check to know if there is any translation.
                has_translations = False
                for key in sanitized_translations.keys():
                    if sanitized_translations[key] != '':
                        has_translations = True
                        break

                if has_translations:
                    # Partial translations cannot be stored unless the fuzzy
                    # flag is set, the exception is raised again and handled
                    # outside this method.
                    raise

        return (validation_status, sanitized_translations)

    def _message_same_as_translations(self, message, translations):
        """Compare a TranslationMessage `message` with a list of
        translation strings `translations`.

        If the number of translations is exactly the same, and they all
        match, return True, otherwise return False.
        """
        # TranslationMessage.translations is a list of all possible
        # plural form translations for this message, with None where
        # there are no translations
        for pluralform, text in enumerate(message.translations):
            # if both have this plural form and they match, or
            # if there is no plural form submitted and it's None in DB
            if not((pluralform < len(translations) and
                    text == translations[pluralform]) or
                   pluralform >= len(translations) and text is None):
                return False
        return True

    def _is_submission_empty(self, pofile, translations):
        """Return True if all `translations` are None.

        It only checks the valid pluralforms.
        """
        for pluralform in range(pofile.language.pluralforms):
            if (pluralform < len(translations) and
                translations[pluralform] is not None):
                return False
        return True

    def updateTranslation(self, pofile, person, new_translations, fuzzy,
                          is_imported, lock_timestamp, ignore_errors=False,
                          force_edition_rights=False):
        """See `IPOTMsgSet`."""
        # Is the person allowed to edit translations?
        is_editor = (force_edition_rights or
                     pofile.canEditTranslations(person))

        assert (is_imported or is_editor or pofile.canAddSuggestions(person)),
            ('%s cannot add translations nor can add suggestions' % (
                person.displayname))

        # It makes no sense to have a "is_imported" submission from someone
        # who is not an editor, so assert that
        if is_imported and not is_editor:
            raise AssertionError(
                'Only an editor can submit is_imported translations.')

        # Sanitize and check that the translations are correct.
        validation_status, sanitized_translations = (
            self._validate_translations(new_translations, fuzzy, ignore_errors))

        # If the update is on the translation credits message, yet
        # update is not is_imported, silently return
        # XXX 2007-06-26 Danilo: Do we want to raise an exception here?
        if potmsgset.is_translation_credit and not is_imported:
            return

        # And we allow changes to translations by default, we don't force
        # submissions as suggestions.
        force_suggestion = False

        if not is_imported and not fuzzy and pofile.isNewerThan(lock_timestamp):
            # Latest active submission in self is newer than 'lock_timestamp'
            # and we try to change it.
            force_suggestion = True

        # Get a currently used and imported translation message.
        current_translation = self.getCurrentTranslationMessage(pofile.language)
        imported_translation = self.getImportedTranslationMessage(
            pofile.language)

        is_same_as_current = self._message_same_as_translations(
            current_translation, sanitized_translations)
        if not force_suggestion:
            has_changed = is_same_as_current
        else:
            has_changed = False

        # Try to find existing matching suggestion
        if is_same_as_current:
            matching_message = current_translation
        elif self._message_same_as_translations(imported_translation,
                                                sanitized_translations):
            matching_message = imported_translation
        else:
            matching_message = TranslationMessage.selectOne(
                """
                """
        # Create a new TranslationMessage if needed
        
        if is_imported:
            origin = RosettaTranslationOrigin.SCM
        else:
            origin = RosettaTranslationOrigin.ROSETTAWEB
        

        # now loop through the translations and submit them one by one
        for index in sanitized_translations.keys():
            newtran = sanitized_translations[index]
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


    def applySanityFixes(self, text):
        """See `IPOTMsgSet`."""

        # Fix the visual point that users copy & paste from the web interface.
        new_text = self.convertDotToSpace(text)
        # Now, fix the newline chars.
        new_text = self.normalizeNewLines(new_text)
        # And finally, set the same whitespaces at the start/end of the string.
        new_text = self.normalizeWhitespaces(new_text)
        # Also, if it's an empty string, replace it with None.
        # XXX: Until we figure out ResettingTranslations
            if newtran == '':
                newtran = None
        if new_text == '':
            new_text = None

        return new_text

    def convertDotToSpace(self, text):
        """See IPOTMsgSet."""
        if u'\u2022' in self.singular_text or u'\u2022' not in text:
            return text

        return text.replace(u'\u2022', ' ')

    def normalizeWhitespaces(self, translation_text):
        """See IPOTMsgSet."""
        if translation_text is None:
            return None

        stripped_singular_text = self.singular_text.strip()
        stripped_translation_text = translation_text.strip()
        new_translation_text = None

        if (len(stripped_singular_text) > 0 and
            len(stripped_translation_text) == 0):
            return ''

        if len(stripped_singular_text) != len(self.singular_text):
            # There are whitespaces that we should copy to the 'text'
            # after stripping it.
            prefix = self.singular_text[:-len(self.singular_text.lstrip())]
            postfix = self.singular_text[len(self.singular_text.rstrip()):]
            new_translation_text = '%s%s%s' % (
                prefix, stripped_translation_text, postfix)
        elif len(stripped_translation_text) != len(translation_text):
            # msgid does not have any whitespace, we need to remove
            # the extra ones added to this text.
            new_translation_text = stripped_translation_text
        else:
            # The text is not changed.
            new_translation_text = translation_text

        return new_translation_text

    def normalizeNewLines(self, translation_text):
        """See IPOTMsgSet."""
        # There are three different kinds of newlines:
        windows_style = u'\r\n'
        mac_style = u'\r'
        unix_style = u'\n'
        # We need the stripped variables because a 'windows' style will be at
        # the same time a 'mac' and 'unix' style.
        stripped_translation_text = translation_text.replace(
            windows_style, u'')
        stripped_singular_text = self.singular_text.replace(windows_style, u'')

        # Get the style that uses singular_text.
        original_style = None
        if windows_style in self.singular_text:
            original_style = windows_style

        if mac_style in stripped_singular_text:
            if original_style is not None:
                raise BrokenTextError(
                    "original text (%r) mixes different newline markers" %
                        self.singular_text)
            original_style = mac_style

        if unix_style in stripped_singular_text:
            if original_style is not None:
                raise BrokenTextError(
                    "original text (%r) mixes different newline markers" %
                        self.singular_text)
            original_style = unix_style

        # Get the style that uses the given text.
        translation_style = None
        if windows_style in translation_text:
            translation_style = windows_style

        if mac_style in stripped_translation_text:
            if translation_style is not None:
                raise BrokenTextError(
                    "translation text (%r) mixes different newline markers" %
                        translation_text)
            translation_style = mac_style

        if unix_style in stripped_translation_text:
            if translation_style is not None:
                raise BrokenTextError(
                    "translation text (%r) mixes different newline markers" %
                        translation_text)
            translation_style = unix_style

        if original_style is None or translation_style is None:
            # We don't need to do anything, the text is not changed.
            return translation_text

        # Fix the newline chars.
        return translation_text.replace(translation_style, original_style)

    @property
    def hide_translations_from_anonymous(self):
        """See `IPOTMsgSet`."""
        # primemsgid_.msgid is pre-joined everywhere where
        # hide_translations_from_anonymous is used
        return self.primemsgid_.msgid in [
            u'translation-credits',
            u'translator-credits',
            u'translator_credits',
            u'_: EMAIL OF TRANSLATORS\nYour emails',
            u'Your emails',
            ]

    @property
    def is_translation_credit(self):
        """See `IPOTMsgSet`."""
        # primemsgid_.msgid is pre-joined everywhere where
        # is_translation_credit is used
        regular_credits = self.primemsgid_.msgid in [
            u'translation-credits',
            u'translator-credits',
            u'translator_credits' ]
        old_kde_credits = self.primemsgid_.msgid in [
            u'_: EMAIL OF TRANSLATORS\nYour emails',
            u'_: NAME OF TRANSLATORS\nYour names'
            ]
        kde_credits = ((self.primemsgid_.msgid == u'Your emails' and
                        self.context == u'EMAIL OF TRANSLATORS') or
                       (self.primemsgid_.msgid == u'Your names' and
                        self.context == u'NAME OF TRANSLATORS'))
        return (regular_credits or old_kde_credits or kde_credits)

    def makeHTMLId(self, suffix=None):
        """See `IPOTMsgSet`."""
        elements = ['msgset', str(self.id)]
        if suffix is not None:
            elements.append(suffix)
        return '_'.join(elements)
