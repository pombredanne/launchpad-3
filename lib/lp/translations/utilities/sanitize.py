# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'sanitize_translations',
    ]

from lp.translations.interfaces.potmsgset import BrokenTextError


class Sanitize(object):
    """Provide a function to sanitize a translation text."""

    # There are three different kinds of newlines:
    windows_style = u'\r\n'
    mac_style = u'\r'
    unix_style = u'\n'


    def __init__(self, english_singular):
        """Extract information from the English singular."""
        # Does the dot character appear in the Eglish singular?
        self.has_dots = u'\u2022' in english_singular
        # Find out if there is leading or trailing whitespace in the English
        # singular.
        stripped_singular_text = english_singular.strip()
        self.len_stripped = len(stripped_singular_text)
        if self.len_stripped != len(english_singular):
            # There are whitespaces that we should copy to the 'text'
            # after stripping it.
            self.prefix = english_singular[:-len(english_singular.lstrip())]
            self.postfix = english_singular[len(english_singular.rstrip()):]
        else:
            self.prefix = ''
            self.postfix = ''
        # Get the newline style that is used in the English Singular.
        self.newline_style = self._getNewlineStyle(
            english_singular, 'Original')

    def _getNewlineStyle(self, text, text_name):
        """Find out which newline style is used in text."""
        stripped_text = text.replace(self.windows_style, u'')
        style = None
        error_message = (
            "%s text (%r) mixes different newline markers" % (
                text_name, text)
            )
        if self.windows_style in text:
            style = self.windows_style

        if self.mac_style in stripped_text:
            if style is not None:
                raise BrokenTextError(error_message)
            style = self.mac_style

        if self.unix_style in stripped_text:
            if style is not None:
                raise BrokenTextError(error_message)
            style = self.unix_style
        return style

    def __call_(self, translation_text):
        """Return 'translation_text' or None after doing some sanitization.

        The text is sanitized through the following filters:

          self.convertDotToSpace
          self.normalizeWhitespaces
          self.normalizeNewlines

        If the resulting string after these operations is an empty string,
        it returns None.

        :param english_singular: The text of the singular MsgId that this
            translation is for.
        :param translation_text: A unicode text that needs to be sanitized.
        """
        if translation_text is None:
            return None

        # Fix the visual point that users copy & paste from the web interface.
        new_text = self.convertDotToSpace(translation_text)
        # Now, fix the newline chars.
        new_text = self.normalizeNewlines(new_text)
        # Finally, set the same whitespaces at the start/end of the string.
        new_text = self.normalizeWhitespaces(new_text)
        # Also, if it's an empty string, replace it with None.
        if new_text == '':
            new_text = None

        return new_text

    def convertDotToSpace(self, translation_text):
        """Return 'translation_text' with the u'\u2022' char exchanged with a
        normal space.

        If the english_singular contains that character, 'translation_text' is
        returned without changes as it's a valid char instead of our way to
        represent a normal space to the user.
        """
        if self.has_dots or u'\u2022' not in translation_text:
            return translation_text

        return translation_text.replace(u'\u2022', ' ')

    def normalizeWhitespaces(self, translation_text):
        """Return 'translation_text' with the same trailing and leading
        whitespaces that self.singular_text has.

        If 'translation_text' has only whitespaces but english_singular has
        other characters, the empty string (u'') is returned to note it as an
        untranslated string.
        """
        if translation_text is None:
            return None

        stripped_translation_text = translation_text.strip()

        if self.len_stripped > 0 and len(stripped_translation_text) == 0:
            return ''

        return '%s%s%s' % (
            self.prefix, stripped_translation_text, self.postfix)

    def normalizeNewlines(self, translation_text):
        """Return 'translation_text' with newlines sync with english_singular.
        """
        if self.newline_style is None:
            # No newlines in the English singular, so we have nothing to do.
            return translation_text

        # Get the style that uses the given text.
        translation_newline_style = self._getNewlineStyle(
            translation_text, 'Translations')

        if translation_newline_style is None:
            # We don't need to do anything, the text is not changed.
            return translation_text

        # Fix the newline chars.
        return translation_text.replace(
            translation_newline_style, self.newline_style)


def sanitize_translations(english_singular, translations, pluralforms):
    """Sanitize `translations` using sanitize_translation.

    If there is no certain pluralform in `translations`, set it to None.
    If there are `translations` with greater pluralforms than allowed,
    sanitize and keep them.
    :param english_singular: The text of the singular MsgId that these
        translations are for.
    :param translations: A dictionary of plural forms, with the
        integer plural form number as the key and the translation as the
        value.
    :param pluralforms: The number of expected pluralforms
    """
    # Sanitize translations and normalize empty translations to None.
    sanitized_translations = {}
    sanitize = Sanitize(english_singular)
    for pluralform in range(pluralforms):
        if pluralform in translations:
            sanitized_translations[pluralform] = (
                sanitize(translations[pluralform]))
        else:
            sanitized_translations[pluralform] = None
    # Unneeded plural forms are stored as well (needed since we may
    # have incorrect plural form data, so we can just reactivate them
    # once we fix the plural information for the language)
    for index, value in enumerate(translations):
        if index >= pluralforms:
            sanitized_translations[index] = sanitize(value)

    return sanitized_translations

