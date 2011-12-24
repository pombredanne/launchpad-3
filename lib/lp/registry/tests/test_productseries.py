# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ProductSeries and ProductSeriesSet."""

__metaclass__ = type

import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login
from lp.services.database.lpstorm import IStore
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.productseries import (
    IProductSeries,
    IProductSeriesSet,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.testing import (
    TestCaseWithFactory,
    WebServiceTestCase,
    )
from lp.testing.matchers import DoesNotSnapshot
from lp.translations.interfaces.translations import (
    TranslationsBranchImportMode,
    )


class ProductSeriesReleasesTestCase(TestCaseWithFactory):
    """Test for ProductSeries.release property."""

    layer = DatabaseFunctionalLayer

    def test_releases(self):
        # The release property returns an iterator of releases ordered
        # by date_released from youngest to oldest.
        series = self.factory.makeProductSeries()
        milestone = self.factory.makeMilestone(
            name='0.0.1', productseries=series)
        release_1 = self.factory.makeProductRelease(milestone=milestone)
        milestone = self.factory.makeMilestone(
            name='0.0.2', productseries=series)
        release_2 = self.factory.makeProductRelease(milestone=milestone)
        self.assertEqual(
            [release_2, release_1], list(series.releases))

    def test_releases_caches_milestone(self):
        # The release's milestone was cached when the release was retrieved.
        milestone = self.factory.makeMilestone(name='0.0.1')
        self.factory.makeProductRelease(milestone=milestone)
        series = milestone.series_target
        IStore(series).invalidate()
        [release] = [release for release in series.releases]
        self.assertStatementCount(0, getattr, release, 'milestone')


class ProductSeriesGetReleaseTestCase(TestCaseWithFactory):
    """Test for ProductSeries.getRelease()."""

    layer = DatabaseFunctionalLayer

    def test_getRelease_match(self):
        # The release is returned when there is a matching release version.
        milestone = self.factory.makeMilestone(name='0.0.1')
        release = self.factory.makeProductRelease(milestone=milestone)
        series = milestone.series_target
        self.assertEqual(release, series.getRelease('0.0.1'))

    def test_getRelease_None(self):
        # None is returned when there is no matching release version.
        milestone = self.factory.makeMilestone(name='0.0.1')
        series = milestone.series_target
        self.assertEqual(None, series.getRelease('0.0.1'))


class TestProductSeriesSetPackaging(TestCaseWithFactory):
    """Test for ProductSeries.setPackaging()."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('admin@canonical.com')

        self.sourcepackagename = self.factory.makeSourcePackageName()

        # Set up productseries.
        self.person = self.factory.makePerson()
        self.product = self.factory.makeProduct(owner=self.person)
        self.dev_focus = self.product.development_focus
        self.product_series = self.factory.makeProductSeries(self.product)

        # Set up distroseries.
        self.distroseries_set = getUtility(IDistroSeriesSet)
        self.distribution_set = getUtility(IDistributionSet)
        self.ubuntu = self.distribution_set.getByName("ubuntu")
        self.debian = self.distribution_set.getByName("debian")
        self.ubuntu_series = self.factory.makeDistroSeries(self.ubuntu)
        self.debian_series = self.factory.makeDistroSeries(self.debian)

    def test_setPackaging_without_publishing_history(self):
        # Fully functional (ubuntu) distributions are prevented from
        # having a packaging entry for a distroseries that does not
        # have a source package publishing history.
        self.assertRaises(
            AssertionError,
            self.product_series.setPackaging,
            self.ubuntu_series, self.sourcepackagename, self.person)

    def test_setPackaging_with_publishing_history(self):
        # Add the source package publishing history to the distroseries
        # so that the packaging can be added successfully.
        self.spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.sourcepackagename,
            distroseries=self.ubuntu_series)
        self.product_series.setPackaging(
            self.ubuntu_series, self.sourcepackagename, self.person)

    def test_setPackaging_not_ubuntu(self):
        # A non-fully-functional distribution does not need a source
        # package publishing history before adding the packaging entry.
        self.product_series.setPackaging(
            self.debian_series, self.sourcepackagename, self.person)

    def makeSourcePackage(self):
        # Create a published sourcepackage for self.ubuntu_series.
        sourcepackage = self.factory.makeSourcePackage(
            distroseries=self.ubuntu_series)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=sourcepackage.sourcepackagename,
            distroseries=self.ubuntu_series)
        return sourcepackage

    def test_setPackaging_two_packagings(self):
        # More than one sourcepackage from the same distroseries
        # can be linked to a productseries.
        sourcepackage_a = self.makeSourcePackage()
        sourcepackage_b = self.makeSourcePackage()
        packaging_a = self.product_series.setPackaging(
            distroseries=self.ubuntu_series,
            sourcepackagename=sourcepackage_a.sourcepackagename,
            owner=self.factory.makePerson())
        packaging_b = self.product_series.setPackaging(
            distroseries=self.ubuntu_series,
            sourcepackagename=sourcepackage_b.sourcepackagename,
            owner=self.factory.makePerson())
        self.assertEqual(
            [packaging_b, packaging_a], list(self.product_series.packagings))

    def test_setPackaging_called_for_existing_multiple_packagings(self):
        # Calling setPackaging for already existing packagings
        # does not have any effect.
        sourcepackage_a = self.makeSourcePackage()
        sourcepackage_b = self.makeSourcePackage()
        packaging_a = self.product_series.setPackaging(
            distroseries=self.ubuntu_series,
            sourcepackagename=sourcepackage_a.sourcepackagename,
            owner=self.factory.makePerson())
        packaging_b = self.product_series.setPackaging(
            distroseries=self.ubuntu_series,
            sourcepackagename=sourcepackage_b.sourcepackagename,
            owner=self.factory.makePerson())
        self.assertEqual(
            packaging_b,
            self.product_series.setPackaging(
                distroseries=self.ubuntu_series,
                sourcepackagename=sourcepackage_b.sourcepackagename,
                owner=self.factory.makePerson()))
        self.assertEqual(
            packaging_a,
            self.product_series.setPackaging(
                distroseries=self.ubuntu_series,
                sourcepackagename=sourcepackage_a.sourcepackagename,
                owner=self.factory.makePerson()))
        self.assertEqual(
            [packaging_b, packaging_a], list(self.product_series.packagings))

    def test_setPackaging__packagings_created_by_sourcepackage(self):
        # Calling setPackaging for already existing packagings
        # created by SourcePackage.setPackaging() does not have any effect.
        sourcepackage_a = self.makeSourcePackage()
        sourcepackage_b = self.makeSourcePackage()
        sourcepackage_a.setPackaging(
            self.product_series, owner=self.factory.makePerson())
        sourcepackage_b.setPackaging(
            self.product_series, owner=self.factory.makePerson())
        packaging_a = sourcepackage_a.packaging
        packaging_b = sourcepackage_b.packaging
        self.assertEqual(
            packaging_b,
            self.product_series.setPackaging(
                distroseries=self.ubuntu_series,
                sourcepackagename=sourcepackage_b.sourcepackagename,
                owner=self.factory.makePerson()))
        self.assertEqual(
            packaging_a,
            self.product_series.setPackaging(
                distroseries=self.ubuntu_series,
                sourcepackagename=sourcepackage_a.sourcepackagename,
                owner=self.factory.makePerson()))
        self.assertEqual(
            [packaging_b, packaging_a], list(self.product_series.packagings))


class TestProductSeriesGetUbuntuTranslationFocusPackage(TestCaseWithFactory):
    """Test for ProductSeries.getUbuntuTranslationFocusPackage."""

    layer = DatabaseFunctionalLayer

    def _makeSourcePackage(self, productseries,
                           series_status=SeriesStatus.EXPERIMENTAL):
        """Make a sourcepckage that packages the productseries."""
        distroseries = self.factory.makeUbuntuDistroSeries(
            status=series_status)
        packaging = self.factory.makePackagingLink(
            productseries=productseries, distroseries=distroseries)
        return packaging.sourcepackage

    def _test_packaged_in_series(
            self, in_translation_focus, in_current_series, in_other_series):
        """Test the given combination of packagings."""
        productseries = self.factory.makeProductSeries()
        package = None
        if in_other_series:
            package = self._makeSourcePackage(productseries)
        if in_current_series:
            package = self._makeSourcePackage(
                productseries, SeriesStatus.FROZEN)
        if in_translation_focus:
            package = self._makeSourcePackage(productseries)
            naked_distribution = removeSecurityProxy(
                package.distroseries.distribution)
            naked_distribution.translation_focus = package.distroseries
        self.assertEqual(
            package,
            productseries.getUbuntuTranslationFocusPackage())

    def test_no_sourcepackage(self):
        self._test_packaged_in_series(
            in_translation_focus=False,
            in_current_series=False,
            in_other_series=False)

    def test_packaged_in_translation_focus(self):
        # The productseries is packaged in the translation focus series
        # and others but only the focus is returned.
        self._test_packaged_in_series(
            in_translation_focus=True,
            in_current_series=True,
            in_other_series=True)

    def test_packaged_in_current_series(self):
        # The productseries is packaged in the current series and others but
        # only the current is returned.
        self._test_packaged_in_series(
            in_translation_focus=False,
            in_current_series=True,
            in_other_series=True)

    def test_packaged_in_other_series(self):
        # The productseries is not packaged in the translation focus or the
        # current series, so that packaging is returned.
        self._test_packaged_in_series(
            in_translation_focus=False,
            in_current_series=False,
            in_other_series=True)


class TestProductSeriesDrivers(TestCaseWithFactory):
    """Test the 'drivers' attribute of a ProductSeries."""

    layer = ZopelessDatabaseLayer

    def _makeProductAndSeries(self, with_project_group=True):
        """Setup Product and a ProductSeries and an optional project group."""
        if with_project_group:
            self.projectgroup = self.factory.makeProject()
        else:
            self.projectgroup = None
        self.product = self.factory.makeProduct(project=self.projectgroup)
        self.series = self.product.getSeries('trunk')

    def test_drivers_nodrivers_group(self):
        # With no drivers set, the project group owner is the driver.
        self._makeProductAndSeries(with_project_group=True)
        self.assertContentEqual(
            [self.projectgroup.owner], self.series.drivers)

    def test_drivers_nodrivers_product(self):
        # With no drivers set and without a project group, the product
        # owner is the driver.
        self._makeProductAndSeries(with_project_group=False)
        self.assertContentEqual(
            [self.product.owner], self.series.drivers)

    def _setDriver(self, object_with_driver):
        """Make a driver for `object_with_driver`, and return the driver."""
        object_with_driver.driver = self.factory.makePerson()
        return object_with_driver.driver

    def test_drivers_group(self):
        # A driver on the group is reported as one of the drivers of the
        # series.
        self._makeProductAndSeries(with_project_group=True)
        group_driver = self._setDriver(self.projectgroup)
        self.assertContentEqual(
            [group_driver], self.series.drivers)

    def test_drivers_group_product(self):
        # The driver on the group and the product are reported as the drivers
        # of the series.
        self._makeProductAndSeries(with_project_group=True)
        group_driver = self._setDriver(self.projectgroup)
        product_driver = self._setDriver(self.product)
        self.assertContentEqual(
            [group_driver, product_driver], self.series.drivers)

    def test_drivers_group_product_series(self):
        # All drivers at all levels are reported as the drivers of the series.
        self._makeProductAndSeries(with_project_group=True)
        group_driver = self._setDriver(self.projectgroup)
        product_driver = self._setDriver(self.product)
        series_driver = self._setDriver(self.series)
        self.assertContentEqual(
            [group_driver, product_driver, series_driver],
            self.series.drivers)

    def test_drivers_product(self):
        # The product driver is the driver if there is no other.
        self._makeProductAndSeries(with_project_group=True)
        product_driver = self._setDriver(self.product)
        self.assertContentEqual(
            [product_driver], self.series.drivers)

    def test_drivers_series(self):
        # If only the series has a driver, the project group owner is
        # is reported, too.
        self._makeProductAndSeries(with_project_group=True)
        series_driver = self._setDriver(self.series)
        self.assertContentEqual(
            [self.projectgroup.owner, series_driver], self.series.drivers)

    def test_drivers_product_series(self):
        self._makeProductAndSeries(with_project_group=True)
        product_driver = self._setDriver(self.product)
        series_driver = self._setDriver(self.series)
        self.assertContentEqual(
            [product_driver, series_driver], self.series.drivers)

    def test_drivers_group_series(self):
        self._makeProductAndSeries(with_project_group=True)
        group_driver = self._setDriver(self.projectgroup)
        series_driver = self._setDriver(self.series)
        self.assertContentEqual(
            [group_driver, series_driver], self.series.drivers)

    def test_drivers_series_nogroup(self):
        # Without a project group, the product owner is reported as driver.
        self._makeProductAndSeries(with_project_group=False)
        series_driver = self._setDriver(self.series)
        self.assertContentEqual(
            [self.product.owner, series_driver], self.series.drivers)

    def test_drivers_product_series_nogroup(self):
        self._makeProductAndSeries(with_project_group=False)
        product_driver = self._setDriver(self.product)
        series_driver = self._setDriver(self.series)
        self.assertContentEqual(
            [product_driver, series_driver], self.series.drivers)

    def test_drivers_product_nogroup(self):
        self._makeProductAndSeries(with_project_group=False)
        product_driver = self._setDriver(self.product)
        self.assertContentEqual(
            [product_driver], self.series.drivers)


class TestProductSeriesSet(TestCaseWithFactory):
    """Test ProductSeriesSet."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestProductSeriesSet, self).setUp()
        self.ps_set = getUtility(IProductSeriesSet)

    def _makeSeriesAndBranch(
            self, import_mode, branch=None, link_branch=True):
        productseries = self.factory.makeProductSeries()
        productseries.translations_autoimport_mode = import_mode
        if branch is None:
            branch = self.factory.makeProductBranch(productseries.product)
        if link_branch:
            productseries.branch = branch
        return (productseries, branch)

    def test_findByTranslationsImportBranch(self):
        productseries, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)

        self.assertContentEqual(
                [productseries],
                self.ps_set.findByTranslationsImportBranch(branch))

    def test_findByTranslationsImportBranch_full_import(self):
        productseries, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.IMPORT_TRANSLATIONS)

        self.assertContentEqual(
                [productseries],
                self.ps_set.findByTranslationsImportBranch(branch))

    def test_findByTranslationsImportBranch_no_autoimport(self):
        productseries, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.NO_IMPORT)

        self.assertContentEqual(
                [],
                self.ps_set.findByTranslationsImportBranch(branch))

    def test_findByTranslationsImportBranch_no_branch(self):
        productseries, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.IMPORT_TEMPLATES, link_branch=False)

        self.assertContentEqual(
                [],
                self.ps_set.findByTranslationsImportBranch(branch))

    def test_findByTranslationsImportBranch_force_import(self):
        productseries, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.NO_IMPORT)

        self.assertContentEqual(
                [productseries],
                self.ps_set.findByTranslationsImportBranch(branch, True))

    def test_findByTranslationsImportBranch_no_branch_force_import(self):
        productseries, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.NO_IMPORT, link_branch=False)

        self.assertContentEqual(
                [],
                self.ps_set.findByTranslationsImportBranch(branch, True))

    def test_findByTranslationsImportBranch_multiple_series(self):
        productseries, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        second_series, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.IMPORT_TEMPLATES, branch=branch)

        self.assertContentEqual(
                [productseries, second_series],
                self.ps_set.findByTranslationsImportBranch(branch))

    def test_findByTranslationsImportBranch_multiple_series_force(self):
        # XXX henninge 2010-03-18 bug=521095: This will fail when the bug
        # fixed. Please update the test accordingly.
        productseries, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        second_series, branch = self._makeSeriesAndBranch(
            TranslationsBranchImportMode.IMPORT_TEMPLATES, branch=branch)

        self.assertContentEqual(
                [productseries, second_series],
                self.ps_set.findByTranslationsImportBranch(branch, True))


