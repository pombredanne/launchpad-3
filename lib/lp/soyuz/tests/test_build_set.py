# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.archivearch import IArchiveArchSet
from lp.soyuz.interfaces.binarypackagebuild import (
    BuildSetStatus,
    IBinaryPackageBuildSet,
    )
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuildSet
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
        self.processor_one = self.factory.makeProcessor()
        self.processor_two = self.factory.makeProcessor()
        self.distroseries = self.factory.makeDistroSeries()
        self.distribution = self.distroseries.distribution
        self.das_one = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processor=self.processor_one,
            supports_virtualized=True)
        self.das_two = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processor=self.processor_two,
            supports_virtualized=True)
        self.archive = self.factory.makeArchive(
            distribution=self.distroseries.distribution,
            purpose=ArchivePurpose.PRIMARY)
        with person_logged_in(self.admin):
            self.publisher = SoyuzTestPublisher()
            self.publisher.prepareBreezyAutotest()
            self.distroseries.nominatedarchindep = self.das_one
            self.publisher.addFakeChroots(distroseries=self.distroseries)
            self.builder_one = self.factory.makeBuilder(
                processors=[self.processor_one])
            self.builder_two = self.factory.makeBuilder(
                processors=[self.processor_two])
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

    def test_get_for_distro_distribution(self):
        # Test fetching builds for a distro's main archives
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution)
        self.assertEquals(set.count(), 10)

    def test_get_for_distro_distroseries(self):
        # Test fetching builds for a distroseries' main archives
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distroseries)
        self.assertEquals(set.count(), 10)

    def test_get_for_distro_distroarchseries(self):
        # Test fetching builds for a distroarchseries' main archives
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.das_one)
        self.assertEquals(set.count(), 5)

    def test_get_for_distro_filter_build_status(self):
        # The result can be filtered based on the build status
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, status=BuildStatus.FULLYBUILT)
        self.assertEquals(set.count(), 8)

    def test_get_for_distro_filter_name(self):
        # The result can be filtered based on the name
        self.setUpBuilds()
        spn = self.builds[2].source_package_release.sourcepackagename.name
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, name=spn)
        self.assertEquals(set.count(), 2)

    def test_get_for_distro_filter_pocket(self):
        # The result can be filtered based on the pocket of the build
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, pocket=PackagePublishingPocket.RELEASE)
        self.assertEquals(set.count(), 10)
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, pocket=PackagePublishingPocket.UPDATES)
        self.assertEquals(set.count(), 0)

    def test_get_for_distro_filter_arch_tag(self):
        # The result can be filtered based on the archtag of the build
        self.setUpBuilds()
        set = getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self.distribution, arch_tag=self.das_one.architecturetag)
        self.assertEquals(set.count(), 5)

    def test_get_status_summary_for_builds(self):
        # We can query for the status summary of a number of builds
        self.setUpBuilds()
        relevant_builds = [self.builds[0], self.builds[2], self.builds[-2]]
        summary = getUtility(
            IBinaryPackageBuildSet).getStatusSummaryForBuilds(
                relevant_builds)
        self.assertEquals(summary['status'], BuildSetStatus.FAILEDTOBUILD)
        self.assertEquals(summary['builds'], [self.builds[-2]])

    def test_preload_data(self):
        # The BuildSet class allows data to be preloaded
        # Note, it is an internal method, so we have to push past the security
        # proxy
        self.setUpBuilds()
        build_ids = [self.builds[i] for i in (0, 1, 2, 3)]
        rset = removeSecurityProxy(
            getUtility(IBinaryPackageBuildSet))._prefetchBuildData(build_ids)
        self.assertEquals(len(rset), 4)

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
        self.assertEquals(sorted(expected_titles), sorted(build_titles))

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
        self.assertEquals(sorted(expected_titles), sorted(build_titles))
        builds = getUtility(
            IBinaryPackageBuildSet).getBuildsBySourcePackageRelease(
                ids, buildstate=BuildStatus.CHROOTWAIT)
        self.assertEquals([], list(builds))

    def test_no_get_builds_by_source_package_release(self):
        # If no ids or None are passed into .getBuildsBySourcePackageRelease,
        # an empty list is returned.
        builds = getUtility(
            IBinaryPackageBuildSet).getBuildsBySourcePackageRelease(None)
        self.assertEquals([], builds)
        builds = getUtility(
            IBinaryPackageBuildSet).getBuildsBySourcePackageRelease([])
        self.assertEquals([], builds)


