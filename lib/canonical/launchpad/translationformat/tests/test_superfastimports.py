# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.testing import ZopelessDatabaseLayer
from lp.testing import TestCaseWithFactory, verifyObject
from canonical.launchpad.translationformat.translation_import import (
    ExistingPOFileInDatabase)
from canonical.launchpad.translationformat.translation_common_format import (
    TranslationMessageData)

class TestSuperFastImports(TestCaseWithFactory):
    """Test how ExistingPOFileInDatabase cache works."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(TestSuperFastImports, self).setUp()
        self.pofile = self.factory.makePOFile('sr')

    def getTranslationMessageData(self, translationmessage):
        potmsgset = translationmessage.potmsgset
        message_data = TranslationMessageData()
        message_data.context = potmsgset.context
        message_data.msgid_singular = potmsgset.singular_text
        message_data.msgid_plural = potmsgset.plural_text
        translations = translationmessage.translations
        for plural in range(len(translations)):
            message_data.addTranslation(
                plural, translations[plural])
        return message_data

    def test_current_messages(self):
        current_message = self.factory.makeTranslationMessage(
            pofile=self.pofile, is_imported=False)
        cached_file = ExistingPOFileInDatabase(self.pofile)
        message_data = self.getTranslationMessageData(current_message)
        self.assertFalse(cached_file.isAlreadyImportedTheSame(message_data))
        self.assertTrue(cached_file.isAlreadyTranslatedTheSame(message_data))

    def test_imported_messages(self):
        imported_message = self.factory.makeTranslationMessage(
            pofile=self.pofile, is_imported=True)
        cached_file = ExistingPOFileInDatabase(self.pofile, is_imported=True)
        message_data = self.getTranslationMessageData(imported_message)
        self.assertTrue(cached_file.isAlreadyImportedTheSame(message_data))
        self.assertTrue(cached_file.isAlreadyTranslatedTheSame(message_data))

    def test_inactive_messages(self):
        inactive_message = self.factory.makeTranslationMessage(
            pofile=self.pofile, suggestion=True)
        cached_file = ExistingPOFileInDatabase(self.pofile)
        message_data = self.getTranslationMessageData(inactive_message)
        self.assertFalse(cached_file.isAlreadyImportedTheSame(message_data))
        self.assertFalse(cached_file.isAlreadyTranslatedTheSame(message_data))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
