# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Build features."""

from datetime import datetime, timedelta
import pytz
import unittest

from storm.store import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.testing import LaunchpadZopelessLayer
from lp.services.job.model.job import Job
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.builder import IBuilderSet
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.buildmaster.tests.test_buildbase import (
    TestGetUploadMethodsMixin, TestHandleStatusMixin)
from lp.soyuz.interfaces.binarypackagebuild import (
    IBinaryPackageBuild, IBinaryPackageBuildSet)
from lp.soyuz.interfaces.buildpackagejob import IBuildPackageJob
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.buildpackagejob import BuildPackageJob
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.soyuzbuilddhelpers import WaitingSlave
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestBinaryPackageBuild(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBinaryPackageBuild, self).setUp()
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        gedit_spr = publisher.getPubSource(
            spr_only=True, sourcename="gedit",
            status=PackagePublishingStatus.PUBLISHED)
        self.build = gedit_spr.createBuild(
            distro_arch_series=publisher.distroseries['i386'],
            archive=gedit_spr.upload_archive,
            pocket=gedit_spr.package_upload.pocket)

    def test_providesInterfaces(self):
        # Build provides IPackageBuild and IBuild.
        self.assertProvides(self.build, IPackageBuild)
        self.assertProvides(self.build, IBinaryPackageBuild)

    def test_queueBuild(self):
        # BinaryPackageBuild can create the queue entry for itself.
        bq = self.build.queueBuild()
        self.assertProvides(bq, IBuildQueue)
        self.assertProvides(bq.specific_job, IBuildPackageJob)
        self.failUnlessEqual(self.build.is_virtualized, bq.virtualized)
        self.failIfEqual(None, bq.processor)
        self.failUnless(bq, self.build.buildqueue_record)

    def test_estimateDuration(self):
        # Without previous builds, a negligable package size estimate is 60s
        self.assertEqual(60, self.build.estimateDuration().seconds)

    def create_previous_build(self, duration):
        spr = self.build.source_package_release
        build = spr.createBuild(
            distro_arch_series=self.build.distro_arch_series,
            archive=spr.upload_archive, pocket=spr.package_upload.pocket)
        build.status = BuildStatus.FULLYBUILT
        now = datetime.now(pytz.UTC)
        build.date_finished = now
        build.date_started = now - timedelta(seconds=duration)
        return build

    def test_estimateDuration_with_history(self):
        # Previous builds of the same source are used for estimates.
        self.create_previous_build(335)
        self.assertEqual(335, self.build.estimateDuration().seconds)

    def test_estimateDuration_with_bad_history(self):
        # If the latest matching build has bad data, ignore it.
        # See bug 589068.
        previous_build = self.create_previous_build(335)
        previous_build.date_started = None
        self.assertEqual(60, self.build.estimateDuration().seconds)


    def addFakeBuildLog(self):
        lfa = self.factory.makeLibraryFileAlias('mybuildlog.txt')
        removeSecurityProxy(self.build).log = lfa

    def test_log_url(self):
        # The log URL for a binary package build will use
        # the distribution source package release when the context
        # is not a PPA or a copy archive.
        self.addFakeBuildLog()
        self.failUnlessEqual(
            'http://launchpad.dev/ubuntutest/+source/'
            'gedit/666/+build/%d/+files/mybuildlog.txt' % (
                self.build.package_build.build_farm_job.id),
            self.build.log_url)

    def test_log_url_ppa(self):
        # On the other hand, ppa or copy builds will have a url in the
        # context of the archive.
        self.addFakeBuildLog()
        ppa_owner = self.factory.makePerson(name="joe")
        removeSecurityProxy(self.build).archive = self.factory.makeArchive(
            owner=ppa_owner, name="myppa")
        self.failUnlessEqual(
            'http://launchpad.dev/~joe/'
            '+archive/myppa/+build/%d/+files/mybuildlog.txt' % (
                self.build.build_farm_job.id),
            self.build.log_url)

    def test_adapt_from_build_farm_job(self):
        # An `IBuildFarmJob` can be adapted to an IBinaryPackageBuild
        # if it has the correct job type.
        build_farm_job = self.build.build_farm_job
        store = Store.of(build_farm_job)
        store.flush()

        self.failUnlessEqual(self.build, build_farm_job.getSpecificJob())

    def test_adapt_from_build_farm_job_prefetching(self):
        # The package_build is prefetched for efficiency.
        build_farm_job = self.build.build_farm_job

        # We clear the cache to avoid getting cached objects where
        # they would normally be queries.
        store = Store.of(build_farm_job)
        store.flush()
        store.reset()

        binary_package_build = build_farm_job.getSpecificJob()

        self.assertStatementCount(
            0, getattr, binary_package_build, "package_build")
        self.assertStatementCount(
            0, getattr, binary_package_build, "build_farm_job")

    def test_getSpecificJob_noop(self):
        # If getSpecificJob is called on the binary build it is a noop.
        store = Store.of(self.build)
        store.flush()
        self.assertStatementCount(
            0, self.build.getSpecificJob)


