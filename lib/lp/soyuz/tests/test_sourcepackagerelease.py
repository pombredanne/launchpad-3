# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test SourcePackageRelease."""

__metaclass__ = type

import transaction
from zope.component import getUtility

from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.testing import (
    TestCaseWithFactory,
    person_logged_in,
    )
from lp.testing.dbuser import dbuser
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )


class TestSourcePackageRelease(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_uploader_no_uploader(self):
        spr = self.factory.makeSourcePackageRelease()
        self.assertIs(None, spr.uploader)

    def test_uploader_dsc_package(self):
        owner = self.factory.makePerson()
        key = self.factory.makeGPGKey(owner)
        spr = self.factory.makeSourcePackageRelease(dscsigningkey=key)
        self.assertEqual(owner, spr.uploader)

    def test_uploader_recipe(self):
        recipe_build = self.factory.makeSourcePackageRecipeBuild()
        recipe = recipe_build.recipe
        spr = self.factory.makeSourcePackageRelease(
            source_package_recipe_build=recipe_build)
        self.assertEqual(recipe_build.requester, spr.uploader)

    def test_user_defined_fields(self):
        release = self.factory.makeSourcePackageRelease(
                user_defined_fields=[
                    ("Python-Version", ">= 2.4"),
                    ("Other", "Bla")])
        self.assertEquals([
            ["Python-Version", ">= 2.4"],
            ["Other", "Bla"]], release.user_defined_fields)

    def test_homepage_default(self):
        # By default, no homepage is set.
        spr = self.factory.makeSourcePackageRelease()
        self.assertEquals(None, spr.homepage)

    def test_homepage_empty(self):
        # The homepage field can be empty.
        spr = self.factory.makeSourcePackageRelease(homepage="")
        self.assertEquals("", spr.homepage)

    def test_homepage_set_invalid(self):
        # As the homepage field is inherited from the DSCFile, the URL
        # does not have to be valid.
        spr = self.factory.makeSourcePackageRelease(homepage="<invalid<url")
        self.assertEquals("<invalid<url", spr.homepage)


class TestSourcePackageReleaseTranslationFeiles(TestCaseWithFactory):
    """Tests for attachTranslationFiles on a different layer."""

    layer = LaunchpadZopelessLayer

    def makeTranslationsLFA(self):
        """Create an LibraryFileAlias containing dummy translation data."""
        test_tar_content = {
            'source/po/foo.pot': 'Foo template',
            'source/po/eo.po': 'Foo translation',
            }
        tarfile_content = LaunchpadWriteTarFile.files_to_string(
            test_tar_content)
        return self.factory.makeLibraryFileAlias(content=tarfile_content)

    def test_attachTranslationFiles__no_translation_sharing(self):
        # If translation sharing is disabled,
        # SourcePackageRelease.attachTranslationFiles() creates a job
        # in the translation import queue.
        spr = self.factory.makeSourcePackageRelease()
        self.assertFalse(spr.sourcepackage.has_sharing_translation_templates)
        lfa = self.makeTranslationsLFA()
        transaction.commit()
        with dbuser('queued'):
            spr.attachTranslationFiles(lfa, True, spr.maintainer)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
                target=spr.sourcepackage).count()
        self.assertEqual(2, entries_in_queue)

    def test_attachTranslationFiles__translation_sharing(self):
        # If translation sharing is enabled,
        # SourcePackageRelease.attachTranslationFiles() only attaches
        # templates.
        spr = self.factory.makeSourcePackageRelease()
        sourcepackage = spr.sourcepackage
        productseries = self.factory.makeProductSeries()
        self.factory.makePOTemplate(productseries=productseries)
        with person_logged_in(sourcepackage.distroseries.owner):
            sourcepackage.setPackaging(
                productseries, sourcepackage.distroseries.owner)
        self.assertTrue(sourcepackage.has_sharing_translation_templates)
        lfa = self.makeTranslationsLFA()
        transaction.commit()
        with dbuser('queued'):
            spr.attachTranslationFiles(lfa, True, spr.maintainer)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries = translation_import_queue.getAllEntries(
                target=sourcepackage)
        self.assertEqual(1, entries.count())
        self.assertTrue(entries[0].path.endswith('.pot'))
