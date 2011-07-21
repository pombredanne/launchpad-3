# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test implementations of the IHasBuildRecords interface."""

from datetime import (
    datetime,
    timedelta,
    )
import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.builder import IBuilderSet
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    )
from lp.buildmaster.interfaces.packagebuild import IPackageBuildSource
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.sourcepackage import SourcePackage
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.buildrecords import (
    IHasBuildRecords,
    IncompatibleArguments,
    )
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.test_binarypackagebuild import BaseTestCaseWithThreeBuilds
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestHasBuildRecordsInterface(BaseTestCaseWithThreeBuilds):
    """Tests the implementation of IHasBuildRecords by the
       Distribution content class by default.

       Inherit and set self.context to another content class to test
       other implementations.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestHasBuildRecordsInterface, self).setUp()
        self.context = self.publisher.distroseries.distribution

    def testProvidesHasBuildRecords(self):
        # Ensure that the context does in fact provide IHasBuildRecords
        self.assertProvides(self.context, IHasBuildRecords)

    def test_getBuildRecords_no_archs(self):
        # getBuildRecords() called without any arguments returns all builds.
        builds = self.context.getBuildRecords()
        self.assertContentEqual(builds, self.builds)

    def test_getBuildRecords_by_arch_tag(self):
        # Build records can be filtered by architecture tag.

        # Target one of the builds to hppa so that we have three builds
        # in total, two of which are i386 and one hppa.
        i386_builds = self.builds[:]
        hppa_build = i386_builds.pop()
        removeSecurityProxy(
            hppa_build).distro_arch_series = self.publisher.distroseries[
                'hppa']

        builds = self.context.getBuildRecords(arch_tag="i386")
        self.assertContentEqual(i386_builds, builds)


class TestDistributionHasBuildRecords(TestCaseWithFactory):
    """Populate a distroseries with builds"""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDistributionHasBuildRecords, self).setUp()
        self.admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        # Create the machinery we need to create builds, such as
        # DistroArchSeries and builders.
        self.pf_one = self.factory.makeProcessorFamily()
        pf_proc_1 = self.pf_one.addProcessor(
            self.factory.getUniqueString(), '', '')
        self.pf_two = self.factory.makeProcessorFamily()
        pf_proc_2 = self.pf_two.addProcessor(
            self.factory.getUniqueString(), '', '')
        self.distroseries = self.factory.makeDistroSeries()
        self.distribution = self.distroseries.distribution
        self.das_one = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processorfamily=self.pf_one,
            supports_virtualized=True)
        self.das_two = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processorfamily=self.pf_two,
            supports_virtualized=True)
        self.archive = self.factory.makeArchive(
            distribution=self.distroseries.distribution,
            purpose=ArchivePurpose.PRIMARY)
        self.arch_ids = [arch.id for arch in self.distroseries.architectures]
        with person_logged_in(self.admin):
            self.publisher = SoyuzTestPublisher()
            self.publisher.prepareBreezyAutotest()
            self.distroseries.nominatedarchindep = self.das_one
            self.publisher.addFakeChroots(distroseries=self.distroseries)
            self.builder_one = self.factory.makeBuilder(processor=pf_proc_1)
            self.builder_two = self.factory.makeBuilder(processor=pf_proc_2)
        self.builds = []
        self.createBuilds()

    def createBuilds(self):
        for i in range(5):
            # Create some test builds.
            spph = self.publisher.getPubSource(
                sourcename=self.factory.getUniqueString(),
                version="%s.%s" % (self.factory.getUniqueInteger(), i),
                distroseries=self.distroseries, architecturehintlist='any')
            builds = spph.createMissingBuilds()
            for b in builds:
                if i == 4:
                    b.status = BuildStatus.FAILEDTOBUILD
                else:
                    b.status = BuildStatus.FULLYBUILT
                b.buildqueue_record.destroySelf()
                b.date_started = datetime.now(pytz.UTC)
                b.date_finished = b.date_started + timedelta(minutes=5)
            self.builds += builds

    def test_get_build_records(self):
        # A Distribution also implements IHasBuildRecords.
        builds = self.distribution.getBuildRecords().count()
        self.assertEquals(10, builds)

class TestDistroSeriesHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the DistroSeries implementation of IHasBuildRecords."""

    def setUp(self):
        super(TestDistroSeriesHasBuildRecords, self).setUp()

        self.context = self.publisher.distroseries


