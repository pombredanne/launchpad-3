# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test generic override methods."""

from testtools.matchers import Equals

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.soyuz.adapters.overrides import (
    FromExistingOverridePolicy,
    UbuntuOverridePolicy,
    UnknownOverridePolicy,
    )
from lp.soyuz.enums import PackagePublishingStatus
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


class TestOverrides(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_FromExistingOverridePolicy_both(self):
        # The FromExistingOverridePolicy() can not handle both source and
        # binary arguments in one call.
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        policy = FromExistingOverridePolicy()
        self.assertRaises(
            AssertionError, policy.calculateOverrides,
            distroseries.main_archive, distroseries, pocket, sources=(),
            binaries=())

    def test_no_source_overrides(self):
        # If the spn is not published in the given archive/distroseries, an
        # empty list is returned.
        spn = self.factory.makeSourcePackageName()
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        policy = FromExistingOverridePolicy()
        overrides = policy.calculateOverrides(
            distroseries.main_archive, distroseries, pocket, sources=(spn,))
        self.assertEqual([], overrides)

    def test_source_overrides(self):
        # When the spn is published in the given archive/distroseries, the
        # overrides for that archive/distroseries are returned.
        spph = self.factory.makeSourcePackagePublishingHistory()
        policy = FromExistingOverridePolicy()
        overrides = policy.calculateOverrides(
            spph.distroseries.main_archive, spph.distroseries, spph.pocket,
            sources=(spph.sourcepackagerelease.sourcepackagename,))
        expected = [(
            spph.sourcepackagerelease.sourcepackagename,
            spph.component, spph.section)]
        self.assertEqual(expected, overrides)

    def test_source_overrides_latest_only_is_returned(self):
        # When the spn is published multiple times in the given
        # archive/distroseries, the latest publication's overrides are
        # returned.
        spn = self.factory.makeSourcePackageName()
        distroseries = self.factory.makeDistroSeries()
        published_spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=spn)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=published_spr, distroseries=distroseries,
            status=PackagePublishingStatus.PUBLISHED)
        spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=spn)
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr, distroseries=distroseries)
        policy = FromExistingOverridePolicy()
        overrides = policy.calculateOverrides(
            distroseries.main_archive, distroseries, spph.pocket,
            sources=(spn,))
        self.assertEqual([(spn, spph.component, spph.section)], overrides)

    def test_source_overrides_constant_query_count(self):
        # The query count is constant, no matter how many sources are
        # checked.
        spns = []
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        for i in xrange(10):
            spph = self.factory.makeSourcePackagePublishingHistory(
                distroseries=distroseries, archive=distroseries.main_archive,
                pocket=pocket)
            spns.append(spph.sourcepackagerelease.sourcepackagename)
        policy = FromExistingOverridePolicy()
        with StormStatementRecorder() as recorder:
            policy.calculateOverrides(
                spph.distroseries.main_archive, spph.distroseries,
                spph.pocket, sources=spns)
        self.assertThat(recorder, HasQueryCount(Equals(2)))

    def test_no_binary_overrides(self):
        # if the given binary is not published in the given distroarchseries,
        # an empty list is returned.
        distroseries = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        distroseries.nominatedarchindep = das
        bpn = self.factory.makeBinaryPackageName()
        pocket = self.factory.getAnyPocket()
        policy = FromExistingOverridePolicy()
        overrides = policy.calculateOverrides(
            distroseries.main_archive, distroseries, pocket,
            binaries=((bpn, None),))
        self.assertEqual([], overrides)

    def test_binary_overrides(self):
        # When a binary is published in the given distroarchseries, the
        # overrides are returned.
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        distroseries = bpph.distroarchseries.distroseries
        distroseries.nominatedarchindep = bpph.distroarchseries
        policy = FromExistingOverridePolicy()
        overrides = policy.calculateOverrides(
            distroseries.main_archive, distroseries, bpph.pocket,
            binaries=((bpph.binarypackagerelease.binarypackagename, None),))
        expected = [(
            bpph.binarypackagerelease.binarypackagename,
            bpph.distroarchseries, bpph.component, bpph.section,
            bpph.priority)]
        self.assertEqual(expected, overrides)

    def test_binary_overrides_constant_query_count(self):
        # The query count is constant, no matter how many bpn-das pairs are
        # checked.
        bpns = []
        distroarchseries = self.factory.makeDistroArchSeries()
        distroseries = distroarchseries.distroseries
        distroseries.nominatedarchindep = distroarchseries
        pocket = self.factory.getAnyPocket()
        for i in xrange(10):
            bpph = self.factory.makeBinaryPackagePublishingHistory(
                distroarchseries=distroarchseries, 
                archive=distroseries.main_archive, pocket=pocket)
            bpns.append((bpph.binarypackagerelease.binarypackagename, None))
        policy = FromExistingOverridePolicy()
        with StormStatementRecorder() as recorder:
            policy.calculateOverrides(
                distroseries.main_archive, distroseries, pocket,
                binaries=bpns)
        self.assertThat(recorder, HasQueryCount(Equals(5)))

    def test_unknown_sources(self):
        # If the unknown policy is used, it does no checks, just returns the
        # defaults.
        spph = self.factory.makeSourcePackagePublishingHistory()
        policy = UnknownOverridePolicy()
        overrides = policy.calculateOverrides(
            spph.distroseries.main_archive, spph.distroseries, spph.pocket,
            sources=(spph.sourcepackagerelease.sourcepackagename,))
        expected = [(spph.sourcepackagerelease.sourcepackagename, 'universe',
            None)]
        self.assertEqual(expected, overrides)

    def test_unknown_binaries(self):
        # If the unknown policy is used, it does no checks, just returns the
        # defaults.
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        distroseries = bpph.distroarchseries.distroseries
        distroseries.nominatedarchindep = bpph.distroarchseries
        policy = UnknownOverridePolicy()
        overrides = policy.calculateOverrides(
            distroseries.main_archive, distroseries, bpph.pocket,
            binaries=((bpph.binarypackagerelease.binarypackagename, None),))
        expected = [(bpph.binarypackagerelease.binarypackagename,
            bpph.distroarchseries, 'universe', None, None)]
        self.assertEqual(expected, overrides)

    def test_ubuntu_override_policy_sources(self):
        # The Ubuntu policy incorporates both the existing and the unknown
        # policy.
        spns = [self.factory.makeSourcePackageName()]
        expected = [(spns[0], 'universe', None)]
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        for i in xrange(8):
            spph = self.factory.makeSourcePackagePublishingHistory(
                distroseries=distroseries, archive=distroseries.main_archive,
                pocket=pocket)
            spns.append(spph.sourcepackagerelease.sourcepackagename)
            expected.append((
                spph.sourcepackagerelease.sourcepackagename, spph.component,
                spph.section))
        spns.append(self.factory.makeSourcePackageName())
        expected.append((spns[-1], 'universe', None))
        policy = UbuntuOverridePolicy()
        overrides = policy.calculateOverrides(
            distroseries.main_archive, distroseries, pocket, sources=spns)
        self.assertEqual(10, len(overrides))
        self.assertContentEqual(expected, overrides)

    def test_ubuntu_override_policy_binaries(self):
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        bpn = self.factory.makeBinaryPackageName()
        bpns = []
        expected = []
        for i in xrange(3):
            distroarchseries = self.factory.makeDistroArchSeries(
                distroseries=distroseries)
            bpr = self.factory.makeBinaryPackageRelease(
                binarypackagename=bpn)
            bpph = self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr, distroarchseries=distroarchseries,
                archive=distroseries.main_archive, pocket=pocket)
            bpns.append((bpn, distroarchseries.architecturetag))
            expected.append((
                bpn, distroarchseries, bpph.component, bpph.section,
                bpph.priority))
        for i in xrange(2):
            distroarchseries = self.factory.makeDistroArchSeries(
                distroseries=distroseries)
            bpns.append((bpn, distroarchseries.architecturetag))
            expected.append((bpn, distroarchseries, 'universe', None, None))
        distroseries.nominatedarchindep = distroarchseries
        policy = UbuntuOverridePolicy()
        overrides = policy.calculateOverrides(
            distroseries.main_archive, distroseries, pocket, binaries=bpns)
        self.assertEqual(5, len(overrides))
        self.assertContentEqual(expected, overrides)
