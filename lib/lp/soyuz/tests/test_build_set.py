# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import (
    ArchivePurpose,
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.binarypackagebuild import (
    BuildSetStatus,
    IBinaryPackageBuildSet,
    )
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuildSet
from lp.soyuz.scripts.packagecopier import do_copy
from lp.soyuz.tests.test_publishing import (
    SoyuzTestPublisher,
    TestNativePublishingBase,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    LaunchpadFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestBuildSet(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuildSet, self).setUp()
        self.admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self.processor_one = self.factory.makeProcessor(
            supports_virtualized=True)
        self.processor_two = self.factory.makeProcessor(
            supports_virtualized=True)
        self.distroseries = self.factory.makeDistroSeries()
        self.distribution = self.distroseries.distribution
        self.das_one = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processor=self.processor_one)
        self.das_two = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processor=self.processor_two)
        self.archive = self.factory.makeArchive(
            distribution=self.distroseries.distribution,
            purpose=ArchivePurpose.PRIMARY)
        with person_logged_in(self.admin):
            self.publisher = SoyuzTestPublisher()
            self.publisher.prepareBreezyAutotest()
            self.distroseries.nominatedarchindep = self.das_one
            self.publisher.addFakeChroots(distroseries=self.distroseries)
            self.factory.makeBuilder(processors=[self.processor_one])
            self.factory.makeBuilder(processors=[self.processor_two])
        self.builds = []
        self.spphs = []

    def setUpBuilds(self):
        for i in range(5):
            # Create some test builds
            spph = self.publisher.getPubSource(
                sourcename=self.factory.getUniqueString(),
                version="%s.%s" % (self.factory.getUniqueInteger(), i),
                distroseries=self.distroseries, architecturehintlist='any')
            self.spphs.append(spph)
            builds = removeSecurityProxy(
                getUtility(IBinaryPackageBuildSet).createForSource(
                    spph.sourcepackagerelease, spph.archive,
                    spph.distroseries, spph.pocket))
            with person_logged_in(self.admin):
                for b in builds:
                    b.updateStatus(BuildStatus.BUILDING)
                    if i == 4:
                        b.updateStatus(BuildStatus.FAILEDTOBUILD)
                    else:
                        b.updateStatus(BuildStatus.FULLYBUILT)
                    b.buildqueue_record.destroySelf()
            self.builds += builds

    def test_new_virtualization(self):
        # Builds are virtualized unless Processor.support_nonvirtualized
        # and not Archive.require_virtualized.

        def make(proc_virt, proc_nonvirt, archive_virt):
            proc = self.factory.makeProcessor(
                supports_nonvirtualized=proc_nonvirt,
                supports_virtualized=proc_virt)
            das = self.factory.makeDistroArchSeries(processor=proc)
            archive = self.factory.makeArchive(
                distribution=das.distroseries.distribution,
                virtualized=archive_virt)
            bpb = getUtility(IBinaryPackageBuildSet).new(
                self.factory.makeSourcePackageRelease(),
                archive, das, PackagePublishingPocket.RELEASE)
            self.assertEqual(proc, bpb.processor)
            return bpb

        vvvbpb = make(proc_virt=True, proc_nonvirt=True, archive_virt=True)
        self.assertTrue(vvvbpb.virtualized)

        vvnbpb = make(proc_virt=True, proc_nonvirt=True, archive_virt=False)
        self.assertFalse(vvnbpb.virtualized)

        vnvbpb = make(proc_virt=True, proc_nonvirt=False, archive_virt=True)
        self.assertTrue(vnvbpb.virtualized)

        vnvbpb = make(proc_virt=True, proc_nonvirt=False, archive_virt=False)
        self.assertTrue(vnvbpb.virtualized)

    def test_get_for_distro_distribution(self):
        # Test fetching builds for a distro's main archives
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution)
        self.assertEqual(set.count(), 10)

    def test_get_for_distro_distroseries(self):
        # Test fetching builds for a distroseries' main archives
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distroseries)
        self.assertEqual(set.count(), 10)

    def test_get_for_distro_distroarchseries(self):
        # Test fetching builds for a distroarchseries' main archives
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.das_one)
        self.assertEqual(set.count(), 5)

    def test_get_for_distro_filter_build_status(self):
        # The result can be filtered based on the build status
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, status=BuildStatus.FULLYBUILT)
        self.assertEqual(set.count(), 8)

    def test_get_for_distro_filter_name(self):
        # The result can be filtered based on the name
        self.setUpBuilds()
        spn = self.builds[2].source_package_release.sourcepackagename.name
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, name=spn)
        self.assertEqual(set.count(), 2)

    def test_get_for_distro_filter_pocket(self):
        # The result can be filtered based on the pocket of the build
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, pocket=PackagePublishingPocket.RELEASE)
        self.assertEqual(set.count(), 10)
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, pocket=PackagePublishingPocket.UPDATES)
        self.assertEqual(set.count(), 0)

    def test_get_for_distro_filter_arch_tag(self):
        # The result can be filtered based on the archtag of the build
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, arch_tag=self.das_one.architecturetag)
        self.assertEqual(set.count(), 5)

    def test_get_status_summary_for_builds(self):
        # We can query for the status summary of a number of builds
        self.setUpBuilds()
        relevant_builds = [self.builds[0], self.builds[2], self.builds[-2]]
        summary = getUtility(
            IBinaryPackageBuildSet).getStatusSummaryForBuilds(
                relevant_builds)
        self.assertEqual(summary['status'], BuildSetStatus.FAILEDTOBUILD)
        self.assertEqual(summary['builds'], [self.builds[-2]])

    def test_preload_data(self):
        # The BuildSet class allows data to be preloaded
        # Note, it is an internal method, so we have to push past the security
        # proxy
        self.setUpBuilds()
        build_ids = [self.builds[i] for i in (0, 1, 2, 3)]
        rset = removeSecurityProxy(
            getUtility(IBinaryPackageBuildSet))._prefetchBuildData(build_ids)
        self.assertEqual(len(rset), 4)

    def test_get_builds_by_source_package_release(self):
        # We are able to return all of the builds for the source package
        # release ids passed in.
        self.setUpBuilds()
        spphs = self.spphs[:2]
        ids = [spph.sourcepackagerelease.id for spph in spphs]
        builds = getUtility(
            IBinaryPackageBuildSet).getBuildsBySourcePackageRelease(ids)
        expected_titles = []
        for spph in spphs:
            for das in (self.das_one, self.das_two):
                expected_titles.append(
                    '%s build of %s %s in %s %s RELEASE' % (
                        das.architecturetag, spph.source_package_name,
                        spph.source_package_version,
                        self.distroseries.distribution.name,
                        self.distroseries.name))
        build_titles = [build.title for build in builds]
        self.assertEqual(sorted(expected_titles), sorted(build_titles))

    def test_get_builds_by_source_package_release_filtering(self):
        self.setUpBuilds()
        ids = [self.spphs[-1].sourcepackagerelease.id]
        builds = getUtility(
            IBinaryPackageBuildSet).getBuildsBySourcePackageRelease(
                ids, buildstate=BuildStatus.FAILEDTOBUILD)
        expected_titles = []
        for das in (self.das_one, self.das_two):
            expected_titles.append(
                '%s build of %s %s in %s %s RELEASE' % (
                    das.architecturetag, self.spphs[-1].source_package_name,
                    self.spphs[-1].source_package_version,
                    self.distroseries.distribution.name,
                    self.distroseries.name))
        build_titles = [build.title for build in builds]
        self.assertEqual(sorted(expected_titles), sorted(build_titles))
        builds = getUtility(
            IBinaryPackageBuildSet).getBuildsBySourcePackageRelease(
                ids, buildstate=BuildStatus.CHROOTWAIT)
        self.assertEqual([], list(builds))

    def test_no_get_builds_by_source_package_release(self):
        # If no ids or None are passed into .getBuildsBySourcePackageRelease,
        # an empty list is returned.
        builds = getUtility(
            IBinaryPackageBuildSet).getBuildsBySourcePackageRelease(None)
        self.assertEqual([], builds)
        builds = getUtility(
            IBinaryPackageBuildSet).getBuildsBySourcePackageRelease([])
        self.assertEqual([], builds)

    def test_getBySourceAndLocation(self):
        self.setUpBuilds()
        self.assertEqual(
            self.builds[0],
            getUtility(IBinaryPackageBuildSet).getBySourceAndLocation(
                self.builds[0].source_package_release, self.builds[0].archive,
                self.builds[0].distro_arch_series))
        self.assertEqual(
            self.builds[1],
            getUtility(IBinaryPackageBuildSet).getBySourceAndLocation(
                self.builds[1].source_package_release, self.builds[1].archive,
                self.builds[1].distro_arch_series))
        self.assertIs(
            None,
            getUtility(IBinaryPackageBuildSet).getBySourceAndLocation(
                self.builds[1].source_package_release,
                self.factory.makeArchive(),
                self.builds[1].distro_arch_series))


