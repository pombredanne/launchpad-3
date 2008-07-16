# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Distribution."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.archive import ArchivePurpose, IArchiveSet
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


class TestDistributionCurrentReleases(unittest.TestCase):
    """Test for Distribution.getCurrentReleases."""

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
        if name is None:
            name = self.published_package.name
        if distroseries is None:
            distroseries = self.development_series
        self.publisher.getPubSource(
            sourcename=name, status=status,distroseries=distroseries,
            version=version, archive=archive)

    def assertCurrentVersion(self, version, package_name=None):
        if package_name is None:
            package_name = self.published_package.name
        package = self.distribution.getSourcePackage(package_name)
        releases = self.distribution.getCurrentReleases(
            [package.sourcepackagename])
        self.assertEqual(releases[package].version, version)

    def test_one_release(self):
        self.publish('0.9')
        self.assertCurrentVersion('0.9')

    def test_latest_version(self):
        self.publish('0.9')
        self.publish('1.0')
        self.assertCurrentVersion('1.0')

    def test_active_publishing_status(self):
        self.publish('0.9')
        for minor_version, status in enumerate(active_publishing_status):
            latest_version = '1.%s' % minor_version
            self.publish(latest_version, status=status)
            self.assertCurrentVersion(latest_version)

    def test_not_active_publishing_status(self):
        self.publish('0.9')
        for minor_version, status in enumerate(PackagePublishingStatus.items):
            if status in active_publishing_status:
                continue
            self.publish('1.%s' % minor_version, status=status)
            self.assertCurrentVersion('0.9')

    def test_ignore_other_package_names(self):
        self.publish('0.9', name='foo')
        self.publish('1.0', name='bar')
        self.assertCurrentVersion('0.9', package_name='foo')

    def ignore_other_distributions(self):
        series_in_other_distribution = self.factory.makeDistroRelease()
        self.publish('0.9')
        self.publish('1.0', distroseries=series_in_other_distribution)
        self.assertCurrentVersion('0.9')

    def test_which_distroseries_does_not_matter(self):
        self.publish('0.9', distroseries=self.current_series)
        self.publish('1.0', distroseries=self.development_series)
        self.assertCurrentVersion('1.0')

        self.publish('1.1', distroseries=self.current_series)
        self.assertCurrentVersion('1.1')

    def test_ignore_ppa(self):
        ppa_uploader = self.factory.makePerson()
        ppa_archive = getUtility(IArchiveSet).new(
            purpose=ArchivePurpose.PPA, owner=ppa_uploader,
            distribution=self.distribution)
        self.publish('0.9')
        self.publish('1.0', archive=ppa_archive)
        self.assertCurrentVersion('0.9')

    def test_get_multiple(self):
        self.publish('0.9', name='foo')
        self.publish('1.0', name='bar')
        foo_package = self.distribution.getSourcePackage('foo')
        bar_package = self.distribution.getSourcePackage('bar')
        releases = self.distribution.getCurrentReleases(
            [foo_package.sourcepackagename, bar_package.sourcepackagename])
        self.assertEqual(releases[foo_package].version, '0.9')
        self.assertEqual(releases[bar_package].version, '1.0')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDistributionCurrentReleases))
    return suite