class BuildRecordCreationTests(TestNativePublishingBase):
    """Test the creation of build records."""

    def setUp(self):
        super(BuildRecordCreationTests, self).setUp()
        self.distro = self.factory.makeDistribution()
        self.distroseries = self.factory.makeDistroSeries(
            distribution=self.distro, name="crazy")
        self.archive = self.factory.makeArchive()
        self.avr = self.factory.makeProcessor(name="avr2001", restricted=True)
        self.avr_distroarch = self.factory.makeDistroArchSeries(
            architecturetag='avr', processor=self.avr,
            distroseries=self.distroseries, supports_virtualized=True)
        self.sparc = self.factory.makeProcessor(
            name="sparc64", restricted=False)
        self.sparc_distroarch = self.factory.makeDistroArchSeries(
            architecturetag='sparc', processor=self.sparc,
            distroseries=self.distroseries, supports_virtualized=True)
        self.distroseries.nominatedarchindep = self.sparc_distroarch
        self.addFakeChroots(self.distroseries)

    def getPubSource(self, architecturehintlist):
        """Return a mock source package publishing record for the archive
        and architecture used in this testcase.

        :param architecturehintlist: Architecture hint list
            (e.g. "i386 amd64")
        """
        return super(BuildRecordCreationTests, self).getPubSource(
            archive=self.archive, distroseries=self.distroseries,
            architecturehintlist=architecturehintlist)

    def test__getAllowedArchitectures_restricted(self):
        """Test _getAllowedArchitectures doesn't return unrestricted
        archs.

        For a normal archive, only unrestricted architectures should
        be used.
        """
        available_archs = [self.sparc_distroarch, self.avr_distroarch]
        pubrec = self.getPubSource(architecturehintlist='any')
        self.assertEqual(
            [self.sparc_distroarch],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                pubrec.archive, available_archs))

    def test__getAllowedArchitectures_restricted_override(self):
        """Test _getAllowedArchitectures honors overrides of restricted archs.

        Restricted architectures should only be allowed if there is
        an explicit ArchiveArch association with the archive.
        """
        available_archs = [self.sparc_distroarch, self.avr_distroarch]
        getUtility(IArchiveArchSet).new(self.archive, self.avr)
        pubrec = self.getPubSource(architecturehintlist='any')
        self.assertEqual(
            [self.sparc_distroarch, self.avr_distroarch],
            BinaryPackageBuildSet()._getAllowedArchitectures(
                pubrec.archive, available_archs))

    def test_createMissingBuilds_restricts_any(self):
        """createMissingBuilds() should limit builds targeted at 'any'
        architecture to those allowed for the archive.
        """
        pubrec = self.getPubSource(architecturehintlist='any')
        builds = pubrec.createMissingBuilds()
        self.assertEqual(1, len(builds))
        self.assertEqual(self.sparc_distroarch, builds[0].distro_arch_series)

    def test_createMissingBuilds_restricts_explicitlist(self):
        """createMissingBuilds() limits builds targeted at a variety of
        architectures architecture to those allowed for the archive.
        """
        pubrec = self.getPubSource(architecturehintlist='sparc i386 avr')
        builds = pubrec.createMissingBuilds()
        self.assertEqual(1, len(builds))
        self.assertEqual(self.sparc_distroarch, builds[0].distro_arch_series)

    def test_createMissingBuilds_restricts_all(self):
        """createMissingBuilds() should limit builds targeted at 'all'
        architectures to the nominated independent architecture,
        if that is allowed for the archive.
        """
        pubrec = self.getPubSource(architecturehintlist='all')
        builds = pubrec.createMissingBuilds()
        self.assertEqual(1, len(builds))
        self.assertEqual(self.sparc_distroarch, builds[0].distro_arch_series)

    def test_createMissingBuilds_restrict_override(self):
        """createMissingBuilds() should limit builds targeted at 'any'
        architecture to architectures that are unrestricted or
        explicitly associated with the archive.
        """
        getUtility(IArchiveArchSet).new(self.archive, self.avr)
        pubrec = self.getPubSource(architecturehintlist='any')
        builds = pubrec.createMissingBuilds()
        self.assertEqual(2, len(builds))
        self.assertEqual(self.avr_distroarch, builds[0].distro_arch_series)
        self.assertEqual(self.sparc_distroarch, builds[1].distro_arch_series)


class TestFindBySourceAndLocation(TestCaseWithFactory):
    """Tests for SourcePackageRelease.findBuildsByArchitecture."""

    layer = ZopelessDatabaseLayer

    def test_finds_build_with_matching_pub(self):
        # _findBySourceAndLocation finds builds for a source package
        # release.  In particular, an arch-independent BPR is published in
        # multiple architectures.  But findBuildsByArchitecture only counts
        # the publication for the same architecture it was built in.
        distroseries = self.factory.makeDistroSeries()
        archive = distroseries.main_archive
        # The series has a nominated arch-indep architecture.
        distroseries.nominatedarchindep = self.factory.makeDistroArchSeries(
            distroseries=distroseries)

        bpb = self.factory.makeBinaryPackageBuild(
            distroarchseries=distroseries.nominatedarchindep)
        bpr = self.factory.makeBinaryPackageRelease(
            build=bpb, architecturespecific=False)
        spr = bpr.build.source_package_release

        # The series also has other architectures.
        self.factory.makeDistroArchSeries(distroseries=distroseries)

        # makeBinaryPackagePublishingHistory will actually publish an
        # arch-indep BPR everywhere.
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr, archive=archive,
            distroarchseries=distroseries.nominatedarchindep)

        naked_spr = removeSecurityProxy(spr)
        self.assertEqual(
            {distroseries.nominatedarchindep.architecturetag: bpr.build},
            BinaryPackageBuildSet()._findBySourceAndLocation(
                naked_spr, archive, distroseries))
