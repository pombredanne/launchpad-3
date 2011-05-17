# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.soyuz.model.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease,
    )
from lp.testing import TestCaseWithFactory


class TestDistributionSourcePackageRelease(TestCaseWithFactory):
    """Tests for DistributionSourcePackageRelease."""

    layer = DatabaseFunctionalLayer

    def test_sample_binary_packages__no_releases(self):
        # If no binary releases exist,
        # DistributionSourcePackageRelease.sample_binary_packages is empty.
        sourcepackage_release = self.factory.makeSourcePackageRelease()
        distribution = (
            sourcepackage_release.sourcepackage.distroseries.distribution)
        dsp_release = DistributionSourcePackageRelease(
            distribution, sourcepackage_release)
        self.assertEqual([], dsp_release.sample_binary_packages)

    def makeBinaryPackageRelease(self, sourcepackage_release, name,
                                 distroarchseries):
        bp_build = self.factory.makeBinaryPackageBuild(
            source_package_release=sourcepackage_release,
            distroarchseries=distroarchseries)
        bp_release = self.factory.makeBinaryPackageRelease(
            build=bp_build, binarypackagename=name)
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bp_release,
            distroarchseries=distroarchseries)

    def test_sample_binary_packages__one_release(self):
        # If a binary release exists,
        # DistributionSourcePackageRelease.sample_binary_packages
        # returns it.
        sourcepackage_release = self.factory.makeSourcePackageRelease()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=sourcepackage_release.sourcepackage.distroseries)
        name = self.factory.makeBinaryPackageName(name='binary-package')
        self.makeBinaryPackageRelease(
            sourcepackage_release, name, distroarchseries)
        distribution = (
            sourcepackage_release.sourcepackage.distroseries.distribution)
        dsp_release = DistributionSourcePackageRelease(
            distribution, sourcepackage_release)
        self.assertEqual(
            ['binary-package'],
            [release.name for release in dsp_release.sample_binary_packages])

    def test_sample_binary_packages__two_releases_one_binary_package(self):
        # If two binary releases with the same name exist,
        # DistributionSourcePackageRelease.sample_binary_packages
        # returns only one.
        sourcepackage_release = self.factory.makeSourcePackageRelease()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=sourcepackage_release.sourcepackage.distroseries)
        name = self.factory.makeBinaryPackageName(name='binary-package')
        self.makeBinaryPackageRelease(
            sourcepackage_release, name, distroarchseries)
        self.makeBinaryPackageRelease(
            sourcepackage_release, name, distroarchseries)
        distribution = (
            sourcepackage_release.sourcepackage.distroseries.distribution)
        dsp_release = DistributionSourcePackageRelease(
            distribution, sourcepackage_release)
        self.assertEqual(
            ['binary-package'],
            [release.name for release in dsp_release.sample_binary_packages])

    def test_sample_binary_packages__two_release_two_binary_packages(self):
        # If a two binary releases with different names exist,
        # DistributionSourcePackageRelease.sample_binary_packages
        # returns both.
        sourcepackage_release = self.factory.makeSourcePackageRelease()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=sourcepackage_release.sourcepackage.distroseries)
        name = self.factory.makeBinaryPackageName(name='binary-package')
        self.makeBinaryPackageRelease(
            sourcepackage_release, name, distroarchseries)
        name = self.factory.makeBinaryPackageName(name='binary-package-2')
        self.makeBinaryPackageRelease(
            sourcepackage_release, name, distroarchseries)
        distribution = (
            sourcepackage_release.sourcepackage.distroseries.distribution)
        dsp_release = DistributionSourcePackageRelease(
            distribution, sourcepackage_release)
        self.assertEqual(
            ['binary-package', 'binary-package-2'],
            [release.name for release in dsp_release.sample_binary_packages])
