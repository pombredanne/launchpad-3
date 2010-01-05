#! /usr/bin/python2.5
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the validate-translations-file script."""

__metaclass__ = type

import logging
from textwrap import dedent
from unittest import TestCase, TestLoader

from lp.translations.scripts.validate_translations_file import (
    UnknownFileType, ValidateTranslationsFile)


class TestValidateTranslationsFile(TestCase):

    def _makeValidator(self, test_args=None):
        """Produce a ValidateTranslationsFile."""
        if test_args is None:
            test_args = []
        validator = ValidateTranslationsFile(test_args=test_args)
        validator.logger.setLevel(logging.CRITICAL)
        return validator

    def _strip(self, file_contents):
        """Remove leading newlines & indentation from file_contents."""
        return dedent(file_contents.strip())

    def test_validate_unknown(self):
        # Unknown filename extensions result in UnknownFileType.
        validator = self._makeValidator(['foo.bar'])
        self.assertRaises(
            UnknownFileType, validator._validateContent, 'foo.bar', 'content')

    def test_validate_dtd_good(self):
        validator = self._makeValidator()
        result = validator._validateContent(
            'test.dtd', '<!ENTITY a.translatable.string "A string">\n')
        self.assertTrue(result)

    def test_validate_dtd_bad(self):
        validator = self._makeValidator()
        result = validator._validateContent(
            'test.dtd', '<!ENTIT etc.')
        self.assertFalse(result)

    def test_validate_xpi_manifest_good(self):
        validator = self._makeValidator()
        result = validator._validateContent(
            'chrome.manifest', 'locale foo nl jar:chrome/nl.jar!/foo/')
        self.assertTrue(result)

    def test_validate_xpi_manifest_bad(self):
        # XPI manifests must not begin with newline.
        validator = self._makeValidator()
        result = validator._validateContent('chrome.manifest', '\nlocale')
        self.assertFalse(result)

    def test_validate_po_good(self):
        validator = self._makeValidator()
        result = validator._validateContent('nl.po', self._strip(r"""
            msgid ""
            msgstr ""
            "MIME-Version: 1.0\n"
            "Content-Type: text/plan; charset=UTF-8\n"
            "Content-Transfer-Encoding: 8bit\n"

            msgid "foo"
            msgstr "bar"
            """))
        self.assertTrue(result)

    def test_validate_po_bad(self):
        validator = self._makeValidator()
        result = validator._validateContent('nl.po', self._strip("""
            msgid "no header here"
            msgstr "hier geen kopje"
            """))
        self.assertFalse(result)

    def test_validate_pot_good(self):
        validator = self._makeValidator()
        result = validator._validateContent('test.pot', self._strip(r"""
            msgid ""
            msgstr ""
            "MIME-Version: 1.0\n"
            "Content-Type: text/plan; charset=UTF-8\n"
            "Content-Transfer-Encoding: 8bit\n"

            msgid "foo"
            msgstr ""
            """))
        self.assertTrue(result)

    def test_validate_pot_bad(self):
        validator = self._makeValidator()
        result = validator._validateContent('test.pot', 'garble')
        self.assertFalse(result)

    def test_validate_xpi_good(self):
        pass
    def test_validate_xpi_bad(self):
        pass
    def test_readAndValidate(self):
        pass
    def test_script(self):
        pass
