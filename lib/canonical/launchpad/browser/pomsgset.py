# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POMsgSetView']

from zope.exceptions import NotFoundError
from zope.component import getUtility

from canonical.launchpad import helpers
from canonical.launchpad.helpers import TranslationConstants
from canonical.launchpad.interfaces import ILanguageSet


class POMsgSetView:
    """Class that holds all data needed to show a POMsgSet."""

    def __init__(self, potmsgset, code, plural_form_counts,
                 web_translations=None, web_fuzzy=None, error=None):
        """Create a object representing the potmsgset with translations.


        'web_translations' and 'web_fuzzy' overrides the translations/fuzzy
        flag in our database for this potmsgset.
        If 'error' is not None, the translations at web_translations contain
        an error with the.
        """
        self.potmsgset = potmsgset
        self.id = potmsgset.id
        self.msgids = list(potmsgset.messageIDs())
        self.web_translations = web_translations
        self.web_fuzzy = web_fuzzy
        self.error = error
        self.plural_form_counts = plural_form_counts
        self.translations = None
        self.language = getUtility(ILanguageSet)[code]
        self._wiki_submissions = None
        self._current_submissions = None
        self._suggested_submissions = None

        try:
            self.pomsgset = potmsgset.poMsgSet(code)
        except NotFoundError:
            # The PO file doesn't have this message ID.
            self.pomsgset = None

        if len(self.msgids) == 0:
            raise AssertionError(
                'Found a POTMsgSet without any POMsgIDSighting')

        self.msgidHasTab = False

        for msgid in self.msgids:
            if '\t' in msgid.msgid:
                self.msgidHasTab = True
                break

    def getMsgID(self):
        """Return a msgid string prepared to render in a web page."""
        msgid = self.msgids[TranslationConstants.SINGULAR_FORM].msgid
        return helpers.msgid_html(msgid, self.potmsgset.flags())

    def getMsgIDPlural(self):
        """Return a msgid plural string prepared to render as a web page.

        If there is no plural form, return None.
        """
        if self.isPlural():
            msgid = self.msgids[TranslationConstants.PLURAL_FORM].msgid
            return helpers.msgid_html(msgid, self.potmsgset.flags())
        else:
            return None

    def getMaxLinesCount(self):
        """Return the max number of lines a multiline entry will have

        It will never be bigger than 12.
        """
        if self.isPlural():
            singular_lines = helpers.count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)
            plural_lines = helpers.count_lines(
                self.msgids[TranslationConstants.PLURAL_FORM].msgid)
            lines = max(singular_lines, plural_lines)
        else:
            lines = helpers.count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)

        return min(lines, 12)

    def isPlural(self):
        """Return if we have plural forms or not."""
        return len(self.msgids) > 1

    def isMultiline(self):
        """Return if the singular or plural msgid have more than one line."""
        return self.getMaxLinesCount() > 1

    def getSequence(self):
        """Return the position number of this potmsgset."""
        return self.potmsgset.sequence

    def getFileReferences(self):
        """Return the file references for this potmsgset.

        If there are no file references, return None.
        """
        return self.potmsgset.filereferences

    def getSourceComment(self):
        """Return the source code comments for this potmsgset.

        If there are no source comments, return None.
        """
        return self.potmsgset.sourcecomment

    def getComment(self):
        """Return the translator comments for this pomsgset.

        If there are no comments, return None.
        """
        if self.pomsgset is None:
            return None
        else:
            return self.pomsgset.commenttext

    def _prepareTranslations(self):
        """Prepare self.translations to be used.
        """
        if self.translations is None:
            # This is done only the first time.
            if self.web_translations is None:
                self.web_translations = {}

            # Fill the list of translations based on the input the user
            # submitted.
            web_translations_keys = self.web_translations.keys()
            web_translations_keys.sort()
            self.translations = [
                self.web_translations[web_translations_key]
                for web_translations_key in web_translations_keys]

            if self.pomsgset is None and not self.translations:
                if self.plural_form_counts is None or not self.isPlural():
                    # Either we don't have plural form information or this
                    # entry has not plural forms.
                    self.translations = [None]
                else:
                    self.translations = [None] * self.plural_form_counts
            elif self.pomsgset is not None and not self.translations:
                self.translations = self.pomsgset.active_texts

    def getTranslationRange(self):
        """Return a list with all indexes we have to get translations."""
        self._prepareTranslations()
        return range(len(self.translations))

    def getTranslation(self, index):
        """Return the active translation for the pluralform 'index'.

        There are as many translations as the plural form information defines
        for that language/pofile. If one of those translations does not
        exists, it will have a None value. If the potmsgset is not a plural
        form one, we only have one entry.
        """
        self._prepareTranslations()

        if index in self.getTranslationRange():
            translation = self.translations[index]
            # We store newlines as '\n' but forms should have them as '\r\n'
            # so we need to change them before showing them.
            return helpers.unix2windows_newlines(translation)
        else:
            raise IndexError('Translation out of range')

    # The three functions below are tied to the UI policy. In essence, they
    # will present up to three proposed translations from each of the
    # following categories in order:
    #
    #   - new submissions to this pofile by people who don't have permission
    #     to write here
    #   - items actually published or currently active elsewhere
    #   - new submissions to ANY similar pofile for the same msgset from
    #     people who did not have write permission THERE
    def getWikiSubmissions(self, index):
        # the UI expects these to come after suggested and current, and will
        # present at most three of them
        if self._wiki_submissions is not None:
            return self._wiki_submissions
        curr = self.getTranslation(index)
        wiki = self.potmsgset.getWikiSubmissions(self.language, index)
        suggested = self.getSuggestedSubmissions(index)
        suggested_texts = [s.potranslation.translation
                           for s in suggested]
        current = self.getCurrentSubmissions(index)
        current_texts = [c.potranslation.translation
                         for c in current]
        self._wiki_submissions = list([submission for submission in wiki
            if submission.potranslation.translation != curr and
            submission.potranslation.translation not in suggested_texts and
            submission.potranslation.translation not in current_texts])[:3]
        return self._wiki_submissions

    def getCurrentSubmissions(self, index):
        # the ui expectes these after the suggested ones and will show at
        # most 3 of them
        if self._current_submissions is not None:
            return self._current_submissions
        curr = self.getTranslation(index)
        current = self.potmsgset.getCurrentSubmissions(self.language, index)
        suggested = self.getSuggestedSubmissions(index)
        suggested_texts = [s.potranslation.translation
                           for s in suggested]
        self._current_submissions = list([submission
            for submission in current 
            if submission.potranslation.translation != curr and
            submission.potranslation.translation not in suggested_texts])[:3]
        return self._current_submissions

    def getSuggestedSubmissions(self, index):
        # these are expected to be shown first, we will show at most 3 of
        # them
        if self._suggested_submissions is not None:
            return self._suggested_submissions
        if not self.pomsgset:
            return []
        self._suggested_submissions = list(self.pomsgset.getSuggestedSubmissions(index))[:3]
        return self._suggested_submissions

    def isFuzzy(self):
        """Return if this pomsgset is set as fuzzy or not."""
        if self.web_fuzzy is None and self.pomsgset is None:
            return False
        elif self.web_fuzzy is not None:
            return self.web_fuzzy
        else:
            return self.pomsgset.isfuzzy

    def getError(self):
        """Return a string with the error.

        If there is no error, return None.
        """
        return self.error


