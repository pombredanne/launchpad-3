# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import logging

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from lp.translations.scripts.migrate_current_flag import (
    MigrateCurrentFlagProcess,
    TranslationMessageImportedFlagUpdater,
    )


class TestMigrateCurrentFlag(TestCaseWithFactory):
    """Test current-flag migration script."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # This test needs the privileges of rosettaadmin (to update
        # TranslationMessages) but it also needs to set up test conditions
        # which requires other privileges.
        self.layer.switchDbUser('postgres')
        super(TestMigrateCurrentFlag, self).setUp(user='mark@example.com')
        self.migrate_process = MigrateCurrentFlagProcess(self.layer.txn)

    def test_getProductsWithTemplates_sampledata(self):
        # Sample data already has 3 products with templates.
        sampledata_products = list(
            self.migrate_process.getProductsWithTemplates())
        self.assertEquals(3, len(sampledata_products))

    def test_getProductsWithTemplates_noop(self):
        # Adding a product with no templates doesn't change anything.
        sampledata_products = list(
            self.migrate_process.getProductsWithTemplates())
        self.factory.makeProduct()
        products = self.migrate_process.getProductsWithTemplates()
        self.assertContentEqual(sampledata_products, list(products))

    def test_getProductsWithTemplates_new_template(self):
        # A new product with a template is included.
        sampledata_products = list(
            self.migrate_process.getProductsWithTemplates())
        product = self.factory.makeProduct()
        self.factory.makePOTemplate(productseries=product.development_focus)
        products = self.migrate_process.getProductsWithTemplates()
        self.assertContentEqual(
            sampledata_products + [product], list(products))

    def test_getCurrentNonimportedTranslations_empty(self):
        # For a product with no translations no messages are returned.
        potemplate = self.factory.makePOTemplate()
        results = list(
            self.migrate_process.getCurrentNonimportedTranslations(
                potemplate.productseries.product))
        self.assertContentEqual([], results)

    def test_getCurrentNonimportedTranslations_noncurrent(self):
        # For a product with non-current translations no messages
        # are returned.
        potemplate = self.factory.makePOTemplate()
        potmsgset = self.factory.makePOTMsgSet(
            potemplate=potemplate,
            sequence=1)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        translation = self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, suggestion=True)
        results = list(
            self.migrate_process.getCurrentNonimportedTranslations(
                potemplate.productseries.product))
        self.assertContentEqual([], results)

    def test_getCurrentNonimportedTranslations_current_imported(self):
        # For a product with current, imported translations no messages
        # are returned.
        potemplate = self.factory.makePOTemplate()
        potmsgset = self.factory.makePOTMsgSet(
            potemplate=potemplate,
            sequence=1)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        translation = self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, is_imported=True)
        results = list(
            self.migrate_process.getCurrentNonimportedTranslations(
                potemplate.productseries.product))
        self.assertContentEqual([], results)

    def test_getCurrentNonimportedTranslations_current_nonimported(self):
        # For a product with current, non-imported translations,
        # that translation is returned.
        potemplate = self.factory.makePOTemplate()
        potmsgset = self.factory.makePOTMsgSet(
            potemplate=potemplate,
            sequence=1)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        translation = self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, is_imported=False)
        results = list(
            self.migrate_process.getCurrentNonimportedTranslations(
                potemplate.productseries.product))
        self.assertContentEqual([translation.id], results)


class TestUpdaterLoop(TestCaseWithFactory):
    """Test updater-loop core functionality."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # This test needs the privileges of rosettaadmin (to update
        # TranslationMessages) but it also needs to set up test conditions
        # which requires other privileges.
        self.layer.switchDbUser('postgres')
        super(TestUpdaterLoop, self).setUp(user='mark@example.com')
        self.logger = logging.getLogger("migrate-current-flag")
        self.migrate_loop = TranslationMessageImportedFlagUpdater(
            self.layer.txn, self.logger, [])

    def test_updateTranslationMessages_base(self):
        # Passing in a TranslationMessage.id sets is_imported flag
        # on that message even if it was not set before.
        translation = self.factory.makeTranslationMessage()
        self.assertFalse(translation.is_imported)

        self.migrate_loop._updateTranslationMessages([translation.id])
        self.assertTrue(translation.is_imported)

    def test_updateTranslationMessages_unsetting_imported(self):
        # If there was a previous imported message, it is unset
        # first.
        pofile = self.factory.makePOFile()
        imported = self.factory.makeTranslationMessage(
            pofile=pofile, is_imported=True)
        translation = self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=imported.potmsgset, is_imported=False)
        self.assertTrue(imported.is_imported)
        self.assertFalse(imported.is_current)
        self.assertFalse(translation.is_imported)
        self.assertTrue(translation.is_current)

        self.migrate_loop._updateTranslationMessages([translation.id])
        self.assertFalse(imported.is_imported)
        self.assertTrue(translation.is_imported)
        self.assertTrue(translation.is_current)

    def test_updateTranslationMessages_other_language(self):
        # If there was a previous imported message in another language
        # it is not unset.
        pofile = self.factory.makePOFile()
        pofile_other = self.factory.makePOFile(potemplate=pofile.potemplate)
        imported = self.factory.makeTranslationMessage(
            pofile=pofile_other, is_imported=True)
        translation = self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=imported.potmsgset, is_imported=False)
        self.assertTrue(imported.is_imported)
        self.assertTrue(imported.is_current)
        self.assertFalse(translation.is_imported)
        self.assertTrue(translation.is_current)

        self.migrate_loop._updateTranslationMessages([translation.id])
        self.assertTrue(imported.is_imported)
        self.assertTrue(imported.is_current)
        self.assertTrue(translation.is_imported)
        self.assertTrue(translation.is_current)

    def test_updateTranslationMessages_diverged(self):
        # If there was a previous diverged message, it is not
        # touched.
        pofile = self.factory.makePOFile()
        translation = self.factory.makeTranslationMessage(
            pofile=pofile, is_imported=False)
        diverged_imported = self.factory.makeTranslationMessage(
            pofile=pofile, force_diverged=True, is_imported=True,
            potmsgset=translation.potmsgset)
        self.assertEquals(pofile.potemplate, diverged_imported.potemplate)
        self.assertTrue(diverged_imported.is_imported)
        self.assertTrue(diverged_imported.is_current)

        self.migrate_loop._updateTranslationMessages([translation.id])
        self.assertEquals(pofile.potemplate, diverged_imported.potemplate)
        self.assertTrue(diverged_imported.is_imported)
        self.assertTrue(diverged_imported.is_current)
