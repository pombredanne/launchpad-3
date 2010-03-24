# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from lp.translations.utilities.sanitize import Sanitize


class TestSanitizeTranslations(unittest.TestCase):
    """Test sanitization functions."""

    def test_convertDotToSpace(self):
        # Dots are converted back to spaces.
        sanitize = Sanitize(u"English with space.")
        translation = u"Text\u2022with\u2022dots."
        expected_sanitized = u"Text with dots."

        self.assertEqual(
            expected_sanitized,
            sanitize.convertDotToSpace(translation))

    def test_convertDotToSpace_dot_in_english(self):
        # If there are dots in the English string, no conversion happens.
        sanitize = Sanitize(u"English\u2022with\u2022dots.")
        translation = u"Text\u2022with\u2022dots."
        expected_sanitized = u"Text\u2022with\u2022dots."

        self.assertEqual(
            expected_sanitized,
            sanitize.convertDotToSpace(translation))

    def test_normalizeWhitespaces_add(self):
        # Leading and trailing white space in the translation are synced to
        # what the English text has.
        sanitize = Sanitize(u"  English with leading white space.  ")
        translation = u"Text without white space."
        expected_sanitized = u"  Text without white space.  "

        self.assertEqual(
            expected_sanitized,
            sanitize.normalizeWhitespaces(translation))

    def test_normalizeWhitespaces_remove(self):
        # Leading and trailing white space in the translation are synced to
        # what the English text has.
        sanitize = Sanitize(u"English without leading white space.")
        translation = u"  Text with white space.  "
        expected_sanitized = u"Text with white space."

        self.assertEqual(
            expected_sanitized,
            sanitize.normalizeWhitespaces(translation))

    def test_normalizeWhitespaces_add_and_remove(self):
        # Leading and trailing white space in the translation are synced to
        # what the English text has.
        sanitize = Sanitize(u"  English with leading white space.")
        translation = u"Text with trailing white space.  "
        expected_sanitized = u"  Text with trailing white space."

        self.assertEqual(
            expected_sanitized,
            sanitize.normalizeWhitespaces(translation))

