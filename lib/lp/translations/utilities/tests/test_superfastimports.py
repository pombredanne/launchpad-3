# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.config import config
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.testing import TestCaseWithFactory
from lp.translations.utilities.translation_common_format import (
    TranslationMessageData,
    )
from lp.translations.utilities.translation_import import (
    ExistingPOFileInDatabase,
    )


class TestSuperFastImports(TestCaseWithFactory):
    """Test how ExistingPOFileInDatabase cache works."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Set up a single POFile in the database to be cached and
        # examined.
        super(TestSuperFastImports, self).setUp()
        self.pofile = self.factory.makePOFile('sr')

    def getTranslationMessageData(self, translationmessage):
        # Convert a TranslationMessage to TranslationMessageData object,
        # which is used during import.
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
        # Make sure current, non-imported messages are properly
        # cached in ExistingPOFileInDatabase.
        current_message = self.factory.makeTranslationMessage(
            pofile=self.pofile, is_imported=False)
        cached_file = ExistingPOFileInDatabase(self.pofile)
        message_data = self.getTranslationMessageData(current_message)
        self.assertFalse(cached_file.isAlreadyImportedTheSame(message_data))
        self.assertTrue(cached_file.isAlreadyTranslatedTheSame(message_data))

    def test_imported_messages(self):
        # Make sure current, imported messages are properly
        # cached in ExistingPOFileInDatabase.
        imported_message = self.factory.makeTranslationMessage(
            pofile=self.pofile, is_imported=True)
        cached_file = ExistingPOFileInDatabase(self.pofile, is_imported=True)
        message_data = self.getTranslationMessageData(imported_message)
        self.assertTrue(cached_file.isAlreadyImportedTheSame(message_data))
        self.assertTrue(cached_file.isAlreadyTranslatedTheSame(message_data))

    def test_inactive_messages(self):
        # Make sure non-current messages (i.e. suggestions) are
        # not cached in ExistingPOFileInDatabase.
        inactive_message = self.factory.makeTranslationMessage(
            pofile=self.pofile, suggestion=True)
        cached_file = ExistingPOFileInDatabase(self.pofile)
        message_data = self.getTranslationMessageData(inactive_message)
        self.assertFalse(cached_file.isAlreadyImportedTheSame(message_data))
        self.assertFalse(cached_file.isAlreadyTranslatedTheSame(message_data))

    def test_query_timeout(self):
        # Test that super-fast-imports doesn't cache anything when it hits
        # a timeout.

        # Override the config option to force a timeout error.
        new_config = ("""
            [poimport]
            statement_timeout: timeout
            """)
        config.push('super_fast_timeout', new_config)

        # Add a message that would otherwise be cached (see other tests).
        current_message = self.factory.makeTranslationMessage(
            pofile=self.pofile, is_imported=False)
        message_data = self.getTranslationMessageData(current_message)
        cached_file = ExistingPOFileInDatabase(self.pofile)
        self.assertFalse(cached_file.isAlreadyTranslatedTheSame(message_data))

        # Restore the old configuration.
        config.pop('super_fast_timeout')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