class TestDistroArchSeriesHasBuildRecords(TestDistributionHasBuildRecords):
    """Test the DistroArchSeries implementation of IHasBuildRecords."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDistroArchSeriesHasBuildRecords, self).setUp()

    def test_distroarchseries(self):
        # We can fetch builds records from a DistroArchSeries.
        builds = self.das_one.getBuildRecords().count()
        self.assertEquals(5, builds)
        builds = self.das_one.getBuildRecords(
            build_state=BuildStatus.FULLYBUILT).count()
        self.assertEquals(4, builds)
        spn = self.builds[0].source_package_release.sourcepackagename.name
        builds = self.das_one.getBuildRecords(name=spn).count()
        self.assertEquals(1, builds)
        builds = self.das_one.getBuildRecords(
            pocket=PackagePublishingPocket.RELEASE).count()
        self.assertEquals(5, builds)
        builds = self.das_one.getBuildRecords(
            pocket=PackagePublishingPocket.UPDATES).count()
        self.assertEquals(0, builds)


class TestArchiveHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the Archive implementation of IHasBuildRecords."""

    def setUp(self):
        super(TestArchiveHasBuildRecords, self).setUp()

        self.context = self.publisher.distroseries.main_archive

    def test_binary_only_false(self):
        # An archive can optionally return the more general
        # package build objects.

        # Until we have different IBuildFarmJob types implemented, we
        # can only test this by creating a lone PackageBuild of a
        # different type.
        getUtility(IPackageBuildSource).new(
            job_type=BuildFarmJobType.RECIPEBRANCHBUILD, virtualized=True,
            archive=self.context, pocket=PackagePublishingPocket.RELEASE)

        builds = self.context.getBuildRecords(binary_only=True)
        self.failUnlessEqual(3, builds.count())

        builds = self.context.getBuildRecords(binary_only=False)
        self.failUnlessEqual(4, builds.count())

    def test_incompatible_arguments(self):
        # binary_only=False is incompatible with arch_tag and name.
        self.failUnlessRaises(
            IncompatibleArguments, self.context.getBuildRecords,
            binary_only=False, arch_tag="anything")
        self.failUnlessRaises(
            IncompatibleArguments, self.context.getBuildRecords,
            binary_only=False, name="anything")


class TestBuilderHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the Builder implementation of IHasBuildRecords."""

    def setUp(self):
        super(TestBuilderHasBuildRecords, self).setUp()

        # Create a 386 builder
        owner = self.factory.makePerson()
        processor_family = ProcessorFamilySet().getByProcessorName('386')
        processor = processor_family.processors[0]
        builder_set = getUtility(IBuilderSet)
        self.context = builder_set.new(
            processor, 'http://example.com', 'Newbob', 'New Bob the Builder',
            'A new and improved bob.', owner)

        # Ensure that our builds were all built by the test builder.
        for build in self.builds:
            build.builder = self.context

    def test_binary_only_false(self):
        # A builder can optionally return the more general
        # build farm job objects.

        # Until we have different IBuildFarmJob types implemented, we
        # can only test this by creating a lone IBuildFarmJob of a
        # different type.
        from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type=BuildFarmJobType.RECIPEBRANCHBUILD, virtualized=True,
            status=BuildStatus.BUILDING)
        removeSecurityProxy(build_farm_job).builder = self.context

        builds = self.context.getBuildRecords(binary_only=True)
        binary_only_count = builds.count()

        self.assertTrue(
            all([IBinaryPackageBuild.providedBy(build) for build in builds]))

        builds = self.context.getBuildRecords(binary_only=False)
        all_count = builds.count()

        self.assertFalse(
            any([IBinaryPackageBuild.providedBy(build) for build in builds]))
        self.assertTrue(
            all([IBuildFarmJob.providedBy(build) for build in builds]))
        self.assertBetween(0, binary_only_count, all_count)

    def test_incompatible_arguments(self):
        # binary_only=False is incompatible with arch_tag and name.
        self.failUnlessRaises(
            IncompatibleArguments, self.context.getBuildRecords,
            binary_only=False, arch_tag="anything")
        self.failUnlessRaises(
            IncompatibleArguments, self.context.getBuildRecords,
            binary_only=False, name="anything")


class TestSourcePackageHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the SourcePackage implementation of IHasBuildRecords."""

    def setUp(self):
        super(TestSourcePackageHasBuildRecords, self).setUp()
        gedit_name = self.builds[0].source_package_release.sourcepackagename
        self.context = SourcePackage(
            gedit_name, self.builds[0].distro_arch_series.distroseries)

        # Convert the other two builds to be builds of
        # gedit as well so that the one source package (gedit) will have
        # three builds.
        for build in self.builds[1:3]:
            spr = build.source_package_release
            removeSecurityProxy(spr).sourcepackagename = gedit_name

        # Set them as sucessfully built
        for build in self.builds:
            build.status = BuildStatus.FULLYBUILT
            build.buildqueue_record.destroySelf()
            removeSecurityProxy(build).date_created = (
                self.factory.getUniqueDate())
            build.date_started = datetime.now(pytz.UTC)
            build.date_finished = build.date_started + timedelta(minutes=5)

    def test_get_build_records(self):
        # We can fetch builds records from a SourcePackage.
        builds = self.context.getBuildRecords(
            build_state=BuildStatus.FULLYBUILT).count()
        self.assertEquals(3, builds)
        builds = self.context.getBuildRecords(
            pocket=PackagePublishingPocket.RELEASE).count()
        self.assertEquals(3, builds)
        builds = self.context.getBuildRecords(
            pocket=PackagePublishingPocket.UPDATES).count()
        self.assertEquals(0, builds)

    def test_ordering_date(self):
        # Build records returned are ordered by creation date.
        builds = self.context.getBuildRecords(
            build_state=BuildStatus.FULLYBUILT)
        date_created = [build.date_created for build in builds]
        self.assertTrue(date_created[0] > date_created[1] > date_created[2])

    def test_ordering_lastscore(self):
        # PENDING build records returned are ordered by score.
        spph = self.factory.makeSourcePackagePublishingHistory()
        spr = spph.sourcepackagerelease
        source_package = SourcePackage.new(
            spph.sourcepackagerelease.sourcepackagename, spph.distroseries)
        build1 = self.factory.makeBinaryPackageBuild(
            source_package_release=spr)
        build2 = self.factory.makeBinaryPackageBuild(
            source_package_release=spr)
        build1.queueBuild()
        build2.queueBuild()
        build1.buildqueue_record.lastscore = 10
        build2.buildqueue_record.lastscore = 1000
        builds = list(source_package.getBuildRecords())
        self.assertEquals([build2, build1], builds)

    def test_copy_archive_without_leak(self):
        # If source publications are copied to a .COPY archive, they don't
        # "leak" into SourcePackage.getBuildRecords().
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        # Set up a distroseries and related bits, so we can create builds.
        source_name = self.factory.getUniqueString()
        spn = self.factory.makeSourcePackageName(name=source_name)
        pf = self.factory.makeProcessorFamily()
        pf_proc = pf.addProcessor(self.factory.getUniqueString(), '', '')
        distroseries = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(
            distroseries=distroseries, processorfamily=pf,
            supports_virtualized=True)
        with person_logged_in(admin):
            publisher = SoyuzTestPublisher()
            publisher.prepareBreezyAutotest()
            publisher.addFakeChroots(distroseries=distroseries)
            distroseries.nominatedarchindep = das
            builder = self.factory.makeBuilder(processor=pf_proc)
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=spn, distroseries=distroseries)
        spph.createMissingBuilds()
        # Create a copy archive.
        copy = self.factory.makeArchive(
            purpose=ArchivePurpose.COPY,
            distribution=distroseries.distribution)
        # And copy the publication into it.
        copy_spph = spph.copyTo(
            distroseries, PackagePublishingPocket.RELEASE, copy)
        [copy_build] = copy_spph.createMissingBuilds()
        builds = copy.getBuildRecords()
        self.assertEquals([copy_build], list(builds))
        source = SourcePackage(spn, spph.distroseries)
        # SourcePackage.getBuildRecords() doesn't have two build records.
        builds = source.getBuildRecords().count()
        self.assertEquals(1, builds)
