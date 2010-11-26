# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the is_current_ubuntu to is_current_upstream migration.

This test and the script it is testing lives in two worlds because it migrates
data from the old model to the new. Since the naming and meaning of the flags
have changed, the code and comments may sometimes be confusing. Here a
little guide:

Old model                            New Model
---------                            ---------
The is_current flag marks a          The is_current_ubuntu flag marks a
translation as being currently in    translation as being currently used in
use in the project or package        the Ubuntu source package that the
that the POFile of this translation  translation is linked to.
belongs to.

The is_imported flag marks a         The is_current_upstream flag marks a
translation as having been imported  translation as being currently used in
from an external source into this    the upstream project that this
project or source package.           translation is linked to.

Translations from projects and       Translations are shared between upstream
source packages are not shared.      projects and source packages.

Ubuntu source packages can live quite happily in the new world because the
meaning of the flag "is_current_ubuntu", which used to be called "is_current",
remains the same for them.

Projects on the other hand could lose all their translations because their
former "current" translation would then be "current in the source package"
but not in the project itself. For this reason, all current messages in
projects need to get their "is_current_upstream" flag set. This may
currently not be the case because it used to be called "is_imported" and
the messages may not have been imported from an external source.

The factory creates POTemplates and POFiles in projects if not directed
otherwise, which is what we need in this test. When setting up tests, though,
the old model has to be mimicked by setting "is_current_ubuntu" to True
although the translation is meant to be "is_current_upstream". This script
is about fixing exactly that, so don't get confused when reading the tests.
"""

__metaclass__ = type

import logging

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from lp.translations.scripts.migrate_current_flag import (
    MigrateCurrentFlagProcess,
    TranslationMessageUpstreamFlagUpdater,
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

    def test_getTranslationsToMigrate_empty(self):
        # For a product with no translations no messages are returned.
        potemplate = self.factory.makePOTemplate()
        results = list(
            self.migrate_process.getTranslationsToMigrate(
                potemplate.productseries.product))
        self.assertContentEqual([], results)

    def test_getTranslationsToMigrate_noncurrent(self):
        # For a product with non-current translations no messages
        # are returned.
        potemplate = self.factory.makePOTemplate()
        potmsgset = self.factory.makePOTMsgSet(
            potemplate=potemplate,
            sequence=1)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        self.factory.makeSuggestion(pofile=pofile, potmsgset=potmsgset)
        results = list(
            self.migrate_process.getTranslationsToMigrate(
                potemplate.productseries.product))
        self.assertContentEqual([], results)

    def test_getTranslationsToMigrate_current_upstream(self):
        # For a product with both flasg set, no messages are returned.
        potemplate = self.factory.makePOTemplate()
        potmsgset = self.factory.makePOTMsgSet(
            potemplate=potemplate,
            sequence=1)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset)
        translation.is_current_ubuntu = True
        results = list(
            self.migrate_process.getTranslationsToMigrate(
                potemplate.productseries.product))
        self.assertContentEqual([], results)

    def test_getTranslationsToMigrate_current_nonupstream(self):
        # For a product with current, non-upstream translations,
        # that translation is returned.
        potemplate = self.factory.makePOTemplate()
        potmsgset = self.factory.makePOTMsgSet(
            potemplate=potemplate,
            sequence=1)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        translation = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset)
        translation.is_current_ubuntu = True
        results = list(
            self.migrate_process.getTranslationsToMigrate(
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
        self.migrate_loop = TranslationMessageUpstreamFlagUpdater(
            self.layer.txn, self.logger, [])

    def test_updateTranslationMessages_base(self):
        # Passing in a TranslationMessage.id sets is_current_upstream flag
        # on that message even if it was not set before.
        translation = self.factory.makeSuggestion()
        translation.is_current_ubuntu = True
        self.assertFalse(translation.is_current_upstream)

        self.migrate_loop._updateTranslationMessages([translation.id])
        self.assertTrue(translation.is_current_upstream)

    def test_updateTranslationMessages_unsetting_upstream(self):
        # If there was a previous upstream message, it is unset
        # first.
        pofile = self.factory.makePOFile()
        upstream = self.factory.makeCurrentTranslationMessage(pofile=pofile)
        ubuntu = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=upstream.potmsgset)
        ubuntu.is_current_ubuntu = True
        self.assertTrue(upstream.is_current_upstream)
        self.assertFalse(upstream.is_current_ubuntu)
        self.assertFalse(ubuntu.is_current_upstream)

        self.migrate_loop._updateTranslationMessages([ubuntu.id])
        self.assertFalse(upstream.is_current_upstream)
        self.assertTrue(ubuntu.is_current_upstream)
        self.assertTrue(ubuntu.is_current_ubuntu)

    def test_updateTranslationMessages_other_language(self):
        # If there was a previous upstream message in another language
        # it is not unset.
        pofile = self.factory.makePOFile()
        pofile_other = self.factory.makePOFile(potemplate=pofile.potemplate)
        upstream = self.factory.makeCurrentTranslationMessage(
            pofile=pofile_other)
        upstream.is_current_ubuntu = True
        ubuntu = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=upstream.potmsgset)
        ubuntu.is_current_ubuntu = True
        self.assertTrue(upstream.is_current_upstream)
        self.assertTrue(upstream.is_current_ubuntu)
        self.assertFalse(ubuntu.is_current_upstream)

        self.migrate_loop._updateTranslationMessages([ubuntu.id])
        self.assertTrue(upstream.is_current_upstream)
        self.assertTrue(upstream.is_current_ubuntu)
        self.assertTrue(ubuntu.is_current_upstream)
        self.assertTrue(ubuntu.is_current_ubuntu)

    def test_updateTranslationMessages_diverged(self):
        # If there was a previous diverged message, it is not
        # touched.
        pofile = self.factory.makePOFile()
        ubuntu = self.factory.makeSuggestion(pofile=pofile)
        ubuntu.is_current_ubuntu = True
        diverged_upstream = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, diverged=True, potmsgset=ubuntu.potmsgset)
        diverged_upstream.is_current_ubuntu = True
        self.assertEquals(pofile.potemplate, diverged_upstream.potemplate)
        self.assertTrue(diverged_upstream.is_current_upstream)

        self.migrate_loop._updateTranslationMessages([ubuntu.id])
        self.assertEquals(pofile.potemplate, diverged_upstream.potemplate)
        self.assertTrue(diverged_upstream.is_current_upstream)
        self.assertTrue(diverged_upstream.is_current_ubuntu)
