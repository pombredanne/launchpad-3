# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Unit tests for `TranslatableMessage`."""

__metaclass__ = type

from unittest import TestLoader
import transaction

from lp.testing import TestCaseWithFactory
from lp.translations.model.translatablemessage import TranslatableMessage
from canonical.testing import LaunchpadZopelessLayer


class TestTranslatableMessage(TestCaseWithFactory):
    """Tests for `TranslationMessage.findIdenticalMessage`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up test situation.

        Arranges for a `ProductSeries` with `POTemplate` and
        `POTMsgSet`, as well as a Esperanto translation.
        """
        super(TestTranslatableMessage, self).setUp()
        self.product = self.factory.makeProduct()
        self.product.official_rosetta = True
        self.trunk = self.product.getSeries('trunk')
        self.potemplate = self.factory.makePOTemplate(
            productseries=self.trunk, name="shared")
        self.potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.potemplate, singular='foo', sequence=1)
        self.pofile = self.factory.makePOFile(
            potemplate=self.potemplate, language_code='eo')

    def _createTranslation(self, translation, is_current=False,
                           is_imported=False, is_diverged=False):
        is_suggestion = not (is_current or is_imported or is_diverged)
        return self.factory.makeTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            translations=[translation],
            suggestion=is_suggestion,
            is_imported=is_imported,
            force_diverged=is_diverged)

    def test_sequence(self):
        # After instantiation, the sequence number from the potmsgset is
        # available.
        message = TranslatableMessage(self.potmsgset, self.pofile)
        self.assertEqual(1, message.sequence)

    def test_isObsolete(self):
        # A message is obsolete if the sequence number is 0.
        message = TranslatableMessage(self.potmsgset, self.pofile)
        self.assertFalse(message.isObsolete())

        self.potmsgset.setSequence(self.potemplate, 0)
        message = TranslatableMessage(self.potmsgset, self.pofile)
        self.assertTrue(message.isObsolete())

    def test_isCurrentDiverged(self):
        translation = self._createTranslation('bar',
                                              is_current=True,
                                              is_diverged=True)
        message = TranslatableMessage(self.potmsgset, self.pofile)
        self.assertTrue(message.isCurrentDiverged())

    def test_isCurrentEmpty(self):
        translation = self._createTranslation('', is_current=True)
        message = TranslatableMessage(self.potmsgset, self.pofile)
        self.assertTrue(message.isCurrentEmpty())

    def test_isCurrentImported(self):
        translation = self._createTranslation('bar',
                                              is_current=True,
                                              is_imported=True)
        message = TranslatableMessage(self.potmsgset, self.pofile)
        self.assertTrue(message.isCurrentImported())

    def test_getCurrentTranslation(self):
        translation = self._createTranslation('bar', is_current=True)
        message = TranslatableMessage(self.potmsgset, self.pofile)
        current = message.getCurrentTranslation()
        self.assertEqual(translation, current)

    def test_getImportedTranslation(self):
        translation = self._createTranslation('bar', is_imported=True)

        message = TranslatableMessage(self.potmsgset, self.pofile)
        imported = message.getImportedTranslation()
        self.assertEqual(translation, imported)

    def test_getSharedTranslation(self):
        translation = self._createTranslation('bar', is_current=True)
        message = TranslatableMessage(self.potmsgset, self.pofile)
        shared = message.getSharedTranslation()
        self.assertEqual(translation, shared)

    def test_getSuggestions(self):
        suggestion1 = self._createTranslation('bar1')
        suggestion2 = self._createTranslation('bar2')
        message = TranslatableMessage(self.potmsgset, self.pofile)
        suggestions = message.getSuggestions(False)
        self.assertContentEqual([suggestion1, suggestion2], suggestions)

    def test_getExternalTranslations(self):
        # Create a potmsgset with the same msg id in another product and
        # pull its translations in as an external translations.
        external_potemplate = self.factory.makePOTemplate()
        external_potemplate.productseries.product.official_rosetta = True
        external_potmsgset = self.factory.makePOTMsgSet(
            potemplate=external_potemplate, singular='foo', sequence=1)
        external_pofile = self.factory.makePOFile(
            potemplate=external_potemplate, language_code='eo')

        external_current = self.factory.makeTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            translations=['external_bar'])
        external_imported = self.factory.makeTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            translations=['external_bar_imported'],
            is_imported=True)

        message = TranslatableMessage(self.potmsgset, self.pofile)
        externals = message.getExternalTranslations()
        self.assertContentEqual([external_current, external_imported], externals)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
