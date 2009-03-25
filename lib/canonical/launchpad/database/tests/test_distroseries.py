# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Distribution."""

__metaclass__ = type

import unittest

import transaction

from zope.component import getUtility

from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.interfaces.archive import ArchivePurpose, IArchiveSet
from canonical.launchpad.interfaces.distroseries import (
    IDistroSeriesSet, NoSuchDistroSeries)
from canonical.launchpad.interfaces.distroseriessourcepackagerelease import (
    IDistroSeriesSourcePackageRelease)
from canonical.launchpad.interfaces.publishing import (
    active_publishing_status, PackagePublishingPocket,
    PackagePublishingStatus)
from canonical.launchpad.testing import TestCase, TestCaseWithFactory
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)


class TestDistroSeriesCurrentSourceReleases(TestCase):
    """Test for DistroSeries.getCurrentSourceReleases()."""

    layer = LaunchpadFunctionalLayer
    release_interface = IDistroSeriesSourcePackageRelease

    def setUp(self):
        # Log in as an admin, so that we can create distributions.
        login('foo.bar@canonical.com')
        self.publisher = SoyuzTestPublisher()
        self.factory = self.publisher.factory
        self.development_series = self.publisher.setUpDefaultDistroSeries()
        self.distribution = self.development_series.distribution
        self.published_package = self.test_target.getSourcePackage(
            self.publisher.default_package_name)
        login(ANONYMOUS)

    @property
    def test_target(self):
        return self.development_series

    def assertCurrentVersion(self, expected_version, package_name=None):
        """Assert the current version of a package is the expected one.

        It uses getCurrentSourceReleases() to get the version.

        If package_name isn't specified, the test publisher's default
        name is used.
        """
        if package_name is None:
            package_name = self.publisher.default_package_name
        package = self.test_target.getSourcePackage(package_name)
        releases = self.test_target.getCurrentSourceReleases(
            [package.sourcepackagename])
        self.assertEqual(releases[package].version, expected_version)

    def test_one_release(self):
        # If there is one published version, that one will be returned.
        self.publisher.getPubSource(version='0.9')
        self.assertCurrentVersion('0.9')

    def test_return_value(self):
        # getCurrentSourceReleases() returns a dict. The corresponding
        # source package is used as the key, with
        # a DistroSeriesSourcePackageRelease as the values.
        self.publisher.getPubSource(version='0.9')
        releases = self.test_target.getCurrentSourceReleases(
            [self.published_package.sourcepackagename])
        self.assertTrue(self.published_package in releases)
        self.assertTrue(self.release_interface.providedBy(
            releases[self.published_package]))

    def test_latest_version(self):
        # If more than one version is published, the latest one is
        # returned.
        self.publisher.getPubSource(version='0.9')
        self.publisher.getPubSource(version='1.0')
        self.assertCurrentVersion('1.0')

    def test_active_publishing_status(self):
        # Every status defined in active_publishing_status is considered
        # when checking for the current release.
        self.publisher.getPubSource(version='0.9')
        for minor_version, status in enumerate(active_publishing_status):
            latest_version = '1.%s' % minor_version
            self.publisher.getPubSource(version=latest_version, status=status)
            self.assertCurrentVersion(latest_version)

    def test_not_active_publishing_status(self):
        # Every status not defined in active_publishing_status is
        # ignored when checking for the current release.
        self.publisher.getPubSource(version='0.9')
        for minor_version, status in enumerate(PackagePublishingStatus.items):
            if status in active_publishing_status:
                continue
            self.publisher.getPubSource(
                version='1.%s' % minor_version, status=status)
            self.assertCurrentVersion('0.9')

    def test_ignore_other_package_names(self):
        # Packages with different names don't affect the returned
        # version.
        self.publisher.getPubSource(version='0.9', sourcename='foo')
        self.publisher.getPubSource(version='1.0', sourcename='bar')
        self.assertCurrentVersion('0.9', package_name='foo')

    def ignore_other_distributions(self):
        # Packages with the same name in other distributions don't
        # affect the returned version.
        series_in_other_distribution = self.factory.makeDistroRelease()
        self.publisher.getPubSource(version='0.9')
        self.publisher.getPubSource(
            version='1.0', distroseries=series_in_other_distribution)
        self.assertCurrentVersion('0.9')

    def test_ignore_ppa(self):
        # PPA packages having the same name don't affect the returned
        # version.
        ppa_uploader = self.factory.makePerson()
        ppa_archive = getUtility(IArchiveSet).new(
            purpose=ArchivePurpose.PPA, owner=ppa_uploader,
            distribution=self.distribution)
        self.publisher.getPubSource(version='0.9')
        self.publisher.getPubSource(version='1.0', archive=ppa_archive)
        self.assertCurrentVersion('0.9')

    def test_get_multiple(self):
        # getCurrentSourceReleases() allows you to get information about
        # the current release for multiple packages at the same time.
        # This is done using a single DB query, making it more efficient
        # than using IDistributionSource.currentrelease.
        self.publisher.getPubSource(version='0.9', sourcename='foo')
        self.publisher.getPubSource(version='1.0', sourcename='bar')
        foo_package = self.distribution.getSourcePackage('foo')
        bar_package = self.distribution.getSourcePackage('bar')
        releases = self.distribution.getCurrentSourceReleases(
            [foo_package.sourcepackagename, bar_package.sourcepackagename])
        self.assertEqual(releases[foo_package].version, '0.9')
        self.assertEqual(releases[bar_package].version, '1.0')


class TestDistroSeriesSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def _get_translatables(self):
        distro_series_set = getUtility(IDistroSeriesSet)
        # Get translatables as a sequence of names of the series.
        return sorted(
            [series.name for series in distro_series_set.translatables()])

    def _ref_translatables(self, expected=None):
        # Return the reference value, merged with expected data.
        if expected is None:
            return self.ref_translatables
        if isinstance(expected, list):
            return sorted(self.ref_translatables + expected)
        return sorted(self.ref_translatables + [expected])

    def test_translatables(self):
        # translatables() returns all distroseries that have potemplates
        # and are not set to "hide all translations".
        # See whatever distroseries sample data already has.
        self.ref_translatables = self._get_translatables()

        new_distroseries = (
            self.factory.makeDistroRelease(name=u"sampleseries"))
        new_distroseries.hide_all_translations = False
        transaction.commit()
        translatables = self._get_translatables()
        self.failUnlessEqual(
            translatables, self._ref_translatables(),
            "A newly created distroseries should not be translatable but "
            "translatables() returns %r instead of %r." % (
                translatables, self._ref_translatables())
            )

        new_sourcepackagename = self.factory.makeSourcePackageName()
        new_potemplate = self.factory.makePOTemplate(
            distroseries=new_distroseries,
            sourcepackagename=new_sourcepackagename)
        transaction.commit()
        translatables = self._get_translatables()
        self.failUnlessEqual(
            translatables, self._ref_translatables(u"sampleseries"),
            "After assigning a PO template, a distroseries should be "
            "translatable but translatables() returns %r instead of %r." % (
                translatables,
                self._ref_translatables(u"sampleseries"))
            )

        new_distroseries.hide_all_translations = True
        transaction.commit()
        translatables = self._get_translatables()
        self.failUnlessEqual(
            translatables, self._ref_translatables(),
            "After hiding all translation, a distroseries should not be "
            "translatable but translatables() returns %r instead of %r." % (
                translatables, self._ref_translatables()))

    def test_fromSuite_release_pocket(self):
        series = self.factory.makeDistroRelease()
        result = getUtility(IDistroSeriesSet).fromSuite(
            series.distribution, series.name)
        self.assertEqual((series, PackagePublishingPocket.RELEASE), result)

    def test_fromSuite_non_release_pocket(self):
        series = self.factory.makeDistroRelease()
        pocket = PackagePublishingPocket.BACKPORTS
        suite = '%s-backports' % series.name
        result = getUtility(IDistroSeriesSet).fromSuite(
            series.distribution, suite)
        self.assertEqual((series, PackagePublishingPocket.BACKPORTS), result)

    def test_fromSuite_no_such_series(self):
        distribution = self.factory.makeDistribution()
        self.assertRaises(
            NoSuchDistroSeries,
            getUtility(IDistroSeriesSet).fromSuite,
            distribution, 'doesntexist')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