class TestGetAllowedArchitectures(TestCaseWithFactory):
    """Tests for _getAllowedArchitectures."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestGetAllowedArchitectures, self).setUp()
        self.avr = self.factory.makeProcessor(
            name="avr2001", supports_virtualized=True)
        self.sparc = self.factory.makeProcessor(
            name="sparc64", supports_virtualized=True)
        self.distroseries = self.factory.makeDistroSeries()
        self.distro = self.distroseries.distribution
        for name, arch in (('avr', self.avr), ('sparc', self.sparc)):
            self.factory.makeDistroArchSeries(
                architecturetag=name, processor=arch,
                distroseries=self.distroseries)

    def test_normal(self):
        self.assertContentEqual(
            [self.distroseries['sparc'], self.distroseries['avr']],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                self.factory.makeArchive(distribution=self.distro),
                self.distroseries.architectures))

    def test_restricted(self):
        # Restricted architectures aren't returned by default.
        self.avr.build_by_default = False
        self.avr.restricted = True
        self.assertContentEqual(
            [self.distroseries['sparc']],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                self.factory.makeArchive(distribution=self.distro),
                self.distroseries.architectures))

    def test_restricted_override(self):
        # Restricted architectures are returned if allowed by the archive.
        self.avr.build_by_default = False
        self.avr.restricted = True
        archive = self.factory.makeArchive(distribution=self.distro)
        self.assertContentEqual(
            [self.distroseries['sparc']],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                archive, self.distroseries.architectures))
        archive.setProcessors(archive.processors + [self.avr])
        self.assertContentEqual(
            [self.distroseries['sparc'], self.distroseries['avr']],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                archive, self.distroseries.architectures))

    def test_disabled_architectures_omitted(self):
        # Disabled architectures are not buildable, so are excluded.
        self.distroseries['sparc'].enabled = False
        self.assertContentEqual(
            [self.distroseries['avr']],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                self.factory.makeArchive(distribution=self.distro),
                self.distroseries.architectures))

    def test_virt_archives_have_only_virt_archs(self):
        # For archives which must build on virtual builders, only
        # virtual archs are returned.
        self.sparc.supports_virtualized = False
        self.assertContentEqual(
            [self.distroseries['avr']],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                self.factory.makeArchive(distribution=self.distro),
                self.distroseries.architectures))

    def test_nonvirt_archives_have_only_all_archs(self):
        # Non-virtual archives can build on all unrestricted architectures.
        self.sparc.supports_virtualized = False
        self.assertContentEqual(
            [self.distroseries['sparc'], self.distroseries['avr']],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                self.factory.makeArchive(
                    distribution=self.distro, virtualized=False),
                self.distroseries.architectures))


class BuildRecordCreationTests(TestNativePublishingBase):
    """Test the creation of build records."""

    def setUp(self):
        super(BuildRecordCreationTests, self).setUp()
        self.distro = self.factory.makeDistribution()
        self.avr = self.factory.makeProcessor(
            name="avr2001", supports_virtualized=True)
        self.sparc = self.factory.makeProcessor(
            name="sparc64", supports_virtualized=True)
        self.x32 = self.factory.makeProcessor(
            name="x32", supports_virtualized=True)

        self.distroseries = self.factory.makeDistroSeries(
            distribution=self.distro, name="crazy")
        for name, arch in (('avr', self.avr), ('sparc', self.sparc)):
            self.factory.makeDistroArchSeries(
                architecturetag=name, processor=arch,
                distroseries=self.distroseries)
        self.distroseries.nominatedarchindep = self.distroseries['sparc']
        self.addFakeChroots(self.distroseries)

        self.distroseries2 = self.factory.makeDistroSeries(
            distribution=self.distro, name="dumb")
        for name, arch in (('avr', self.avr), ('sparc', self.sparc),
                           ('x32', self.x32)):
            self.factory.makeDistroArchSeries(
                architecturetag=name, processor=arch,
                distroseries=self.distroseries2)
        self.distroseries2.nominatedarchindep = self.distroseries2['x32']
        self.addFakeChroots(self.distroseries2)

        # Initialised by the first createBuilds in case the test needs
        # to tweak arch settings.
        self.archive = None

    def getPubSource(self, architecturehintlist):
        """Return a mock source package publishing record for the archive
        and architecture used in this testcase.

        :param architecturehintlist: Architecture hint list
            (e.g. "i386 amd64")
        """
        return super(BuildRecordCreationTests, self).getPubSource(
            archive=self.factory.makeArchive(), distroseries=self.distroseries,
            architecturehintlist=architecturehintlist)

    def createBuilds(self, spr, distroseries):
        if self.archive is None:
            self.archive = self.factory.makeArchive(distribution=self.distro)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr, archive=self.archive,
            distroseries=distroseries, pocket=PackagePublishingPocket.RELEASE)
        return getUtility(IBinaryPackageBuildSet).createForSource(
            spr, self.archive, distroseries, PackagePublishingPocket.RELEASE)

    def assertBuildsMatch(self, expected, builds):
        actual = {
            build.distro_arch_series.architecturetag: build.arch_indep
            for build in builds}
        self.assertContentEqual(expected.items(), actual.items())
        self.assertEqual(len(actual), len(builds))

    def completeBuilds(self, builds, success_map):
        for build in builds:
            success_or_failure = success_map.get(
                build.distro_arch_series.architecturetag, None)
            if success_or_failure is not None:
                build.updateStatus(
                    BuildStatus.FULLYBUILT if success_or_failure
                    else BuildStatus.FAILEDTOBUILD)
                del success_map[build.distro_arch_series.architecturetag]
        self.assertContentEqual([], success_map)

    def test_createForSource_restricts_any(self):
        """createForSource() should limit builds targeted at 'any'
        architecture to those allowed for the archive.
        """
        self.avr.build_by_default = False
        self.avr.restricted = True
        spr = self.factory.makeSourcePackageRelease(architecturehintlist='any')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True}, builds)

    def test_createForSource_restricts_explicitlist(self):
        """createForSource() limits builds targeted at a variety of
        architectures architecture to those allowed for the archive.
        """
        self.avr.build_by_default = False
        self.avr.restricted = True
        spr = self.factory.makeSourcePackageRelease(
            architecturehintlist='sparc i386 avr')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True}, builds)

    def test_createForSource_restricts_all(self):
        """createForSource() should limit builds targeted at 'all'
        architectures to the nominated independent architecture,
        if that is allowed for the archive.
        """
        self.avr.build_by_default = False
        self.avr.restricted = True
        spr = self.factory.makeSourcePackageRelease(architecturehintlist='all')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True}, builds)

    def test_createForSource_restrict_override(self):
        """createForSource() should limit builds targeted at 'any'
        architecture to architectures that are unrestricted or
        explicitly associated with the archive.
        """
        self.avr.build_by_default = False
        self.avr.restricted = True
        self.archive = self.factory.makeArchive(distribution=self.distro)
        self.archive.setProcessors(self.archive.processors + [self.avr])
        spr = self.factory.makeSourcePackageRelease(architecturehintlist='any')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True, 'avr': False}, builds)

    def test_createForSource_arch_indep_from_scratch(self):
        """createForSource() sets arch_indep=True on builds for the
        nominatedarchindep architecture when no builds already exist.
        """
        spr = self.factory.makeSourcePackageRelease(architecturehintlist='any')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True, 'avr': False}, builds)

    def test_createForSource_any_with_nai_change(self):
        # A new non-arch-indep build is created for a new
        # nominatedarchindep architecture if arch-indep has already
        # built elsewhere.
        #
        # This is most important when copying with binaries between
        # series with different nominatedarchdep (bug #1350208).
        spr = self.factory.makeSourcePackageRelease(architecturehintlist='any')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True, 'avr': False}, builds)
        self.completeBuilds(builds, {'sparc': True, 'avr': True})
        # The new nominatedarchindep needs to be built, but we already
        # have arch-indep binaries so arch_indep is False.
        new_builds = self.createBuilds(spr, self.distroseries2)
        self.assertBuildsMatch({'x32': False}, new_builds)

    def test_createForSource_any_with_nai_change_and_fail(self):
        # When the previous arch-indep build has failed, and
        # nominatedarchindep has changed in the new series, the new
        # nominatedarchindep has arch_indep=True while the other arch
        # has arch_indep=False.
        spr = self.factory.makeSourcePackageRelease(architecturehintlist='any')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True, 'avr': False}, builds)
        self.completeBuilds(builds, {'sparc': False, 'avr': True})
        # The new nominatedarchindep needs to be built, and the previous
        # nominatedarchindep build failed. We end up with two new
        # builds, and arch_indep on nominatedarchindep.
        new_builds = self.createBuilds(spr, self.distroseries2)
        self.assertBuildsMatch({'x32': True, 'sparc': False}, new_builds)

    def test_createForSource_all_with_nai_change(self):
        # If we only need arch-indep binaries and they've already built
        # successfully, no build is created for the new series, even if
        # nominatedarchindep has changed.
        spr = self.factory.makeSourcePackageRelease(architecturehintlist='all')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True}, builds)
        self.completeBuilds(builds, {'sparc': True})
        # Despite there being no build for the new nominatedarchindep,
        # the old arch-indep build is sufficient and no new record is
        # created.
        new_builds = self.createBuilds(spr, self.distroseries2)
        self.assertBuildsMatch({}, new_builds)

    def test_createForSource_all_with_nai_change_and_fail(self):
        # If the previous arch-indep sole build failed, a new arch-indep
        # build is created for nominatedarchindep.
        spr = self.factory.makeSourcePackageRelease(architecturehintlist='all')
        builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({'sparc': True}, builds)
        self.completeBuilds(builds, {'sparc': False})
        # Despite there being no build for the new nominatedarchindep,
        # the old arch-indep build is sufficient and no new record is
        # created.
        new_builds = self.createBuilds(spr, self.distroseries2)
        self.assertBuildsMatch({'x32': True}, new_builds)

    def test_createForSource_all_and_other_archs(self):
        # If a source package specifies both 'all' and a set of
        # architectures that doesn't include nominatedarchindep,
        # arch_indep is set on the available DistroArchSeries with the
        # oldest Processor.
        # This is mostly a hack to avoid hardcoding a preference for
        # the faster x86-family architectures, so we don't accidentally
        # build documentation on hppa.
        spr = self.factory.makeSourcePackageRelease(
            architecturehintlist='all sparc avr')
        builds = self.createBuilds(spr, self.distroseries2)
        self.assertBuildsMatch({'sparc': False, 'avr': True}, builds)
        self.completeBuilds(builds, {'sparc': True, 'avr': True})
        new_builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({}, new_builds)

    def test_createForSource_build_indep_architecture(self):
        # A user defined field of Build-Indep-Architecture provides a
        # custom hint list to override Architecture and
        # nominatedarchindep for arch-indep purposes.
        spr = self.factory.makeSourcePackageRelease(
            architecturehintlist='sparc all',
            user_defined_fields=[('build-indep-architecture', 'avr')])
        builds = self.createBuilds(spr, self.distroseries2)
        self.assertBuildsMatch({'sparc': False, 'avr': True}, builds)
        self.completeBuilds(builds, {'sparc': True, 'avr': True})
        new_builds = self.createBuilds(spr, self.distroseries)
        self.assertBuildsMatch({}, new_builds)


class TestFindBuiltOrPublishedBySourceAndArchive(TestCaseWithFactory):
    """Tests for findBuiltOrPublishedBySourceAndArchive()."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestFindBuiltOrPublishedBySourceAndArchive, self).setUp()
        self.bpbs = getUtility(IBinaryPackageBuildSet)

    def test_trivial(self):
        # Builds with status FULLYBUILT with a matching
        # SourcePackageRelease and Archive are returned.
        bpb1 = self.factory.makeBinaryPackageBuild(
            status=BuildStatus.FULLYBUILT)
        bpb2 = self.factory.makeBinaryPackageBuild(
            source_package_release=bpb1.source_package_release,
            archive=bpb1.archive)
        self.assertEqual(
            {bpb1.distro_arch_series.architecturetag: bpb1},
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb1.source_package_release, bpb1.archive))
        bpb2.updateStatus(BuildStatus.FULLYBUILT)
        self.assertEqual(
            {bpb1.distro_arch_series.architecturetag: bpb1,
             bpb2.distro_arch_series.architecturetag: bpb2},
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb1.source_package_release, bpb1.archive))

    def test_trivial_mismatch(self):
        # Builds for other sources and archives are ignored.
        bpb = self.factory.makeBinaryPackageBuild()
        self.assertEqual(
            {},
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb.source_package_release, self.factory.makeArchive()))
        self.assertEqual(
            {},
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                self.factory.makeSourcePackageRelease(), bpb.archive))

    def test_copies_are_found(self):
        # If a build's binaries are published (with a
        # BinaryPackagePublishingHistory) in another archive, it shows
        # up in requests for that archive.
        bpb1 = self.factory.makeBinaryPackageBuild(
            status=BuildStatus.FULLYBUILT)
        bpr1 = self.factory.makeBinaryPackageRelease(build=bpb1)
        bpb2 = self.factory.makeBinaryPackageBuild(
            source_package_release=bpb1.source_package_release,
            archive=bpb1.archive, status=BuildStatus.FULLYBUILT)
        bpr2 = self.factory.makeBinaryPackageRelease(build=bpb2)

        # A fresh archive sees no builds.
        target = self.factory.makeArchive()
        self.assertEqual(
            {},
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb1.source_package_release, target))

        # But copying one build over makes it appear.
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr1, archive=target)
        self.assertEqual(
            {bpb1.distro_arch_series.architecturetag: bpb1},
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb1.source_package_release, target))

        # Copying the second gives us both.
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr2, archive=target)
        self.assertEqual(
            {bpb1.distro_arch_series.architecturetag: bpb1,
             bpb2.distro_arch_series.architecturetag: bpb2},
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb1.source_package_release, target))
        self.assertEqual(
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb1.source_package_release, bpb1.archive),
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb1.source_package_release, target))

        # A third archive still shows nothing.
        untarget = self.factory.makeArchive()
        self.assertEqual(
            {},
            self.bpbs.findBuiltOrPublishedBySourceAndArchive(
                bpb1.source_package_release, untarget))

    def test_can_find_build_in_derived_distro_parent(self):
        # If a derived distribution inherited its binaries from its
        # parent then findBuiltOrPublishedBySourceAndArchive() should
        # look in the parent to find the build.
        dsp = self.factory.makeDistroSeriesParent()
        parent_archive = dsp.parent_series.main_archive

        # Create a built, published package in the parent archive.
        spr = self.factory.makeSourcePackageRelease(
            architecturehintlist='any')
        parent_source_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr, archive=parent_archive,
            distroseries=dsp.parent_series)
        das = self.factory.makeDistroArchSeries(
            distroseries=dsp.parent_series,
            processor=self.factory.makeProcessor(supports_virtualized=True))
        orig_build = getUtility(IBinaryPackageBuildSet).new(
            spr, parent_archive, das, PackagePublishingPocket.RELEASE,
            status=BuildStatus.FULLYBUILT)
        bpr = self.factory.makeBinaryPackageRelease(build=orig_build)
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr, distroarchseries=das,
            archive=parent_archive)

        # Make an architecture in the derived series with the same
        # archtag as the parent.
        das_derived = self.factory.makeDistroArchSeries(
            dsp.derived_series, architecturetag=das.architecturetag,
            processor=das.processor)
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
        found_build = getUtility(
            IBinaryPackageBuildSet).findBuiltOrPublishedBySourceAndArchive(
                spr, derived_archive).get(das_derived.architecturetag)
        self.assertEqual(orig_build, found_build)