class TestBuildUpdateDependencies(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def _setupSimpleDepwaitContext(self):
        """Use `SoyuzTestPublisher` to setup a simple depwait context.

        Return an `IBinaryPackageBuild` in MANUALDEWAIT state and depending on a
        binary that exists and is reachable.
        """
        test_publisher = SoyuzTestPublisher()
        test_publisher.prepareBreezyAutotest()

        depwait_source = test_publisher.getPubSource(
            sourcename='depwait-source')

        test_publisher.getPubBinaries(
            binaryname='dep-bin',
            status=PackagePublishingStatus.PUBLISHED)

        [depwait_build] = depwait_source.createMissingBuilds()
        depwait_build.status = BuildStatus.MANUALDEPWAIT
        depwait_build.dependencies = u'dep-bin'

        return depwait_build

    def testBuildqueueRemoval(self):
        """Test removing buildqueue items.

        Removing a Buildqueue row should also remove its associated
        BuildPackageJob and Job rows.
        """
        # Create a build in depwait.
        depwait_build = self._setupSimpleDepwaitContext()
        depwait_build_id = depwait_build.id

        # Grab the relevant db records for later comparison.
        store = Store.of(depwait_build)
        build_package_job = store.find(
            BuildPackageJob,
            depwait_build.id == BuildPackageJob.build).one()
        build_package_job_id = build_package_job.id
        job_id = store.find(Job, Job.id == build_package_job.job.id).one().id
        build_queue_id = store.find(
            BuildQueue, BuildQueue.job == job_id).one().id

        depwait_build.buildqueue_record.destroySelf()

        # Test that the records above no longer exist in the db.
        self.assertEqual(
            store.find(
                BuildPackageJob,
                BuildPackageJob.id == build_package_job_id).count(),
            0)
        self.assertEqual(
            store.find(Job, Job.id == job_id).count(),
            0)
        self.assertEqual(
            store.find(BuildQueue, BuildQueue.id == build_queue_id).count(),
            0)
        # But the build itself still exists.
        self.assertEqual(
            store.find(
                BinaryPackageBuild,
                BinaryPackageBuild.id == depwait_build_id).count(),
            1)


    def testUpdateDependenciesWorks(self):
        # Calling `IBinaryPackageBuild.updateDependencies` makes the build
        # record ready for dispatch.
        depwait_build = self._setupSimpleDepwaitContext()
        self.layer.txn.commit()
        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, '')

    def testInvalidDependencies(self):
        # Calling `IBinaryPackageBuild.updateDependencies` on a build with
        # invalid 'dependencies' raises an AssertionError.
        # Anything not following '<name> [([relation] <version>)][, ...]'
        depwait_build = self._setupSimpleDepwaitContext()

        # None is not a valid dependency values.
        depwait_build.dependencies = None
        self.assertRaises(
            AssertionError, depwait_build.updateDependencies)

        # Missing 'name'.
        depwait_build.dependencies = u'(>> version)'
        self.assertRaises(
            AssertionError, depwait_build.updateDependencies)

        # Missing 'version'.
        depwait_build.dependencies = u'name (>>)'
        self.assertRaises(
            AssertionError, depwait_build.updateDependencies)

        # Missing comman between dependencies.
        depwait_build.dependencies = u'name1 name2'
        self.assertRaises(
            AssertionError, depwait_build.updateDependencies)

    def testBug378828(self):
        # `IBinaryPackageBuild.updateDependencies` copes with the
        # scenario where the corresponding source publication is not
        # active (deleted) and the source original component is not a
        # valid ubuntu component.
        depwait_build = self._setupSimpleDepwaitContext()

        spr = depwait_build.source_package_release
        depwait_build.current_source_publication.requestDeletion(
            spr.creator)
        contrib = getUtility(IComponentSet).new('contrib')
        removeSecurityProxy(spr).component = contrib

        self.layer.txn.commit()
        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, '')


