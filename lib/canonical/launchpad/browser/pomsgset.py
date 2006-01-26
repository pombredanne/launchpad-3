# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POMsgSetView']

import re
import gettextpo
from zope.exceptions import NotFoundError
from zope.component import getUtility

from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPOMsgSet, TranslationConstants)
from canonical.launchpad.webapp import LaunchpadView




class POMsgSetView(LaunchpadView):
    """Holds all data needed to show an IPOMsgSet."""

    __used_for__ = IPOMsgSet

    def initialize(self):
        self.form = self.request.form
        self.potmsgset = self.context.potmsgset
        self.id = self.potmsgset.id
        self.pofile = self.context.pofile
        self.translations = None

        # By default the submitted values are None
        self.web_translations = None
        self.web_needs_review = None
        self.error = None

        # At this point, we don't know the alternative language selected.
        self.second_lang_pofile = None
        self.second_lang_msgset = None

        # We don't know the suggestions either.
        self._wiki_submissions = None
        self._current_submissions = None
        self._suggested_submissions = None
        self._second_language_submissions = None

        self.msgids = list(self.potmsgset.messageIDs())

        assert len(self.msgids) > 0, (
            'Found a POTMsgSet without any POMsgIDSighting')

        # Handle any form submission.
        self.process_form()

    @property
    def is_plural(self):
        """Return whether there are plural forms."""
        return len(self.msgids) > 1

    @property
    def max_lines_count(self):
        """Return the max number of lines a multiline entry will have

        It will never be bigger than 12.
        """
        if self.is_plural:
            singular_lines = helpers.count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)
            plural_lines = helpers.count_lines(
                self.msgids[TranslationConstants.PLURAL_FORM].msgid)
            lines = max(singular_lines, plural_lines)
        else:
            lines = helpers.count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)

        return min(lines, 12)

    @property
    def is_multi_line(self):
        """Return whether the singular or plural msgid have more than one line.
        """
        return self.max_lines_count > 1

    @property
    def sequence(self):
        """Return the position number of this potmsgset."""
        return self.potmsgset.sequence

    @property
    def msgid(self):
        """Return a msgid string prepared to render in a web page."""
        msgid = self.msgids[TranslationConstants.SINGULAR_FORM].msgid
        return helpers.msgid_html(msgid, self.potmsgset.flags())

    @property
    def msgid_plural(self):
        """Return a msgid plural string prepared to render as a web page.

        If there is no plural form, return None.
        """
        if self.is_plural:
            msgid = self.msgids[TranslationConstants.PLURAL_FORM].msgid
            return helpers.msgid_html(msgid, self.potmsgset.flags())
        else:
            return None

    @property
    def msgid_has_tab(self):
        """Return whether there are a msgid with a '\t' char."""
        for msgid in self.msgids:
            if '\t' in msgid.msgid:
                return True
        return False

    @property
    def source_comment(self):
        """Return the source code comments for this IPOMsgSet."""
        return self.potmsgset.sourcecomment

    @property
    def comment(self):
        """Return the translator comments for this IPOMsgSet."""
        return self.context.commenttext

    @property
    def file_references(self):
        """Return the file references for this IPOMsgSet."""
        return self.potmsgset.filereferences

    @property
    def translation_range(self):
        """Return a list with all indexes we have to get translations."""
        self._prepare_translations()
        return range(len(self.translations))

    @property
    def is_fuzzy(self):
        """Return whether this pomsgset is set as fuzzy."""
        if self.web_needs_review is not None:
            return self.web_needs_review
        else:
            return self.context.isfuzzy

    def _prepare_translations(self):
        """Prepare self.translations to be used."""
        if self.translations is not None:
            # We have already the translations prepared.
            return

        if self.web_translations is None:
            self.web_translations = {}

        # Fill the list of translations based on the input the user
        # submitted.
        web_translations_keys = self.web_translations.keys()
        web_translations_keys.sort()
        self.translations = [
            self.web_translations[web_translations_key]
            for web_translations_key in web_translations_keys]

        if not self.translations:
            # We didn't get any translation from the website.
            self.translations = self.context.active_texts

    def getTranslation(self, index):
        """Return the active translation for the pluralform 'index'.

        There are as many translations as the plural form information defines
        for that language/pofile. If one of those translations does not
        exists, it will have a None value. If the potmsgset is not a plural
        form one, we only have one entry.
        """
        self._prepare_translations()

        if index in self.translation_range:
            translation = self.translations[index]
            # We store newlines as '\n' but forms should have them as '\r\n'
            # so we need to change them before showing them.
            return helpers.unix2windows_newlines(translation)
        else:
            raise IndexError('Translation out of range')

    def set_second_lang_pofile(self, second_lang_pofile):
        """Store the selected second_lang_pofile reference.

        :second_lang_pofile: Is an IPOFile pointing to the language chosen by
            the user as the second language to see translations from.
        """
        self.second_lang_pofile = second_lang_pofile

        if self.second_lang_pofile:
            msgid_text = self.potmsgset.primemsgid_.msgid
            try:
                self.second_lang_msgset = (
                    second_lang_pofile[msgid_text]
                    )
            except NotFoundError:
                # The second language doesn't have this message ID.
                self.second_lang_msgset = None

        # Force a refresh of self._second_language_submissions
        self._second_language_submissions = None


    # The three functions below are tied to the UI policy. In essence, they
    # will present up to three proposed translations from each of the
    # following categories in order:
    #
    #   - new submissions to this pofile by people who don't have permission
    #     to write here
    #   - items actually published or currently active elsewhere
    #   - new submissions to ANY similar pofile for the same msgset from
    #     people who did not have write permission THERE
    def get_wiki_submissions(self, index):
        # the UI expects these to come after suggested and current, and will
        # present at most three of them
        if self._wiki_submissions is not None:
            return self._wiki_submissions
        curr = self.getTranslation(index)

        wiki = self.context.getWikiSubmissions(index)
        suggested = self.get_suggested_submissions(index)
        suggested_texts = [s.potranslation.translation
                           for s in suggested]
        current = self.get_current_submissions(index)
        current_texts = [c.potranslation.translation
                         for c in current]
        self._wiki_submissions = [submission for submission in wiki
            if submission.potranslation.translation != curr and
            submission.potranslation.translation not in suggested_texts and
            submission.potranslation.translation not in current_texts][:3]
        return self._wiki_submissions

    def get_current_submissions(self, index):
        # the ui expectes these after the suggested ones and will show at
        # most 3 of them
        if self._current_submissions is not None:
            return self._current_submissions
        curr = self.getTranslation(index)

        current = self.context.getCurrentSubmissions(index)
        suggested = self.get_suggested_submissions(index)
        suggested_texts = [s.potranslation.translation
                           for s in suggested]
        self._current_submissions = [submission
            for submission in current 
            if submission.potranslation.translation != curr and
            submission.potranslation.translation not in suggested_texts][:3]
        return self._current_submissions

    def get_suggested_submissions(self, index):
        # these are expected to be shown first, we will show at most 3 of
        # them
        if self._suggested_submissions is not None:
            return self._suggested_submissions

        sugg = self.context.getSuggestedSubmissions(index)
        self._suggested_submissions = sugg[:3]
        return self._suggested_submissions

    def get_alternate_language_submissions(self, index):
        """Get suggestions for translations from the alternate language for
        this potemplate."""
        if self._second_language_submissions is not None:
            return self._second_language_submissions
        if self.second_lang_msgset is None:
            return []
        sec_lang = self.second_lang_pofile.language
        sec_lang_potmsgset = self.second_lang_msgset.potmsgset
        curr = sec_lang_potmsgset.getCurrentSubmissions(sec_lang, index)
        self._second_language_submissions = curr[:3]
        return self._second_language_submissions

    def process_form(self):
        """Check whether the form was submitted and calls the right callback.
        """
        if self.request.method != 'POST' or self.user is None:
            # The form was not submitted or the user is not logged in.
            return

        dispatch_table = {
            'submit_translations': self._submit_translations
            }
        dispatch_to = [(key, method)
                        for key,method in dispatch_table.items()
                        if key in self.form
                      ]
        if len(dispatch_to) != 1:
            raise AssertionError(
                "There should be only one command in the form",
                dispatch_to)
        key, method = dispatch_to[0]
        method()

    def _extract_translations_from_form(self):
        """Parse the form submitted to the translation widget looking for
        translations.

        Store the new translations at self.web_translations and its status at
        self.web_needs_review.
        """
        # Reset any old values we could have
        self.web_translations = None
        self.web_needs_review = None
        self.error = None

        # Initialize the entry if we find it in the form submission.
        for key in self.form:
            if key == ('set_%d_msgid' % self.id):
                self.web_translations = {}
                self.web_needs_review = False

        # Extract translations.
        pluralform = 0
        while True:
            key = 'set_%d_translation_%s_%d' % (
                self.id, self.pofile.language.code, pluralform)
            value = self.form.get(key)
            if value is None:
                # There aren't more translations for self.id.
                break
            # Store the translation for the given plural form.
            translation_normalized = (
                helpers.normalize_newlines(value))
            self.web_translations[pluralform] = (
                helpers.contract_rosetta_tabs(translation_normalized))
            pluralform += 1

        # Extract 'needs review' statuses.
        value = self.form.get('set_%d_needs_review_%s' % (
            self.id, self.pofile.language.code))
        if value is not None:
            self.web_needs_review = True


    def _submit_translations(self):
        """Handle a form submission for the translation form.

        The form contains translations, some of which will be unchanged, some
        of which will be modified versions of old translations and some of
        which will be new. Returns a dictionary mapping sequence numbers to
        submitted message sets, where each message set will have information
        on any validation errors it has.
        """
        # Extract the values from the form and set self.web_translations and
        # self.web_needs_review.
        self._extract_translations_from_form()

        if self.web_translations is None:
            # There are not translations interesting for us.
            return

        has_translations = False
        for web_translation_key in self.web_translations.keys():
            if self.web_translations[web_translation_key] != '':
                has_translations = True
                break

        if has_translations and not self.web_needs_review:
            # The submit has translations to validate and are not set as
            # needs review.

            msgids_text = [pomsgid.msgid
                           for pomsgid in self.potmsgset.messageIDs()]

            # Validate the translation we got from the translation form
            # to know if gettext is happy with the input.
            try:
                helpers.validate_translation(msgids_text,
                                             self.web_translations,
                                             self.potmsgset.flags())
            except gettextpo.error, e:
                # Save the error message gettext gave us to show it to the
                # user and jump to the next entry so this messageSet is
                # not stored into the database.
                self.error = str(e)
                return

        try:
            self.context.updateTranslationSet(
                person=self.user,
                new_translations=self.web_translations,
                fuzzy=self.web_needs_review,
                published=False)
        except gettextpo.error, e:
            # Save the error message gettext gave us to show it to the
            # user.
            self.error = str(e)

        # update the statistis for this po file
        self.pofile.updateStatistics()