class TestProductSeriesReleases(TestCaseWithFactory):
    '''Tests the releases functions for productseries.'''

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductSeriesReleases, self).setUp()
        self.product = self.factory.makeProduct()
        self.productseries = self.factory.makeProductSeries(
                                            product=self.product)

    def test_getLatestRelease(self):
        # getLatestRelease returns the most recent release.
        self.assertIs(None, self.productseries.getLatestRelease())

        release = self.factory.makeProductRelease(
                        product=self.product,
                        productseries=self.productseries)
        self.assertEqual(release, self.productseries.getLatestRelease())

        second_release = self.factory.makeProductRelease(
                                product=self.product,
                                productseries=self.productseries)
        self.assertEqual(
            second_release,
            self.productseries.getLatestRelease())


class ProductSeriesSnapshotTestCase(TestCaseWithFactory):
    """A TestCase for snapshots of productseries."""

    layer = DatabaseFunctionalLayer

    def test_productseries(self):
        """Asserts that fields marked doNotSnapshot are skipped."""
        productseries = self.factory.makeProductSeries()
        skipped = [
            'milestones',
            'all_milestones',
            ]
        self.assertThat(
            productseries,
            DoesNotSnapshot(skipped, IProductSeries))


class TestWebService(WebServiceTestCase):

    def test_translations_autoimport_mode(self):
        """Autoimport mode can be set over Web Service."""
        series = self.factory.makeProductSeries()
        transaction.commit()
        ws_series = self.wsObject(series, series.owner)
        mode = TranslationsBranchImportMode.IMPORT_TRANSLATIONS
        ws_series.translations_autoimport_mode = mode.title
        ws_series.lp_save()
