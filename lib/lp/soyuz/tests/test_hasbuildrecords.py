# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test implementations of the IHasBuildRecords interface."""

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.buildmaster.enums import BuildFarmJobType
from lp.buildmaster.interfaces.builder import IBuilderSet
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    )
from lp.buildmaster.interfaces.packagebuild import IPackageBuildSource
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.sourcepackage import SourcePackage
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.buildrecords import (
    IHasBuildRecords,
    IncompatibleArguments,
    )
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.test_binarypackagebuild import BaseTestCaseWithThreeBuilds


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


class TestDistroSeriesHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the DistroSeries implementation of IHasBuildRecords."""

    def setUp(self):
        super(TestDistroSeriesHasBuildRecords, self).setUp()

        self.context = self.publisher.distroseries


class TestDistroArchSeriesHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the DistroArchSeries implementation of IHasBuildRecords."""

    def setUp(self):
        super(TestDistroArchSeriesHasBuildRecords, self).setUp()

        self.context = self.publisher.distroseries['i386']


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
        from lp.buildmaster.enums import BuildStatus
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
            gedit_name,
            self.builds[0].distro_arch_series.distroseries)

        # Convert the other two builds to be builds of
        # gedit as well so that the one source package (gedit) will have
        # three builds.
        for build in self.builds[1:3]:
            spr = build.source_package_release
            removeSecurityProxy(spr).sourcepackagename = gedit_name
