# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser code for Product Series Languages."""

__metaclass__ = type

__all__ = ['TranslatableMessageView']

from canonical.launchpad.webapp import LaunchpadView
from lp.translations.browser.browser_helpers import text_to_html


class TranslatableMessageView(LaunchpadView):
    """View class to render an `ITranslatableMessage`."""

    @property
    def label(self):
        """The form label."""
        return 'Translate messge %d into %s' % (
            self.context.sequence,
            self.context.pofile.language.englishname)

    @property
    def page_title(self):
        """The page title."""
        return self.label

    @property
    def singular_text(self):
        """HTML version of the singular msgid."""
        return text_to_html(self.context.potmsgset.singular_text,
                            self.context.potmsgset.flags)

    @property
    def plural_text(self):
        """HTML version of the plural msgid."""
        return text_to_html(self.context.potmsgset.plural_text,
                            self.context.potmsgset.flags)

    def _translation_info(self, plural, text):
        """Build a dictionary with 'plural' and 'text' keys."""
        return {'plural': plural,
                'text': text_to_html(text, self.context.potmsgset.flags)}

    def _make_translation_info(self, translationmessage):
        """Prepare translation information for the given message."""
        if self.context.has_plural_forms:
            translations = [
                self._translation_info(u"Plural %d:" % index, msgstr)
                for index, msgstr in enumerate(
                                        translationmessage.translations)]
            translator_class = "translator_plural"
        else:
            translations = [self._translation_info(
                                "", translationmessage.msgstr0.translation)]
            translator_class = "translator_singular"
        return {
            'translator': translationmessage.submitter,
            'translation_class': 'current',
            'translator_class': translator_class,
            'translations': translations,
            }

    @property
    def current_translation(self):
        """Information about the current translation prepared for display.

        :returns: A dictionary with the following keys:
          translator - The IPerson object of the translator or None.
          translations - A list of dictionaries with the following keys:
            plural - The plural label to explain this form or an empty string
            text - The actual translation text as HTML
          translator_class - the css class to use for the translator
          translation_class - The css class to use for the translation
        """
        current = self.context.getCurrentTranslation()
        if current is None:
            return {'translator': None,
                    'translation_class': 'current_empty',
                    'translator_class': '',
                    'translations': [
                        self._translation_info(u"", u"(no translation yet)")]}
        return self._make_translation_info(current)

