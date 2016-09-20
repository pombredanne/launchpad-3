# Copyright 2011-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test generic override policy classes."""

from testtools.matchers import Equals
from zope.component import getUtility

from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database import bulk
from lp.services.database.sqlbase import flush_database_caches
from lp.soyuz.adapters.overrides import (
    BinaryOverride,
    ConstantOverridePolicy,
    FallbackOverridePolicy,
    FromExistingOverridePolicy,
    FromSourceOverridePolicy,
    SourceOverride,
    UnknownOverridePolicy,
    )
from lp.soyuz.enums import (
    PackagePublishingPriority,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import ZopelessDatabaseLayer
from lp.testing.matchers import HasQueryCount


class TestFromExistingOverridePolicy(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_source_overrides(self):
        # When the spn is published in the given archive/distroseries, the
        # overrides for that archive/distroseries are returned.
        spph = self.factory.makeSourcePackagePublishingHistory()
        policy = FromExistingOverridePolicy(
            spph.distroseries.main_archive, spph.distroseries, spph.pocket)
        overrides = policy.calculateSourceOverrides(
            {spph.sourcepackagerelease.sourcepackagename: SourceOverride()})
        expected = {
            spph.sourcepackagerelease.sourcepackagename: SourceOverride(
                component=spph.component, section=spph.section,
                version=spph.sourcepackagerelease.version, new=False)}
        self.assertEqual(expected, overrides)

    def test_source_overrides_pocket(self):
        # If the spn is not published in the given pocket, no changes
        # are made.
        spn = self.factory.makeSourcePackageName()
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeSourcePackagePublishingHistory(
            archive=distroseries.main_archive, distroseries=distroseries,
            pocket=PackagePublishingPocket.RELEASE, sourcepackagename=spn)
        overrides = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries,
            PackagePublishingPocket.PROPOSED).calculateSourceOverrides(
            {spn: SourceOverride()})
        self.assertEqual(0, len(overrides))
        overrides = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries,
            PackagePublishingPocket.RELEASE).calculateSourceOverrides(
            {spn: SourceOverride()})
        self.assertEqual(1, len(overrides))
        overrides = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries,
            None).calculateSourceOverrides(
            {spn: SourceOverride()})
        self.assertEqual(1, len(overrides))

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
        overrides = FromExistingOverridePolicy(
            spph.distroseries.main_archive, spph.distroseries,
            spph.pocket).calculateSourceOverrides(
            {spn: SourceOverride()})
        self.assertEqual(
            {spn: SourceOverride(
                component=spph.component, section=spph.section,
                version=spph.sourcepackagerelease.version, new=False)},
            overrides)

    def test_source_overrides_can_include_deleted(self):
        # include_deleted=True causes Deleted publications to be
        # considered too.
        spn = self.factory.makeSourcePackageName()
        distroseries = self.factory.makeDistroSeries()
        spr = self.factory.makeSourcePackageRelease(sourcepackagename=spn)
        spph = self.factory.makeSourcePackagePublishingHistory(
            archive=distroseries.main_archive, distroseries=distroseries,
            sourcepackagerelease=spr, status=PackagePublishingStatus.PUBLISHED)
        deleted_spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=spn)
        deleted_spph = self.factory.makeSourcePackagePublishingHistory(
            archive=distroseries.main_archive, distroseries=distroseries,
            sourcepackagerelease=deleted_spr,
            status=PackagePublishingStatus.DELETED, pocket=spph.pocket)

        # With include_deleted=False only the Published ancestry is
        # found.
        overrides = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries,
            spph.pocket).calculateSourceOverrides(
            {spn: SourceOverride(spn)})
        self.assertEqual(
            {spn: SourceOverride(
                component=spph.component, section=spph.section,
                version=spph.sourcepackagerelease.version, new=False)},
            overrides)

        # But with include_deleted=True the newer Deleted publication is
        # used.
        overrides = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries,
            spph.pocket, include_deleted=True).calculateSourceOverrides(
            {spn: SourceOverride(spn)})
        self.assertEqual(
            {spn: SourceOverride(
                component=deleted_spph.component, section=deleted_spph.section,
                version=deleted_spph.sourcepackagerelease.version, new=True)},
            overrides)

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
        flush_database_caches()
        distroseries.main_archive
        bulk.reload(spns)
        policy = FromExistingOverridePolicy(
            spph.distroseries.main_archive, spph.distroseries, spph.pocket)
        with StormStatementRecorder() as recorder:
            policy.calculateSourceOverrides(
                dict((spn, SourceOverride()) for spn in spns))
        self.assertThat(recorder, HasQueryCount(Equals(3)))

    def test_no_binary_overrides(self):
        # if the given binary is not published in the given distroarchseries,
        # an empty list is returned.
        distroseries = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        distroseries.nominatedarchindep = das
        bpn = self.factory.makeBinaryPackageName()
        pocket = self.factory.getAnyPocket()
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, pocket)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, None): BinaryOverride()})
        self.assertEqual({}, overrides)

    def test_binary_overrides(self):
        # When a binary is published in the given distroarchseries, the
        # overrides are returned. None means nominatedarchindep,
        # whatever that is in the target series.
        distroseries = self.factory.makeDistroSeries()
        bpph1 = self.factory.makeBinaryPackagePublishingHistory(
            archive=distroseries.main_archive,
            distroarchseries=self.factory.makeDistroArchSeries(distroseries))
        bpph2 = self.factory.makeBinaryPackagePublishingHistory(
            archive=distroseries.main_archive, pocket=bpph1.pocket,
            distroarchseries=self.factory.makeDistroArchSeries(distroseries))
        distroseries.nominatedarchindep = bpph1.distroarchseries
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, bpph1.pocket)
        overrides = policy.calculateBinaryOverrides(
            {(bpph1.binarypackagerelease.binarypackagename,
              bpph1.distroarchseries.architecturetag): BinaryOverride(),
             (bpph2.binarypackagerelease.binarypackagename,
              bpph2.distroarchseries.architecturetag): BinaryOverride(),
             (bpph2.binarypackagerelease.binarypackagename, None):
                BinaryOverride(),
             })
        expected = {
            (bpph1.binarypackagerelease.binarypackagename,
             bpph1.distroarchseries.architecturetag):
                BinaryOverride(
                    component=bpph1.component, section=bpph1.section,
                    priority=bpph1.priority, new=False,
                    version=bpph1.binarypackagerelease.version),
            (bpph2.binarypackagerelease.binarypackagename,
             bpph2.distroarchseries.architecturetag):
                BinaryOverride(
                    component=bpph2.component, section=bpph2.section,
                    priority=bpph2.priority, new=False,
                    version=bpph2.binarypackagerelease.version),
            (bpph2.binarypackagerelease.binarypackagename, None):
                BinaryOverride(
                    component=bpph2.component, section=bpph2.section,
                    priority=bpph2.priority, new=False,
                    version=bpph2.binarypackagerelease.version),
            }
        self.assertEqual(expected, overrides)

    def test_binary_overrides_pocket(self):
        # If the binary is not published in the given pocket, no changes
        # are made.
        distroseries = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        bpn = self.factory.makeBinaryPackageName()
        self.factory.makeBinaryPackagePublishingHistory(
            archive=distroseries.main_archive, distroarchseries=das,
            pocket=PackagePublishingPocket.RELEASE, binarypackagename=bpn)
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries,
            PackagePublishingPocket.PROPOSED)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, das.architecturetag): BinaryOverride()})
        self.assertEqual(0, len(overrides))
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries,
            PackagePublishingPocket.RELEASE)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, das.architecturetag): BinaryOverride()})
        self.assertEqual(1, len(overrides))
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, None)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, das.architecturetag): BinaryOverride()})
        self.assertEqual(1, len(overrides))

    def test_binary_overrides_skips_unknown_arch(self):
        # If calculateBinaryOverrides is passed with an archtag that
        # does not correspond to an ArchSeries of the distroseries,
        # an empty list is returned.
        distroseries = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(
            architecturetag='amd64',
            distroseries=distroseries)
        distroseries.nominatedarchindep = das
        bpn = self.factory.makeBinaryPackageName()
        pocket = self.factory.getAnyPocket()
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, pocket)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, 'i386'): BinaryOverride()})
        self.assertEqual({}, overrides)

    def test_binary_overrides_can_cross_archs(self):
        # calculateBinaryOverrides can be asked to ignore the archtag
        # and look for ancestry in any architecture.
        distroseries = self.factory.makeDistroSeries()
        amd64 = self.factory.makeDistroArchSeries(
            architecturetag='amd64',
            distroseries=distroseries)
        i386 = self.factory.makeDistroArchSeries(
            architecturetag='i386',
            distroseries=distroseries)
        distroseries.nominatedarchindep = i386
        bpn = self.factory.makeBinaryPackageName()
        pocket = self.factory.getAnyPocket()
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            archive=distroseries.main_archive, distroarchseries=amd64,
            pocket=pocket, binarypackagename=bpn, architecturespecific=True)
        bpph_override = BinaryOverride(
            component=bpph.component, section=bpph.section,
            priority=bpph.priority, version=bpph.binarypackagerelease.version,
            new=False)

        # With any_arch=False only amd64 is found.
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, pocket)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, 'i386'): BinaryOverride(),
             (bpn, 'amd64'): BinaryOverride(),
             (bpn, None): BinaryOverride()})
        self.assertEqual({(bpn, 'amd64'): bpph_override}, overrides)

        # But with any_arch=True we get the amd64 overrides everywhere.
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, pocket, any_arch=True)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, 'i386'): BinaryOverride(),
             (bpn, 'amd64'): BinaryOverride(),
             (bpn, None): BinaryOverride()})
        self.assertEqual(
            {(bpn, 'i386'): bpph_override,
             (bpn, 'amd64'): bpph_override,
             (bpn, None): bpph_override},
            overrides)

    def test_binary_overrides_can_include_deleted(self):
        # calculateBinaryOverrides can be asked to include Deleted
        # publications.
        distroseries = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(
            architecturetag='amd64',
            distroseries=distroseries)
        bpn = self.factory.makeBinaryPackageName()
        pocket = self.factory.getAnyPocket()
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            archive=distroseries.main_archive, distroarchseries=das,
            pocket=pocket, binarypackagename=bpn, architecturespecific=True,
            status=PackagePublishingStatus.PUBLISHED)
        deleted_bpph = self.factory.makeBinaryPackagePublishingHistory(
            archive=distroseries.main_archive, distroarchseries=das,
            pocket=pocket, binarypackagename=bpn, architecturespecific=True,
            status=PackagePublishingStatus.DELETED)

        # With include_deleted=False the Published pub is found.
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, pocket)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, 'amd64'): BinaryOverride()})
        self.assertEqual(
            {(bpn, 'amd64'): BinaryOverride(
                component=bpph.component, section=bpph.section,
                priority=bpph.priority,
                version=bpph.binarypackagerelease.version, new=False)},
            overrides)

        # But with include_deleted=True we get the newer Deleted pub instead.
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, pocket,
            include_deleted=True)
        overrides = policy.calculateBinaryOverrides(
            {(bpn, 'amd64'): BinaryOverride()})
        self.assertEqual(
            {(bpn, 'amd64'): BinaryOverride(
                component=deleted_bpph.component, section=deleted_bpph.section,
                priority=deleted_bpph.priority,
                version=deleted_bpph.binarypackagerelease.version, new=True)},
            overrides)

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
        flush_database_caches()
        distroseries.main_archive
        bulk.reload(bpn[0] for bpn in bpns)
        policy = FromExistingOverridePolicy(
            distroseries.main_archive, distroseries, pocket)
        with StormStatementRecorder() as recorder:
            policy.calculateBinaryOverrides(
                dict(((bpn, das), BinaryOverride()) for bpn, das in bpns))
        self.assertThat(recorder, HasQueryCount(Equals(4)))


