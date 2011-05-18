# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of DistributionSourcePackageRelease."""

from testtools.matchers import LessThan
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeriesSet
from lp.soyuz.model.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


class TestDistributionSourcePackageRelease(TestCaseWithFactory):
    """Tests for DistributionSourcePackageRelease."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionSourcePackageRelease, self).setUp()
        self.sourcepackagerelease = self.factory.makeSourcePackageRelease()
        self.distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=self.sourcepackagerelease.sourcepackage.distroseries)

    def makeBinaryPackageRelease(self, name=None):
        if name is None:
            name = self.factory.makeBinaryPackageName()
        bp_build = self.factory.makeBinaryPackageBuild(
            source_package_release=self.sourcepackagerelease,
            distroarchseries=self.distroarchseries)
        bp_release = self.factory.makeBinaryPackageRelease(
            build=bp_build, binarypackagename=name)
        sourcepackagename = self.sourcepackagerelease.sourcepackagename
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename,
            sourcepackagerelease=self.sourcepackagerelease,
            distroseries=self.sourcepackagerelease.sourcepackage.distroseries,
            status=PackagePublishingStatus.PUBLISHED)
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bp_release,
            distroarchseries=self.distroarchseries)

    def test_sample_binary_packages__no_releases(self):
        # If no binary releases exist,
        # DistributionSourcePackageRelease.sample_binary_packages is empty.
        distribution = self.distroarchseries.distroseries.distribution
        dsp_release = DistributionSourcePackageRelease(
            distribution, self.sourcepackagerelease)
        self.assertEqual([], dsp_release.sample_binary_packages)

    def test_sample_binary_packages__one_release(self):
        # If a binary release exists,
        # DistributionSourcePackageRelease.sample_binary_packages
        # returns it.
        self.makeBinaryPackageRelease(
            self.factory.makeBinaryPackageName(name='binary-package'))
        distribution = self.distroarchseries.distroseries.distribution
        dsp_release = DistributionSourcePackageRelease(
            distribution, self.sourcepackagerelease)
        self.assertEqual(
            ['binary-package'],
            [release.name for release in dsp_release.sample_binary_packages])

    def test_sample_binary_packages__two_releases_one_binary_package(self):
        # If two binary releases with the same name exist,
        # DistributionSourcePackageRelease.sample_binary_packages
        # returns only one.
        name = self.factory.makeBinaryPackageName(name='binary-package')
        self.makeBinaryPackageRelease(name)
        self.makeBinaryPackageRelease(name)
        distribution = self.distroarchseries.distroseries.distribution
        dsp_release = DistributionSourcePackageRelease(
            distribution, self.sourcepackagerelease)
        self.assertEqual(
            ['binary-package'],
            [release.name for release in dsp_release.sample_binary_packages])

    def test_sample_binary_packages__two_release_two_binary_packages(self):
        # If a two binary releases with different names exist,
        # DistributionSourcePackageRelease.sample_binary_packages
        # returns both.
        self.makeBinaryPackageRelease(
            self.factory.makeBinaryPackageName(name='binary-package'))
        self.makeBinaryPackageRelease(
            self.factory.makeBinaryPackageName(name='binary-package-2'))
        distribution = self.distroarchseries.distroseries.distribution
        dsp_release = DistributionSourcePackageRelease(
            distribution, self.sourcepackagerelease)
        self.assertEqual(
            ['binary-package', 'binary-package-2'],
            [release.name for release in dsp_release.sample_binary_packages])

    def updateDistroSeriesPackageCache(self):
        # Create DistroSeriesPackageCache records for new binary
        # packages.
        #
        # SoyuzTestPublisher.updateDistroSeriesPackageCache() creates
        # a DistroSeriesPackageCache record for the new binary package.
        # The method closes the current DB connection, making references
        # to DB objects in other DB objects unusable. Starting with
        # the distroarchseries, we can create new, valid, instances of
        # objects required later in the test again.
        # of the objects we need later.
        sourcepackagename = self.sourcepackagerelease.sourcepackagename
        publisher = SoyuzTestPublisher()
        publisher.updateDistroSeriesPackageCache(
            self.distroarchseries.distroseries)
        self.distroarchseries = getUtility(IDistroArchSeriesSet).get(
            self.distroarchseries.id)
        distribution = self.distroarchseries.distroseries.distribution
        releases = distribution.getCurrentSourceReleases([sourcepackagename])
        [(distribution_sourcepackage, dsp_release)] = releases.items()
        self.sourcepackagerelease = dsp_release.sourcepackagerelease
        return dsp_release

    def test_sample_binary_packages__constant_number_sql_queries(self):
        # Retrieving
        # DistributionSourcePackageRelease.sample_binary_packages and
        # accessing the property "summary" of its items requires a
        # constant number of SQL queries, regardless of the number
        # of existing binary package releases.
        self.makeBinaryPackageRelease()
        dsp_release = self.updateDistroSeriesPackageCache()
        with StormStatementRecorder() as recorder:
            for dsp_package in dsp_release.sample_binary_packages:
                dsp_package.summary
        self.assertThat(recorder, HasQueryCount(LessThan(5)))
        self.assertEqual(1, len(dsp_release.sample_binary_packages))

        for iteration in range(5):
            self.makeBinaryPackageRelease()
        dsp_release = self.updateDistroSeriesPackageCache()
        with StormStatementRecorder() as recorder:
            for dsp_package in dsp_release.sample_binary_packages:
                dsp_package.summary
        self.assertThat(recorder, HasQueryCount(LessThan(5)))
        self.assertEqual(6, len(dsp_release.sample_binary_packages))

        # Even if the cache is not updated for binary packages,
        # DistributionSourcePackageRelease objects do not try to
        # retrieve DistroSeriesPackageCache records if they know
        # that such records do not exist.
        for iteration in range(5):
            self.makeBinaryPackageRelease()
        with StormStatementRecorder() as recorder:
            for dsp_package in dsp_release.sample_binary_packages:
                dsp_package.summary
        self.assertThat(recorder, HasQueryCount(LessThan(5)))
        self.assertEqual(11, len(dsp_release.sample_binary_packages))
