# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POTMsgSet']

import gettextpo

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey, IntCol, StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote, sqlvalues

from canonical.launchpad import helpers

from canonical.launchpad.interfaces import (
    BrokenTextError, ILanguageSet, IPOTMsgSet, ITranslationImporter,
    RosettaTranslationOrigin, TranslationConflict, TranslationConstants,
    TranslationValidationStatus)
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.potranslation import POTranslation
from canonical.launchpad.database.translationmessage import (
    DummyTranslationMessage, TranslationMessage)


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
        if self.msgid_plural is None:
            return None
        else:
            return self.msgid_plural.msgid

    def getCurrentDummyTranslationMessage(self, language):
        """See `IPOTMsgSet`."""
        assert self.getCurrentTranslationMessage(language) is None, (
            'There is already a translation message in our database.')

        pofile = self.potemplate.getPOFileByLang(language.code)
        return DummyTranslationMessage(pofile, self)

    def getCurrentTranslationMessage(self, language):
        """See `IPOTMsgSet`."""
        return TranslationMessage.selectOne("""
            potmsgset = %s AND is_current IS TRUE AND POFile.language = %s
            AND pofile = POFile.id
            """ % sqlvalues(self, language), clauseTables=['POFile'])

    def getImportedTranslationMessage(self, language):
        """See `IPOTMsgSet`."""
        return TranslationMessage.selectOne("""
            potmsgset = %s AND is_imported IS TRUE AND POFile.language = %s
            AND pofile = POFile.id
            """ % sqlvalues(self, language), clauseTables=['POFile'])

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
            POFile.language = %s AND pofile=POFile.id""" %
                                         sqlvalues(self, language),
                                         clauseTables=['POFile'])

    def getExternalTranslationMessages(self, language):
        """See `IPOTMsgSet`."""
        return TranslationMessage.select(
            """id in (
              SELECT DISTINCT ON (msgstr0) TranslationMessage.id
                 FROM TranslationMessage
                 LEFT JOIN POTMsgSet ON
                   TranslationMessage.potmsgset = POTMsgSet.id
                 LEFT JOIN POFile ON
                   POFile.potemplate = POTMsgSet.potemplate
                 WHERE
                   is_current IS TRUE AND
                   -- Fuzzy are not really 'used in'
                   is_fuzzy IS NOT TRUE AND
                   -- Exclude ourselves
                   potmsgset != %s AND
                   POTMsgSet.msgid_singular=%s AND
                   POFile.language = %s AND
                   -- Exclude untranslated (deactivation) messages
                   (msgstr0 IS NOT NULL AND msgstr1 IS NOT NULL AND
                    msgstr2 IS NOT NULL AND msgstr3 IS NOT NULL)
                 ORDER BY TranslationMessage.date_created DESC
              )""" %
            sqlvalues(self, self.msgid_singular, language))

    def hasTranslationChangedInLaunchpad(self, language):
        """See `IPOTMsgSet`."""
        imported_translation = self.getImportedTranslationMessage(language)
        if (imported_translation is not None and
            not imported_translation.is_current):
            return True
        else:
            return False

    def isTranslationNewerThan(self, language, timestamp):
        """See `IPOTMsgSet`."""
        current = self.getCurrentTranslationMessage(language)
        if current is None:
            return False
        date_updated = current.date_created
        if (current.date_reviewed is not None and
            current.date_reviewed > date_updated):
            date_updated = current.date_reviewed
        if date_updated is not None and date_updated > timestamp:
            return True
        else:
            return False

    def _list_of_msgids(self):
        """Return a list of [singular_text, plural_text] if the message
        is using plural forms, or just [singular_text] if it's not.
        """
        original_texts = [self.singular_text]
        if self.plural_text is not None:
            original_texts.append(self.plural_text)
        return original_texts

    def _sanitizeTranslations(self, translations, pluralforms):
        """Sanitize `translations` using self.applySanityFixes.

        If there is no certain pluralform in `translations`, set it to None.
        If there are `translations` with greater pluralforms than allowed,
        sanitize and keep them.
        """
        # Fix the trailing and leading whitespaces
        sanitized_translations = {}
        for pluralform in range(pluralforms):
            if pluralform < len(translations):
                sanitized_translations[pluralform] = self.applySanityFixes(
                    translations[pluralform])
            else:
                sanitized_translations[pluralform] = None
        # Unneeded plural forms are stored as well (needed since we may
        # have incorrect plural form data, so we can just reactivate them
        # once we fix the plural information for the language)
        for index, value in enumerate(translations):
            if index not in sanitized_translations:
                sanitized_translations[index] = self.applySanityFixes(value)

        return sanitized_translations

    def _validate_translations(self, translations, fuzzy, ignore_errors):
        """Validate all the `translations` and return a validation_status."""
        # By default all translations are correct.
        validation_status = TranslationValidationStatus.OK

        # Cache the list of singular_text and plural_text
        original_texts = self._list_of_msgids()

        # Validate the translation we got from the translation form
        # to know if gettext is unhappy with the input.
        try:
            helpers.validate_translation(
                original_texts, translations, self.flags())
        except gettextpo.error:
            if fuzzy or ignore_errors:
                # The translations are stored anyway, but we set them as
                # broken.
                validation_status = TranslationValidationStatus.UNKNOWNERROR
            else:
                # Check to know if there is any translation.
                has_translations = False
                for key in translations.keys():
                    if translations[key] is not None:
                        has_translations = True
                        break

                if has_translations:
                    # Partial translations cannot be stored unless the fuzzy
                    # flag is set, the exception is raised again and handled
                    # outside this method.
                    raise

        return validation_status

    def _findPOTranslations(self, translations):
        """Find all POTranslation records for passed `translations`."""
        potranslations = {}
        # Set all POTranslations we can have (up to 4)
        for pluralform in range(4):
            if (pluralform in translations and
                translations[pluralform] is not None):
                translation = translations[pluralform]
                # Find or create a POTranslation for the specified text
                try:
                    potranslations[pluralform] = (
                        POTranslation.byTranslation(translation))
                except SQLObjectNotFound:
                    potranslations[pluralform] = (
                        POTranslation(translation=translation))
            else:
                potranslations[pluralform] = None
        return potranslations

    def _findTranslationMessage(self, language, potranslations, pluralforms):
        """Find a message for this language exactly matching given
        `translations` strings comparing only `pluralforms` of them."""
        query=('potmsgset=%s AND pofile=POFile.id AND POFile.language=%s'
               % sqlvalues(self, language))
        for pluralform in range(pluralforms):
            if potranslations[pluralform] is None:
                query += ' AND msgstr%s IS NULL' % sqlvalues(pluralform)
            else:
                query += ' AND msgstr%s=%s' % (
                    sqlvalues(pluralform, potranslations[pluralform]))
        return TranslationMessage.selectOne(query, clauseTables=['POFile'])

    def updateTranslation(self, pofile, submitter, new_translations, is_fuzzy,
                          is_imported, lock_timestamp, ignore_errors=False,
                          force_edition_rights=False):
        """See `IPOTMsgSet`."""
        assert self.potemplate == pofile.potemplate, (
            "The template for the translation file and this message doesn't"
            " match.")

        # Is the submitter allowed to edit translations?
        is_editor = (force_edition_rights or
                     pofile.canEditTranslations(submitter))

        assert (is_imported or is_editor or
                pofile.canAddSuggestions(submitter)), (
                  '%s cannot add translations nor can add suggestions' % (
                    submitter.displayname))

        # It makes no sense to have an "is_imported" submission from someone
        # who is not an editor, so assert that.
        if is_imported and not is_editor:
            raise AssertionError(
                'Only an editor can submit is_imported translations.')

        assert pofile.language.pluralforms is not None, (
            "Don't know the number of plural forms for %s language." % (
                pofile.language.englishname))

        # If the update is on the translation credits message, yet
        # update is not is_imported, silently return.
        # XXX 2007-06-26 Danilo: Do we want to raise an exception here?
        if self.is_translation_credit and not is_imported:
            return

        # Sanitize translations
        sanitized_translations = self._sanitizeTranslations(
            new_translations, pofile.language.pluralforms)
        # Check that the translations are correct.
        validation_status = self._validate_translations(sanitized_translations,
                                                        is_fuzzy, ignore_errors)

        # If not an editor, default to submitting a suggestion only.
        just_a_suggestion = not is_editor
        warn_about_lock_timestamp = False

        # Our current submission is newer than 'lock_timestamp'
        # and we try to change it, so just add a suggestion.
        if (not is_imported and not is_fuzzy and
            self.isTranslationNewerThan(pofile.language, lock_timestamp)):
            just_a_suggestion = True
            warn_about_lock_timestamp = True

        # Find all POTranslation records for strings we need.
        potranslations = self._findPOTranslations(sanitized_translations)

        # Find an existing TranslationMessage with exactly the same set
        # of translations.  None if there is no such message and needs to be
        # created.
        matching_message = self._findTranslationMessage(
            pofile.language, potranslations, pofile.language.pluralforms)

        # Whether we are creating a new message.
        new_message_created = False

        # If it's not a suggestion, it'll be made current.
        is_current = not just_a_suggestion

        has_changed = False

        if matching_message is None:
            new_message_created = True

            # A current one has changed if we are creating a new one.
            has_changed = is_current
            # Create a new one.
            if is_imported:
                origin = RosettaTranslationOrigin.SCM
            else:
                origin = RosettaTranslationOrigin.ROSETTAWEB

            matching_message = TranslationMessage(
                potmsgset=self,
                pofile=pofile,
                origin=origin,
                submitter=submitter,
                msgstr0=potranslations[0],
                msgstr1=potranslations[1],
                msgstr2=potranslations[2],
                msgstr3=potranslations[3],
                validation_status=validation_status)

            if just_a_suggestion:
                # Adds suggestion karma: editors get their translations
                # automatically approved, so they get 'reviewer' karma instead.
                submitter.assignKarma(
                    'translationsuggestionadded',
                    product=self.potemplate.product,
                    distribution=self.potemplate.distribution,
                    sourcepackagename=self.potemplate.sourcepackagename)

        else:
            # Also update validation status if needed
            matching_message.validation_status = validation_status

        if not just_a_suggestion:
            if is_imported:
                current_message = self.getCurrentTranslationMessage(
                    pofile.language)
                if not current_message or current_message.is_imported:
                    matching_message.is_current = True
            else:
                current_message = self.getCurrentTranslationMessage(
                    pofile.language)
                matching_message.is_current = is_current

        if just_a_suggestion:
            if not matching_message.is_current:
                matching_message.is_fuzzy = is_fuzzy
            if warn_about_lock_timestamp:
                raise TranslationConflict(
                    'The new translations were saved as suggestions to avoid '
                    'possible conflicts. Please review them.')
        else: # It's current submission and submitter is an editor.
            matching_message.is_fuzzy = is_fuzzy

            # Set message as current only if it validates ok.
            if (has_changed and (matching_message.validation_status ==
                                 TranslationValidationStatus.OK)):
                pofile.lasttranslator = submitter
                pofile.date_changed = UTC_NOW

            if is_imported:
                matching_message.is_imported = True
            else:
                if (new_message_created and
                    (matching_message.origin ==
                     RosettaTranslationOrigin.ROSETTAWEB)):
                    # The submitted translation came from our UI, we give
                    # give karma to the submitter of that translation.
                    matching_message.submitter.assignKarma(
                        'translationsuggestionapproved',
                        product=self.potemplate.product,
                        distribution=self.potemplate.distribution,
                        sourcepackagename=self.potemplate.sourcepackagename)
                if (has_changed and matching_message.submitter != submitter):
                    # A reviewer activated someone else's translation.
                    submitter.assignKarma(
                        'translationreview',
                        product=self.potemplate.product,
                        distribution=self.potemplate.distribution,
                        sourcepackagename=self.potemplate.sourcepackagename)
                if has_changed:
                    matching_message.reviewer = submitter
                    matching_message.date_reviewed = UTC_NOW

        return matching_message

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
        # msgid_singular.msgid is pre-joined everywhere where
        # hide_translations_from_anonymous is used
        return self.msgid_singular.msgid in [
            u'translation-credits',
            u'translator-credits',
            u'translator_credits',
            u'_: EMAIL OF TRANSLATORS\nYour emails',
            u'Your emails',
            ]

    @property
    def is_translation_credit(self):
        """See `IPOTMsgSet`."""
        # msgid_singular.msgid is pre-joined everywhere where
        # is_translation_credit is used
        regular_credits = self.msgid_singular.msgid in [
            u'translation-credits',
            u'translator-credits',
            u'translator_credits' ]
        old_kde_credits = self.msgid_singular.msgid in [
            u'_: EMAIL OF TRANSLATORS\nYour emails',
            u'_: NAME OF TRANSLATORS\nYour names'
            ]
        kde_credits = ((self.msgid_singular.msgid == u'Your emails' and
                        self.context == u'EMAIL OF TRANSLATORS') or
                       (self.msgid_singular.msgid == u'Your names' and
                        self.context == u'NAME OF TRANSLATORS'))
        return (regular_credits or old_kde_credits or kde_credits)

    def makeHTMLId(self, suffix=None):
        """See `IPOTMsgSet`."""
        elements = ['msgset', str(self.id)]
        if suffix is not None:
            elements.append(suffix)
        return '_'.join(elements)