class TestFromSourceOverridePolicy(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_no_sources(self):
        # Source overrides are never returned.
        self.assertEqual(
            {},
            FromSourceOverridePolicy().calculateSourceOverrides(
                {self.factory.makeSourcePackageName(): SourceOverride()}))

    def test_binaries(self):
        # Binaries are overridden with the component from their
        # corresponding source override, if one was provided.
        bpn = self.factory.makeBinaryPackageName()
        other_bpn = self.factory.makeBinaryPackageName()
        component = self.factory.makeComponent()
        random_component = self.factory.makeComponent()
        self.assertEqual(
            {(bpn, None): BinaryOverride(component=component, new=True)},
            FromSourceOverridePolicy().calculateBinaryOverrides(
                {(bpn, None): BinaryOverride(
                    component=random_component,
                    source_override=SourceOverride(component=component)),
                 (other_bpn, None): BinaryOverride(
                     component=random_component)}))


class TestUnknownOverridePolicy(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_getComponentOverride_default_name(self):
        # getComponentOverride returns the default component name when an
        # unknown component name is passed.
        component_name = UnknownOverridePolicy.getComponentOverride('no-name')

        self.assertEqual('universe', component_name)

    def test_getComponentOverride_default_component(self):
        # getComponentOverride also accepts a component object (as
        # opposed to a component's name).
        component = getUtility(IComponentSet)['universe']
        component_name = UnknownOverridePolicy.getComponentOverride(component)

        self.assertEqual('universe', component_name)

    def test_getComponentOverride_return_component(self):
        # Passing return_component=True to getComponentOverride makes it
        # return the Component object (as opposed to the component's
        # name).
        universe_component = getUtility(IComponentSet)['universe']
        component = UnknownOverridePolicy.getComponentOverride(
            universe_component, return_component=True)

        self.assertEqual(universe_component, component)

    def test_unknown_sources(self):
        # The unknown policy uses a default component based on the
        # pre-override component.
        for component in ('contrib', 'non-free'):
            self.factory.makeComponent(component)
        distroseries = self.factory.makeDistroSeries()
        spns = [self.factory.makeSourcePackageName() for i in range(3)]
        policy = UnknownOverridePolicy(
            distroseries.main_archive, distroseries,
            PackagePublishingPocket.RELEASE)
        overrides = policy.calculateSourceOverrides(
            dict(
                (spn, SourceOverride(
                    component=getUtility(IComponentSet)[component]))
                for spn, component in
                zip(spns, ('main', 'contrib', 'non-free'))))
        expected = dict(
            (spn, SourceOverride(
                component=getUtility(IComponentSet)[component], new=True))
            for spn, component in
            zip(spns, ('universe', 'multiverse', 'multiverse')))
        self.assertEqual(expected, overrides)

    def test_unknown_binaries(self):
        # If the unknown policy is used, it does no checks, just returns the
        # defaults.
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        distroseries = bpph.distroarchseries.distroseries
        distroseries.nominatedarchindep = bpph.distroarchseries
        policy = UnknownOverridePolicy(
            distroseries.main_archive, distroseries, bpph.pocket)
        overrides = policy.calculateBinaryOverrides(
            {(bpph.binarypackagerelease.binarypackagename, None):
                BinaryOverride()})
        universe = getUtility(IComponentSet)['universe']
        expected = {
            (bpph.binarypackagerelease.binarypackagename, None):
                BinaryOverride(component=universe, new=True)}
        self.assertEqual(expected, overrides)


class TestConstantOverridePolicy(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_sources(self):
        policy = ConstantOverridePolicy(
            component=self.factory.makeComponent(),
            section=self.factory.makeSection(),
            phased_update_percentage=50, new=True)
        spn = self.factory.makeSourcePackageName()
        self.assertEqual(
            {spn: SourceOverride(
                component=policy.component, section=policy.section,
                new=True)},
            policy.calculateSourceOverrides(
                {spn: SourceOverride(
                    component=self.factory.makeComponent(),
                    section=self.factory.makeSection(), new=False)}))

    def test_binary(self):
        policy = ConstantOverridePolicy(
            component=self.factory.makeComponent(),
            section=self.factory.makeSection(),
            priority=PackagePublishingPriority.EXTRA,
            phased_update_percentage=50, new=True)
        bpn = self.factory.makeBinaryPackageName()
        self.assertEqual(
            {(bpn, None): BinaryOverride(
                component=policy.component, section=policy.section,
                priority=policy.priority, phased_update_percentage=50,
                new=True)},
            policy.calculateBinaryOverrides(
                {(bpn, None): BinaryOverride(
                    component=self.factory.makeComponent(),
                    section=self.factory.makeSection(),
                    priority=PackagePublishingPriority.REQUIRED,
                    phased_update_percentage=90, new=False)}))


class TestFallbackOverridePolicy(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_fallback_sources(self):
        # The fallback policy runs through a sequence of policies until
        # all overrides are fulfilled.
        universe = getUtility(IComponentSet)['universe']
        spns = [self.factory.makeSourcePackageName()]
        expected = {spns[0]: SourceOverride(component=universe, new=True)}
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        for i in xrange(8):
            spph = self.factory.makeSourcePackagePublishingHistory(
                distroseries=distroseries, archive=distroseries.main_archive,
                pocket=pocket)
            spns.append(spph.sourcepackagerelease.sourcepackagename)
            expected[spph.sourcepackagerelease.sourcepackagename] = (
                SourceOverride(
                    component=spph.component, section=spph.section,
                    version=spph.sourcepackagerelease.version, new=False))
        spns.append(self.factory.makeSourcePackageName())
        expected[spns[-1]] = SourceOverride(component=universe, new=True)
        policy = FallbackOverridePolicy([
            FromExistingOverridePolicy(
                distroseries.main_archive, distroseries, pocket),
            UnknownOverridePolicy(
                distroseries.main_archive, distroseries, pocket)])
        overrides = policy.calculateSourceOverrides(
            dict((spn, SourceOverride()) for spn in spns))
        self.assertEqual(10, len(overrides))
        self.assertEqual(expected, overrides)

    def test_ubuntu_override_policy_binaries(self):
        # The Ubuntu policy incorporates both the existing and the unknown
        # policy.
        universe = getUtility(IComponentSet)['universe']
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        bpn = self.factory.makeBinaryPackageName()
        bpns = []
        expected = {}
        for i in xrange(3):
            distroarchseries = self.factory.makeDistroArchSeries(
                distroseries=distroseries)
            bpb = self.factory.makeBinaryPackageBuild(
                distroarchseries=distroarchseries)
            bpr = self.factory.makeBinaryPackageRelease(
                build=bpb, binarypackagename=bpn,
                architecturespecific=True)
            bpph = self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr, distroarchseries=distroarchseries,
                archive=distroseries.main_archive, pocket=pocket)
            bpns.append((bpn, distroarchseries.architecturetag))
            expected[(bpn, distroarchseries.architecturetag)] = (
                BinaryOverride(
                    component=bpph.component, section=bpph.section,
                    priority=bpph.priority, new=False,
                    version=bpph.binarypackagerelease.version))
        for i in xrange(2):
            distroarchseries = self.factory.makeDistroArchSeries(
                distroseries=distroseries)
            bpns.append((bpn, distroarchseries.architecturetag))
            expected[bpn, distroarchseries.architecturetag] = BinaryOverride(
                component=universe, new=True)
        distroseries.nominatedarchindep = distroarchseries
        policy = FallbackOverridePolicy([
            FromExistingOverridePolicy(
                distroseries.main_archive, distroseries, pocket),
            UnknownOverridePolicy(
                distroseries.main_archive, distroseries, pocket)])
        overrides = policy.calculateBinaryOverrides(
            dict(((bpn, das), BinaryOverride()) for bpn, das in bpns))
        self.assertEqual(5, len(overrides))
        self.assertEqual(expected, overrides)

    def test_phased_update_percentage(self):
        # A policy with a phased_update_percentage applies it to new binary
        # overrides.
        universe = getUtility(IComponentSet)['universe']
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        bpn = self.factory.makeBinaryPackageName()
        bpns = []
        expected = {}
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries)
        bpb = self.factory.makeBinaryPackageBuild(
            distroarchseries=distroarchseries)
        bpr = self.factory.makeBinaryPackageRelease(
            build=bpb, binarypackagename=bpn, architecturespecific=True)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr, distroarchseries=distroarchseries,
            archive=distroseries.main_archive, pocket=pocket)
        bpns.append((bpn, distroarchseries.architecturetag))
        expected[(bpn, distroarchseries.architecturetag)] = BinaryOverride(
            component=bpph.component, section=bpph.section,
            priority=bpph.priority, phased_update_percentage=50,
            version=bpph.binarypackagerelease.version, new=False)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries)
        bpns.append((bpn, distroarchseries.architecturetag))
        expected[(bpn, distroarchseries.architecturetag)] = BinaryOverride(
            component=universe, phased_update_percentage=50, new=True)
        distroseries.nominatedarchindep = distroarchseries
        policy = FallbackOverridePolicy([
            FromExistingOverridePolicy(
                distroseries.main_archive, distroseries, pocket,
                phased_update_percentage=50),
            UnknownOverridePolicy(
                distroseries.main_archive, distroseries, pocket,
                phased_update_percentage=50)])
        overrides = policy.calculateBinaryOverrides(
            dict(((bpn, das), BinaryOverride()) for bpn, das in bpns))
        self.assertEqual(2, len(overrides))
        self.assertEqual(expected, overrides)
