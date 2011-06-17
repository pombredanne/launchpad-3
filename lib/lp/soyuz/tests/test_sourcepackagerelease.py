# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test SourcePackageRelease."""

__metaclass__ = type

import transaction
from zope.component import getUtility

from canonical.testing.layers import (
    ZopelessDatabaseLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    )
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.enums import (
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.scripts.packagecopier import do_copy
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


class TestSourcePackageReleaseGetBuildByArch(TestCaseWithFactory):
    """Tests for SourcePackageRelease.getBuildByArch()."""

    layer = ZopelessDatabaseLayer

    def test_can_find_build_in_derived_distro_parent(self):
        # If a derived distribution inherited its binaries from its
        # parent then getBuildByArch() should look in the parent to find
        # the build.
        dsp = self.factory.makeDistroSeriesParent()
        parent_archive = dsp.parent_series.main_archive

        # Create a built, published package in the parent archive.
        spr = self.factory.makeSourcePackageRelease(
            architecturehintlist='any')
        parent_source_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr, archive=parent_archive,
            distroseries=dsp.parent_series)
        das = self.factory.makeDistroArchSeries(
            distroseries=dsp.parent_series, supports_virtualized=True)
        orig_build = spr.createBuild(
            das, PackagePublishingPocket.RELEASE, parent_archive,
            status=BuildStatus.FULLYBUILT)
        bpr = self.factory.makeBinaryPackageRelease(build=orig_build)
        parent_binary_pub = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr, distroarchseries=das,
            archive=parent_archive)

        # Make an architecture in the derived series with the same
        # archtag as the parent.
        das_derived = self.factory.makeDistroArchSeries(
            dsp.derived_series, architecturetag=das.architecturetag,
            processorfamily=das.processorfamily, supports_virtualized=True)
        # Now copy the package to the derived series, with binary.
        derived_archive = dsp.derived_series.main_archive
        getUtility(ISourcePackageFormatSelectionSet).add(
            dsp.derived_series, SourcePackageFormat.FORMAT_1_0)

        do_copy(
            [parent_source_pub], derived_archive, dsp.derived_series,
            PackagePublishingPocket.RELEASE, include_binaries=True,
            check_permissions=False)

        # Searching for the build in the derived series architecture
        # should automatically pick it up from the parent.
        found_build = spr.getBuildByArch(das_derived, derived_archive)
        self.assertEqual(orig_build, found_build)


class TestSourcePackageReleaseTranslationFiles(TestCaseWithFactory):
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
