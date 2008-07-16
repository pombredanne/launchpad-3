# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Distribution."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.archive import ArchivePurpose, IArchiveSet
from canonical.launchpad.interfaces.distributionsourcepackagerelease import (
    IDistributionSourcePackageRelease)
from canonical.launchpad.interfaces.distroseries import (
    DistroSeriesStatus, IDistroSeriesSet)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.publishing import (
    active_publishing_status, PackagePublishingStatus)
from canonical.launchpad.interfaces.sourcepackagename import (
    ISourcePackageNameSet)
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing import LaunchpadFunctionalLayer


class TestDistributionCurrentSourceReleases(unittest.TestCase):
    """Test for Distribution.getCurrentSourceReleases."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        person_with_gpg_key = getUtility(IPersonSet).getByEmail(
            'foo.bar@canonical.com')
        self.publisher = SoyuzTestPublisher()
        self.publisher.person = person_with_gpg_key
        self.distribution = self.factory.makeDistribution()
        self.current_series = self.factory.makeDistroRelease(
            self.distribution, '1.0', status=DistroSeriesStatus.CURRENT)
        self.development_series = self.factory.makeDistroRelease(
            self.distribution, '2.0', status=DistroSeriesStatus.DEVELOPMENT,
            parent_series=self.current_series)
        self.published_package = self.distribution.getSourcePackage(
            getUtility(ISourcePackageNameSet).getOrCreateByName(
                'published-package'))

    def publish(self, version, name=None,
                status=PackagePublishingStatus.PUBLISHED, distroseries=None,
                archive=None):
        """Publish a new version.

        If name isn't specified, the package we set up in setUp() is
        used.

        If distroseries, the development series we set up in
        setUp() is used.
        """
        if name is None:
            name = self.published_package.name
        if distroseries is None:
            distroseries = self.development_series
        self.publisher.getPubSource(
            sourcename=name, status=status,distroseries=distroseries,
            version=version, archive=archive)

    def assertCurrentVersion(self, expected_version, package_name=None):
        """Assert the the current version of a package is the expected one.

        It uses getCurrentSourceReleases() to get the version.

        If package_name isn't specified, self.published_package is used.
        """
        if package_name is None:
            package_name = self.published_package.name
        package = self.distribution.getSourcePackage(package_name)
        releases = self.distribution.getCurrentSourceReleases(
            [package.sourcepackagename])
        self.assertEqual(releases[package].version, expected_version)

    def test_one_release(self):
        # If there is one published version, that one will be returned.
        self.publish('0.9')
        self.assertCurrentVersion('0.9')

    def test_return_value(self):
        # getCurrentSourceReleases() returns a dict. The corresponding
        # DistributionSourcePackage is used as the key, with
        # DistributionSourcePackages as the values.
        self.publish('0.9')
        releases = self.distribution.getCurrentSourceReleases(
            [self.published_package.sourcepackagename])
        self.assertTrue(self.published_package in releases)
        self.assertTrue(IDistributionSourcePackageRelease.providedBy(
            releases[self.published_package]))

    def test_latest_version(self):
        # If more than one version is published, the latest one is
        # returned.
        self.publish('0.9')
        self.publish('1.0')
        self.assertCurrentVersion('1.0')

    def test_active_publishing_status(self):
        # Every status defined in active_publishing_status is considered
        # when checking for the current release.
        self.publish('0.9')
        for minor_version, status in enumerate(active_publishing_status):
            latest_version = '1.%s' % minor_version
            self.publish(latest_version, status=status)
            self.assertCurrentVersion(latest_version)

    def test_not_active_publishing_status(self):
        # Every status not defined in active_publishing_status is
        # ignored when checking for the current release.
        self.publish('0.9')
        for minor_version, status in enumerate(PackagePublishingStatus.items):
            if status in active_publishing_status:
                continue
            self.publish('1.%s' % minor_version, status=status)
            self.assertCurrentVersion('0.9')

    def test_ignore_other_package_names(self):
        # Packages with different names don't affect the returned
        # version.
        self.publish('0.9', name='foo')
        self.publish('1.0', name='bar')
        self.assertCurrentVersion('0.9', package_name='foo')

    def ignore_other_distributions(self):
        # Packages with the same name in other distributions don't
        # affect the returned version.
        series_in_other_distribution = self.factory.makeDistroRelease()
        self.publish('0.9')
        self.publish('1.0', distroseries=series_in_other_distribution)
        self.assertCurrentVersion('0.9')

    def test_which_distroseries_does_not_matter(self):
        # When checking for the current release, we only care about the
        # version numbers. We don't care whether the version is
        # published in a earlier or later release.
        self.publish('0.9', distroseries=self.current_series)
        self.publish('1.0', distroseries=self.development_series)
        self.assertCurrentVersion('1.0')

        self.publish('1.1', distroseries=self.current_series)
        self.assertCurrentVersion('1.1')

    def test_ignore_ppa(self):
        # PPA packages having the same name don't affect the returned
        # version.
        ppa_uploader = self.factory.makePerson()
        ppa_archive = getUtility(IArchiveSet).new(
            purpose=ArchivePurpose.PPA, owner=ppa_uploader,
            distribution=self.distribution)
        self.publish('0.9')
        self.publish('1.0', archive=ppa_archive)
        self.assertCurrentVersion('0.9')

    def test_get_multiple(self):
        # getCurrentSourceReleases() allows you to get information about
        # the current release for multiple packages at the same time.
        # This is done using a single DB query, making it more efficient
        # than using IDistributionSource.currentrelease.
        self.publish('0.9', name='foo')
        self.publish('1.0', name='bar')
        foo_package = self.distribution.getSourcePackage('foo')
        bar_package = self.distribution.getSourcePackage('bar')
        releases = self.distribution.getCurrentSourceReleases(
            [foo_package.sourcepackagename, bar_package.sourcepackagename])
        self.assertEqual(releases[foo_package].version, '0.9')
        self.assertEqual(releases[bar_package].version, '1.0')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDistributionCurrentSourceReleases))
    return suite