class BaseTestCaseWithThreeBuilds(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Publish some builds for the test archive."""
        super(BaseTestCaseWithThreeBuilds, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create three builds for the publisher's default
        # distroseries.
        self.builds = []
        self.sources = []
        gedit_src_hist = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        self.builds += gedit_src_hist.createMissingBuilds()
        self.sources.append(gedit_src_hist)

        firefox_src_hist = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED)
        self.builds += firefox_src_hist.createMissingBuilds()
        self.sources.append(firefox_src_hist)

        gtg_src_hist = self.publisher.getPubSource(
            sourcename="getting-things-gnome",
            status=PackagePublishingStatus.PUBLISHED)
        self.builds += gtg_src_hist.createMissingBuilds()
        self.sources.append(gtg_src_hist)


class TestBuildSetGetBuildsForArchive(BaseTestCaseWithThreeBuilds):

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestBuildSetGetBuildsForArchive, self).setUp()

        # Short-cuts for our tests.
        self.archive = self.publisher.distroseries.main_archive
        self.build_set = getUtility(IBinaryPackageBuildSet)

    def test_getBuildsForArchive_no_params(self):
        # All builds should be returned when called without filtering
        builds = self.build_set.getBuildsForArchive(self.archive)
        self.assertContentEqual(builds, self.builds)

    def test_getBuildsForArchive_by_arch_tag(self):
        # Results can be filtered by architecture tag.
        i386_builds = self.builds[:]
        hppa_build = i386_builds.pop()
        removeSecurityProxy(hppa_build).distro_arch_series = (
            self.publisher.distroseries['hppa'])

        builds = self.build_set.getBuildsForArchive(self.archive,
                                                    arch_tag="i386")
        self.assertContentEqual(builds, i386_builds)


class TestBuildSetGetBuildsForBuilder(BaseTestCaseWithThreeBuilds):

    def setUp(self):
        super(TestBuildSetGetBuildsForBuilder, self).setUp()

        # Short-cuts for our tests.
        self.build_set = getUtility(IBinaryPackageBuildSet)

        # Create a 386 builder
        owner = self.factory.makePerson()
        processor_family = ProcessorFamilySet().getByProcessorName('386')
        processor = processor_family.processors[0]
        builder_set = getUtility(IBuilderSet)

        self.builder = builder_set.new(
            processor, 'http://example.com', 'Newbob', 'New Bob the Builder',
            'A new and improved bob.', owner)

        # Ensure that our builds were all built by the test builder.
        for build in self.builds:
            build.builder = self.builder

    def test_getBuildsForBuilder_no_params(self):
        # All builds should be returned when called without filtering
        builds = self.build_set.getBuildsForBuilder(self.builder.id)
        self.assertContentEqual(builds, self.builds)

    def test_getBuildsForBuilder_by_arch_tag(self):
        # Results can be filtered by architecture tag.
        i386_builds = self.builds[:]
        hppa_build = i386_builds.pop()
        removeSecurityProxy(hppa_build).distro_arch_series = (
            self.publisher.distroseries['hppa'])

        builds = self.build_set.getBuildsForBuilder(self.builder.id,
                                                    arch_tag="i386")
        self.assertContentEqual(builds, i386_builds)


class TestStoreBuildInfo(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestStoreBuildInfo, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        gedit_src_hist = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        self.build = gedit_src_hist.createMissingBuilds()[0]

        self.builder = self.factory.makeBuilder()
        self.builder.setSlaveForTesting(WaitingSlave('BuildStatus.OK'))
        self.build.buildqueue_record.builder = self.builder
        self.build.buildqueue_record.setDateStarted(UTC_NOW)

    def testDependencies(self):
        """Verify that storeBuildInfo sets any dependencies."""
        self.build.storeBuildInfo(
            self.build, None, {'dependencies': 'somepackage'})
        self.assertIsNot(None, self.build.log)
        self.assertEqual(self.builder, self.build.builder)
        self.assertEqual(u'somepackage', self.build.dependencies)
        self.assertIsNot(None, self.build.date_finished)

    def testWithoutDependencies(self):
        """Verify that storeBuildInfo clears the build's dependencies."""
        # Set something just to make sure that storeBuildInfo actually
        # empties it.
        self.build.dependencies = u'something'
        self.build.storeBuildInfo(self.build, None, {})
        self.assertIsNot(None, self.build.log)
        self.assertEqual(self.builder, self.build.builder)
        self.assertIs(None, self.build.dependencies)
        self.assertIsNot(None, self.build.date_finished)


class MakeBinaryPackageBuildMixin:
    """Provide the makeBuild method returning a queud build."""

    def makeBuild(self):
        test_publisher = SoyuzTestPublisher()
        test_publisher.prepareBreezyAutotest()
        binaries = test_publisher.getPubBinaries()
        return binaries[0].binarypackagerelease.build


class TestGetUploadMethodsForBinaryPackageBuild(
    MakeBinaryPackageBuildMixin, TestGetUploadMethodsMixin,
    TestCaseWithFactory):
    """IBuildBase.getUpload-related methods work with binary builds."""


class TestHandleStatusForBinaryPackageBuild(
    MakeBinaryPackageBuildMixin, TestHandleStatusMixin, TestCaseWithFactory):
    """IBuildBase.handleStatus works with binary builds."""


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
