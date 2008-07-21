# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Distribution."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.interfaces.archive import ArchivePurpose, IArchiveSet
from canonical.launchpad.interfaces.distroseriessourcepackagerelease import (
    IDistroSeriesSourcePackageRelease)
from canonical.launchpad.interfaces.publishing import (
    active_publishing_status, PackagePublishingStatus)
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing import LaunchpadFunctionalLayer


class TestDistroSeriesCurrentSourceReleases(unittest.TestCase):
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
        """Assert the the current version of a package is the expected one.

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDistroSeriesCurrentSourceReleases))
    return suite
