# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Builder features."""

import os
import signal
import tempfile
import xmlrpclib

from testtools.deferredruntest import (
    assert_fails_with,
    AsynchronousDeferredRunTest,
    AsynchronousDeferredRunTestForBrokenTwisted,
    SynchronousDeferredRunTest,
    )

from twisted.internet.defer import (
    CancelledError,
    DeferredList,
    )
from twisted.internet.task import Clock
from twisted.python.failure import Failure
from twisted.web.client import getPage

from zope.component import getUtility
from zope.security.proxy import (
    isinstance as zope_isinstance,
    removeSecurityProxy,
    )

from canonical.buildd.slave import BuilderStatus
from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.builder import (
    CannotFetchFile,
    IBuilder,
    IBuilderSet,
    )
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.interfaces.builder import CannotResumeHost
from lp.buildmaster.model.builder import (
    BuilderSlave,
    ProxyWithConnectionTimeout,
    )
from lp.buildmaster.model.buildfarmjobbehavior import IdleBuildBehavior
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.buildmaster.tests.mock_slaves import (
    AbortedSlave,
    AbortingSlave,
    BrokenSlave,
    BuildingSlave,
    CorruptBehavior,
    DeadProxy,
    LostBuildingBrokenSlave,
    make_publisher,
    MockBuilder,
    OkSlave,
    SlaveTestHelpers,
    TrivialBehavior,
    WaitingSlave,
    )
from lp.services.job.interfaces.job import JobStatus
from lp.services.log.logger import BufferLogger
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.model.binarypackagebuildbehavior import (
    BinaryPackageBuildBehavior,
    )
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


class TestBuilderBasics(TestCaseWithFactory):
    """Basic unit tests for `Builder`."""

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        # Builder provides IBuilder
        builder = self.factory.makeBuilder()
        self.assertProvides(builder, IBuilder)

    def test_default_values(self):
        builder = self.factory.makeBuilder()
        # Make sure the Storm cache gets the values that the database
        # initializes.
        flush_database_updates()
        self.assertEqual(0, builder.failure_count)

    def test_getCurrentBuildFarmJob(self):
        bq = self.factory.makeSourcePackageRecipeBuildJob(3333)
        builder = self.factory.makeBuilder()
        bq.markAsBuilding(builder)
        self.assertEqual(
            bq, builder.getCurrentBuildFarmJob().buildqueue_record)

    def test_getBuildQueue(self):
        buildqueueset = getUtility(IBuildQueueSet)
        active_jobs = buildqueueset.getActiveBuildJobs()
        [active_job] = active_jobs
        builder = active_job.builder

        bq = builder.getBuildQueue()
        self.assertEqual(active_job, bq)

        active_job.builder = None
        bq = builder.getBuildQueue()
        self.assertIs(None, bq)

    def test_setting_builderok_resets_failure_count(self):
        builder = removeSecurityProxy(self.factory.makeBuilder())
        builder.failure_count = 1
        builder.builderok = False
        self.assertEqual(1, builder.failure_count)
        builder.builderok = True
        self.assertEqual(0, builder.failure_count)


class TestBuilder(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer
    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=10)

    def setUp(self):
        super(TestBuilder, self).setUp()
        self.slave_helper = self.useFixture(SlaveTestHelpers())

    def test_updateStatus_aborts_lost_and_broken_slave(self):
        # A slave that's 'lost' should be aborted; when the slave is
        # broken then abort() should also throw a fault.
        slave = LostBuildingBrokenSlave()
        lostbuilding_builder = MockBuilder(
            'Lost Building Broken Slave', slave, behavior=CorruptBehavior())
        d = lostbuilding_builder.updateStatus(BufferLogger())
        def check_slave_status(failure):
            self.assertIn('abort', slave.call_log)
            # 'Fault' comes from the LostBuildingBrokenSlave.  This is
            # just testing that the value is passed through.
            self.assertIsInstance(failure.value, xmlrpclib.Fault)
        return d.addBoth(check_slave_status)

    def test_resumeSlaveHost_nonvirtual(self):
        builder = self.factory.makeBuilder(virtualized=False)
        d = builder.resumeSlaveHost()
        return assert_fails_with(d, CannotResumeHost)

    def test_resumeSlaveHost_no_vmhost(self):
        builder = self.factory.makeBuilder(virtualized=True, vm_host=None)
        d = builder.resumeSlaveHost()
        return assert_fails_with(d, CannotResumeHost)

    def test_resumeSlaveHost_success(self):
        reset_config = """
            [builddmaster]
            vm_resume_command: /bin/echo -n parp"""
        config.push('reset', reset_config)
        self.addCleanup(config.pop, 'reset')

        builder = self.factory.makeBuilder(virtualized=True, vm_host="pop")
        d = builder.resumeSlaveHost()
        def got_resume(output):
            self.assertEqual(('parp', ''), output)
        return d.addCallback(got_resume)

    def test_resumeSlaveHost_command_failed(self):
        reset_fail_config = """
            [builddmaster]
            vm_resume_command: /bin/false"""
        config.push('reset fail', reset_fail_config)
        self.addCleanup(config.pop, 'reset fail')
        builder = self.factory.makeBuilder(virtualized=True, vm_host="pop")
        d = builder.resumeSlaveHost()
        return assert_fails_with(d, CannotResumeHost)

    def test_handleTimeout_resume_failure(self):
        reset_fail_config = """
            [builddmaster]
            vm_resume_command: /bin/false"""
        config.push('reset fail', reset_fail_config)
        self.addCleanup(config.pop, 'reset fail')
        builder = self.factory.makeBuilder(virtualized=True, vm_host="pop")
        builder.builderok = True
        d = builder.handleTimeout(BufferLogger(), 'blah')
        return assert_fails_with(d, CannotResumeHost)

    def _setupBuilder(self):
        processor = self.factory.makeProcessor(name="i386")
        builder = self.factory.makeBuilder(
            processor=processor, virtualized=True, vm_host="bladh")
        builder.setSlaveForTesting(OkSlave())
        distroseries = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="i386",
            processorfamily=processor.family)
        chroot = self.factory.makeLibraryFileAlias()
        das.addOrUpdateChroot(chroot)
        distroseries.nominatedarchindep = das
        return builder, distroseries, das

    def _setupRecipeBuildAndBuilder(self):
        # Helper function to make a builder capable of building a
        # recipe, returning both.
        builder, distroseries, distroarchseries = self._setupBuilder()
        build = self.factory.makeSourcePackageRecipeBuild(
            distroseries=distroseries)
        return builder, build

    def _setupBinaryBuildAndBuilder(self):
        # Helper function to make a builder capable of building a
        # binary package, returning both.
        builder, distroseries, distroarchseries = self._setupBuilder()
        build = self.factory.makeBinaryPackageBuild(
            distroarchseries=distroarchseries, builder=builder)
        return builder, build

    def test_findAndStartJob_returns_candidate(self):
        # findAndStartJob finds the next queued job using _findBuildCandidate.
        # We don't care about the type of build at all.
        builder, build = self._setupRecipeBuildAndBuilder()
        candidate = build.queueBuild()
        # _findBuildCandidate is tested elsewhere, we just make sure that
        # findAndStartJob delegates to it.
        removeSecurityProxy(builder)._findBuildCandidate = FakeMethod(
            result=candidate)
        d = builder.findAndStartJob()
        return d.addCallback(self.assertEqual, candidate)

    def test_findAndStartJob_starts_job(self):
        # findAndStartJob finds the next queued job using _findBuildCandidate
        # and then starts it.
        # We don't care about the type of build at all.
        builder, build = self._setupRecipeBuildAndBuilder()
        candidate = build.queueBuild()
        removeSecurityProxy(builder)._findBuildCandidate = FakeMethod(
            result=candidate)
        d = builder.findAndStartJob()
        def check_build_started(candidate):
            self.assertEqual(candidate.builder, builder)
            self.assertEqual(BuildStatus.BUILDING, build.status)
        return d.addCallback(check_build_started)

    def test_virtual_job_dispatch_pings_before_building(self):
        # We need to send a ping to the builder to work around a bug
        # where sometimes the first network packet sent is dropped.
        builder, build = self._setupBinaryBuildAndBuilder()
        candidate = build.queueBuild()
        removeSecurityProxy(builder)._findBuildCandidate = FakeMethod(
            result=candidate)
        d = builder.findAndStartJob()
        def check_build_started(candidate):
            self.assertIn(
                ('echo', 'ping'), removeSecurityProxy(builder.slave).call_log)
        return d.addCallback(check_build_started)

    def test_slave(self):
        # Builder.slave is a BuilderSlave that points at the actual Builder.
        # The Builder is only ever used in scripts that run outside of the
        # security context.
        builder = removeSecurityProxy(self.factory.makeBuilder())
        self.assertEqual(builder.url, builder.slave.url)

    def test_recovery_of_aborted_virtual_slave(self):
        # If a virtual_slave is in the ABORTED state,
        # rescueBuilderIfLost should clean it if we don't think it's
        # currently building anything.
        # See bug 463046.
        aborted_slave = AbortedSlave()
        builder = MockBuilder("mock_builder", aborted_slave)
        builder.currentjob = None
        d = builder.rescueIfLost()
        def check_slave_calls(ignored):
            self.assertIn('clean', aborted_slave.call_log)
        return d.addCallback(check_slave_calls)

    def test_recovery_of_aborted_nonvirtual_slave(self):
        # Nonvirtual slaves in the ABORTED state cannot be reliably
        # cleaned since the sbuild process doesn't properly kill the
        # build job.  We test that the builder is marked failed.
        aborted_slave = AbortedSlave()
        builder = MockBuilder("mock_builder", aborted_slave)
        builder.currentjob = None
        builder.virtualized = False
        builder.builderok = True
        d = builder.rescueIfLost()
        def check_failed(ignored):
            self.assertFalse(builder.builderok)
            self.assertNotIn('clean', aborted_slave.call_log)
        return d.addCallback(check_failed)

    def test_recover_ok_slave(self):
        # An idle slave is not rescued.
        slave = OkSlave()
        builder = MockBuilder("mock_builder", slave, TrivialBehavior())
        d = builder.rescueIfLost()
        def check_slave_calls(ignored):
            self.assertNotIn('abort', slave.call_log)
            self.assertNotIn('clean', slave.call_log)
        return d.addCallback(check_slave_calls)

    def test_recover_waiting_slave_with_good_id(self):
        # rescueIfLost does not attempt to abort or clean a builder that is
        # WAITING.
        waiting_slave = WaitingSlave()
        builder = MockBuilder("mock_builder", waiting_slave, TrivialBehavior())
        d = builder.rescueIfLost()
        def check_slave_calls(ignored):
            self.assertNotIn('abort', waiting_slave.call_log)
            self.assertNotIn('clean', waiting_slave.call_log)
        return d.addCallback(check_slave_calls)

    def test_recover_waiting_slave_with_bad_id(self):
        # If a slave is WAITING with a build for us to get, and the build
        # cookie cannot be verified, which means we don't recognize the build,
        # then rescueBuilderIfLost should attempt to abort it, so that the
        # builder is reset for a new build, and the corrupt build is
        # discarded.
        waiting_slave = WaitingSlave()
        builder = MockBuilder("mock_builder", waiting_slave, CorruptBehavior())
        d = builder.rescueIfLost()
        def check_slave_calls(ignored):
            self.assertNotIn('abort', waiting_slave.call_log)
            self.assertIn('clean', waiting_slave.call_log)
        return d.addCallback(check_slave_calls)

    def test_recover_building_slave_with_good_id(self):
        # rescueIfLost does not attempt to abort or clean a builder that is
        # BUILDING.
        building_slave = BuildingSlave()
        builder = MockBuilder("mock_builder", building_slave, TrivialBehavior())
        d = builder.rescueIfLost()
        def check_slave_calls(ignored):
            self.assertNotIn('abort', building_slave.call_log)
            self.assertNotIn('clean', building_slave.call_log)
        return d.addCallback(check_slave_calls)

    def test_recover_building_slave_with_bad_id(self):
        # If a slave is BUILDING with a build id we don't recognize, then we
        # abort the build, thus stopping it in its tracks.
        building_slave = BuildingSlave()
        builder = MockBuilder("mock_builder", building_slave, CorruptBehavior())
        d = builder.rescueIfLost()
        def check_slave_calls(ignored):
            self.assertIn('abort', building_slave.call_log)
            self.assertNotIn('clean', building_slave.call_log)
        return d.addCallback(check_slave_calls)

    def test_recover_building_slave_with_job_that_finished_elsewhere(self):
        # See bug 671242
        # When a job is destroyed, the builder's behaviour should be reset
        # too so that we don't traceback when the wrong behaviour tries
        # to access a non-existent job.
        builder, build = self._setupBinaryBuildAndBuilder()
        candidate = build.queueBuild()
        building_slave = BuildingSlave()
        builder.setSlaveForTesting(building_slave)
        candidate.markAsBuilding(builder)

        # At this point we should see a valid behaviour on the builder:
        self.assertFalse(
            zope_isinstance(
                builder.current_build_behavior, IdleBuildBehavior))

        # Now reset the job and try to rescue the builder.
        candidate.destroySelf()
        self.layer.txn.commit()
        builder = getUtility(IBuilderSet)[builder.name]
        d = builder.rescueIfLost()
        def check_builder(ignored):
            self.assertIsInstance(
                removeSecurityProxy(builder.current_build_behavior),
                IdleBuildBehavior)
        return d.addCallback(check_builder)


class TestBuilderSlaveStatus(TestCaseWithFactory):
    # Verify what IBuilder.slaveStatus returns with slaves in different
    # states.

    layer = LaunchpadZopelessLayer
    run_tests_with = AsynchronousDeferredRunTest

    def setUp(self):
        super(TestBuilderSlaveStatus, self).setUp()
        self.slave_helper = self.useFixture(SlaveTestHelpers())

    def assertStatus(self, slave, builder_status=None,
                     build_status=None, logtail=False, filemap=None,
                     dependencies=None):
        builder = self.factory.makeBuilder()
        builder.setSlaveForTesting(slave)
        d = builder.slaveStatus()

        def got_status(status_dict):
            expected = {}
            if builder_status is not None:
                expected["builder_status"] = builder_status
            if build_status is not None:
                expected["build_status"] = build_status
            if dependencies is not None:
                expected["dependencies"] = dependencies

            # We don't care so much about the content of the logtail,
            # just that it's there.
            if logtail:
                tail = status_dict.pop("logtail")
                self.assertIsInstance(tail, xmlrpclib.Binary)

            self.assertEqual(expected, status_dict)

        return d.addCallback(got_status)

    def test_slaveStatus_idle_slave(self):
        self.assertStatus(
            OkSlave(), builder_status='BuilderStatus.IDLE')

    def test_slaveStatus_building_slave(self):
        self.assertStatus(
            BuildingSlave(), builder_status='BuilderStatus.BUILDING',
            logtail=True)

    def test_slaveStatus_waiting_slave(self):
        self.assertStatus(
            WaitingSlave(), builder_status='BuilderStatus.WAITING',
            build_status='BuildStatus.OK', filemap={})

    def test_slaveStatus_aborting_slave(self):
        self.assertStatus(
            AbortingSlave(), builder_status='BuilderStatus.ABORTING')

    def test_slaveStatus_aborted_slave(self):
        self.assertStatus(
            AbortedSlave(), builder_status='BuilderStatus.ABORTED')

    def test_isAvailable_with_not_builderok(self):
        # isAvailable() is a wrapper around slaveStatusSentence()
        builder = self.factory.makeBuilder()
        builder.builderok = False
        d = builder.isAvailable()
        return d.addCallback(self.assertFalse)

    def test_isAvailable_with_slave_fault(self):
        builder = self.factory.makeBuilder()
        builder.setSlaveForTesting(BrokenSlave())
        d = builder.isAvailable()
        return d.addCallback(self.assertFalse)

    def test_isAvailable_with_slave_idle(self):
        builder = self.factory.makeBuilder()
        builder.setSlaveForTesting(OkSlave())
        d = builder.isAvailable()
        return d.addCallback(self.assertTrue)


class TestFindBuildCandidateBase(TestCaseWithFactory):
    """Setup the test publisher and some builders."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindBuildCandidateBase, self).setUp()
        self.publisher = make_publisher()
        self.publisher.prepareBreezyAutotest()

        # Create some i386 builders ready to build PPA builds.  Two
        # already exist in sampledata so we'll use those first.
        self.builder1 = getUtility(IBuilderSet)['bob']
        self.frog_builder = getUtility(IBuilderSet)['frog']
        self.builder3 = self.factory.makeBuilder(name='builder3')
        self.builder4 = self.factory.makeBuilder(name='builder4')
        self.builder5 = self.factory.makeBuilder(name='builder5')
        self.builders = [
            self.builder1,
            self.frog_builder,
            self.builder3,
            self.builder4,
            self.builder5,
            ]

        # Ensure all builders are operational.
        for builder in self.builders:
            builder.builderok = True
            builder.manual = False


class TestFindBuildCandidateGeneralCases(TestFindBuildCandidateBase):
    # Test usage of findBuildCandidate not specific to any archive type.

    def test_findBuildCandidate_supersedes_builds(self):
        # IBuilder._findBuildCandidate identifies if there are builds
        # for superseded source package releases in the queue and marks
        # the corresponding build record as SUPERSEDED.
        archive = self.factory.makeArchive()
        self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=archive).createMissingBuilds()
        old_candidate = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()

        # The candidate starts off as NEEDSBUILD:
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(
            old_candidate)
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)

        # Now supersede the source package:
        publication = build.current_source_publication
        publication.status = PackagePublishingStatus.SUPERSEDED

        # The candidate returned is now a different one:
        new_candidate = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        self.assertNotEqual(new_candidate, old_candidate)

        # And the old_candidate is superseded:
        self.assertEqual(BuildStatus.SUPERSEDED, build.status)

    def test_acquireBuildCandidate_marks_building(self):
        # acquireBuildCandidate() should call _findBuildCandidate and
        # mark the build as building.
        archive = self.factory.makeArchive()
        self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=archive).createMissingBuilds()
        candidate = removeSecurityProxy(
            self.frog_builder).acquireBuildCandidate()
        self.assertEqual(JobStatus.RUNNING, candidate.job.status)


class TestFindBuildCandidatePPAWithSingleBuilder(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindBuildCandidatePPAWithSingleBuilder, self).setUp()
        self.publisher = make_publisher()
        self.publisher.prepareBreezyAutotest()

        self.bob_builder = getUtility(IBuilderSet)['bob']
        self.frog_builder = getUtility(IBuilderSet)['frog']

        # Disable bob so only frog is available.
        self.bob_builder.manual = True
        self.bob_builder.builderok = True
        self.frog_builder.manual = False
        self.frog_builder.builderok = True

        # Make a new PPA and give it some builds.
        self.ppa_joe = self.factory.makeArchive(name="joesppa")
        self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_joe).createMissingBuilds()

    def test_findBuildCandidate_first_build_started(self):
        # The allocation rule for PPA dispatching doesn't apply when
        # there's only one builder available.

        # Asking frog to find a candidate should give us the joesppa build.
        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.assertEqual('joesppa', build.archive.name)

        # If bob is in a failed state the joesppa build is still
        # returned.
        self.bob_builder.builderok = False
        self.bob_builder.manual = False
        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.assertEqual('joesppa', build.archive.name)


class TestFindBuildCandidatePPABase(TestFindBuildCandidateBase):

    ppa_joe_private = False
    ppa_jim_private = False

    def _setBuildsBuildingForArch(self, builds_list, num_builds,
                                  archtag="i386"):
        """Helper function.

        Set the first `num_builds` in `builds_list` with `archtag` as
        BUILDING.
        """
        count = 0
        for build in builds_list[:num_builds]:
            if build.distro_arch_series.architecturetag == archtag:
                build.status = BuildStatus.BUILDING
                build.builder = self.builders[count]
            count += 1

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindBuildCandidatePPABase, self).setUp()

        # Create two PPAs and add some builds to each.
        self.ppa_joe = self.factory.makeArchive(
            name="joesppa", private=self.ppa_joe_private)
        self.ppa_jim = self.factory.makeArchive(
            name="jimsppa", private=self.ppa_jim_private)

        self.joe_builds = []
        self.joe_builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_joe).createMissingBuilds())
        self.joe_builds.extend(
            self.publisher.getPubSource(
                sourcename="firefox",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_joe).createMissingBuilds())
        self.joe_builds.extend(
            self.publisher.getPubSource(
                sourcename="cobblers",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_joe).createMissingBuilds())
        self.joe_builds.extend(
            self.publisher.getPubSource(
                sourcename="thunderpants",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_joe).createMissingBuilds())

        self.jim_builds = []
        self.jim_builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_jim).createMissingBuilds())
        self.jim_builds.extend(
            self.publisher.getPubSource(
                sourcename="firefox",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_jim).createMissingBuilds())

        # Set the first three builds in joe's PPA as building, which
        # leaves two builders free.
        self._setBuildsBuildingForArch(self.joe_builds, 3)
        num_active_builders = len(
            [build for build in self.joe_builds if build.builder is not None])
        num_free_builders = len(self.builders) - num_active_builders
        self.assertEqual(num_free_builders, 2)


class TestFindBuildCandidatePPA(TestFindBuildCandidatePPABase):

    def test_findBuildCandidate_first_build_started(self):
        # A PPA cannot start a build if it would use 80% or more of the
        # builders.
        next_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.failIfEqual('joesppa', build.archive.name)

    def test_findBuildCandidate_first_build_finished(self):
        # When joe's first ppa build finishes, his fourth i386 build
        # will be the next build candidate.
        self.joe_builds[0].status = BuildStatus.FAILEDTOBUILD
        next_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('joesppa', build.archive.name)

    def test_findBuildCandidate_with_disabled_archive(self):
        # Disabled archives should not be considered for dispatching
        # builds.
        disabled_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(
            disabled_job)
        build.archive.disable()
        next_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        self.assertNotEqual(disabled_job, next_job)


class TestFindBuildCandidatePrivatePPA(TestFindBuildCandidatePPABase):

    ppa_joe_private = True

    def test_findBuildCandidate_for_private_ppa(self):
        # If a ppa is private it will be able to have parallel builds
        # for the one architecture.
        next_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('joesppa', build.archive.name)

        # If the source for the build is still pending, it won't be
        # dispatched because the builder has to fetch the source files
        # from the (password protected) repo area, not the librarian.
        pub = build.current_source_publication
        pub.status = PackagePublishingStatus.PENDING
        candidate = removeSecurityProxy(self.builder4)._findBuildCandidate()
        self.assertNotEqual(next_job.id, candidate.id)


class TestFindBuildCandidateDistroArchive(TestFindBuildCandidateBase):

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindBuildCandidateDistroArchive, self).setUp()
        # Create a primary archive and publish some builds for the
        # queue.
        self.non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)

        self.gedit_build = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.non_ppa).createMissingBuilds()[0]
        self.firefox_build = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
            archive=self.non_ppa).createMissingBuilds()[0]

    def test_findBuildCandidate_for_non_ppa(self):
        # Normal archives are not restricted to serial builds per
        # arch.

        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('primary', build.archive.name)
        self.failUnlessEqual('gedit', build.source_package_release.name)

        # Now even if we set the build building, we'll still get the
        # second non-ppa build for the same archive as the next candidate.
        build.status = BuildStatus.BUILDING
        build.builder = self.frog_builder
        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('primary', build.archive.name)
        self.failUnlessEqual('firefox', build.source_package_release.name)

    def test_findBuildCandidate_for_recipe_build(self):
        # Recipe builds with a higher score are selected first.
        # This test is run in a context with mixed recipe and binary builds.

        self.assertIsNot(self.frog_builder.processor, None)
        self.assertEqual(self.frog_builder.virtualized, True)

        self.assertEqual(self.gedit_build.buildqueue_record.lastscore, 2505)
        self.assertEqual(self.firefox_build.buildqueue_record.lastscore, 2505)

        recipe_build_job = self.factory.makeSourcePackageRecipeBuildJob(9999)

        self.assertEqual(recipe_build_job.lastscore, 9999)

        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()

        self.failUnlessEqual(recipe_build_job, next_job)


class TestFindRecipeBuildCandidates(TestFindBuildCandidateBase):
    # These tests operate in a "recipe builds only" setting.
    # Please see also bug #507782.

    def clearBuildQueue(self):
        """Delete all `BuildQueue`, XXXJOb and `Job` instances."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        for bq in store.find(BuildQueue):
            bq.destroySelf()

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindRecipeBuildCandidates, self).setUp()
        # Create a primary archive and publish some builds for the
        # queue.
        self.non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)

        self.clearBuildQueue()
        self.bq1 = self.factory.makeSourcePackageRecipeBuildJob(3333)
        self.bq2 = self.factory.makeSourcePackageRecipeBuildJob(4333)

    def test_findBuildCandidate_with_highest_score(self):
        # The recipe build with the highest score is selected first.
        # This test is run in a "recipe builds only" context.

        self.assertIsNot(self.frog_builder.processor, None)
        self.assertEqual(self.frog_builder.virtualized, True)

        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()

        self.failUnlessEqual(self.bq2, next_job)


class TestCurrentBuildBehavior(TestCaseWithFactory):
    """This test ensures the get/set behavior of IBuilder's
    current_build_behavior property.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Create a new builder ready for testing."""
        super(TestCurrentBuildBehavior, self).setUp()
        self.builder = self.factory.makeBuilder(name='builder')

        # Have a publisher and a ppa handy for some of the tests below.
        self.publisher = make_publisher()
        self.publisher.prepareBreezyAutotest()
        self.ppa_joe = self.factory.makeArchive(name="joesppa")

        self.build = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_joe).createMissingBuilds()[0]

        self.buildfarmjob = self.build.buildqueue_record.specific_job

    def test_idle_behavior_when_no_current_build(self):
        """We return an idle behavior when there is no behavior specified
        nor a current build.
        """
        self.assertIsInstance(
            self.builder.current_build_behavior, IdleBuildBehavior)

    def test_set_behavior_sets_builder(self):
        """Setting a builder's behavior also associates the behavior with the
        builder."""
        behavior = IBuildFarmJobBehavior(self.buildfarmjob)
        self.builder.current_build_behavior = behavior

        self.assertEqual(behavior, self.builder.current_build_behavior)
        self.assertEqual(behavior._builder, self.builder)

    def test_current_job_behavior(self):
        """The current behavior is set automatically from the current job."""
        # Set the builder attribute on the buildqueue record so that our
        # builder will think it has a current build.
        self.build.buildqueue_record.builder = self.builder

        self.assertIsInstance(
            self.builder.current_build_behavior, BinaryPackageBuildBehavior)


class TestSlave(TestCase):
    """
    Integration tests for BuilderSlave that verify how it works against a
    real slave server.
    """

    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=10)

    def setUp(self):
        super(TestSlave, self).setUp()
        self.slave_helper = self.useFixture(SlaveTestHelpers())

    # XXX 2010-10-06 Julian bug=655559
    # This is failing on buildbot but not locally; it's trying to abort
    # before the build has started.
    def disabled_test_abort(self):
        slave = self.slave_helper.getClientSlave()
        # We need to be in a BUILDING state before we can abort.
        d = self.slave_helper.triggerGoodBuild(slave)
        d.addCallback(lambda ignored: slave.abort())
        d.addCallback(self.assertEqual, BuilderStatus.ABORTING)
        return d

    def test_build(self):
        # Calling 'build' with an expected builder type, a good build id,
        # valid chroot & filemaps works and returns a BuilderStatus of
        # BUILDING.
        build_id = 'some-id'
        slave = self.slave_helper.getClientSlave()
        d = self.slave_helper.triggerGoodBuild(slave, build_id)
        return d.addCallback(
            self.assertEqual, [BuilderStatus.BUILDING, build_id])

    def test_clean(self):
        slave = self.slave_helper.getClientSlave()
        # XXX: JonathanLange 2010-09-21: Calling clean() on the slave requires
        # it to be in either the WAITING or ABORTED states, and both of these
        # states are very difficult to achieve in a test environment. For the
        # time being, we'll just assert that a clean attribute exists.
        self.assertNotEqual(getattr(slave, 'clean', None), None)

    def test_echo(self):
        # Calling 'echo' contacts the server which returns the arguments we
        # gave it.
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        d = slave.echo('foo', 'bar', 42)
        return d.addCallback(self.assertEqual, ['foo', 'bar', 42])

    def test_info(self):
        # Calling 'info' gets some information about the slave.
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        d = slave.info()
        # We're testing the hard-coded values, since the version is hard-coded
        # into the remote slave, the supported build managers are hard-coded
        # into the tac file for the remote slave and config is returned from
        # the configuration file.
        return d.addCallback(
            self.assertEqual,
            ['1.0',
             'i386',
             ['sourcepackagerecipe',
              'translation-templates', 'binarypackage', 'debian']])

    def test_initial_status(self):
        # Calling 'status' returns the current status of the slave. The
        # initial status is IDLE.
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        d = slave.status()
        return d.addCallback(self.assertEqual, [BuilderStatus.IDLE, ''])

    def test_status_after_build(self):
        # Calling 'status' returns the current status of the slave. After a
        # build has been triggered, the status is BUILDING.
        slave = self.slave_helper.getClientSlave()
        build_id = 'status-build-id'
        d = self.slave_helper.triggerGoodBuild(slave, build_id)
        d.addCallback(lambda ignored: slave.status())
        def check_status(status):
            self.assertEqual([BuilderStatus.BUILDING, build_id], status[:2])
            [log_file] = status[2:]
            self.assertIsInstance(log_file, xmlrpclib.Binary)
        return d.addCallback(check_status)

    def test_ensurepresent_not_there(self):
        # ensurepresent checks to see if a file is there.
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        d = slave.ensurepresent('blahblah', None, None, None)
        d.addCallback(self.assertEqual, [False, 'No URL'])
        return d

    def test_ensurepresent_actually_there(self):
        # ensurepresent checks to see if a file is there.
        tachandler = self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        self.slave_helper.makeCacheFile(tachandler, 'blahblah')
        d = slave.ensurepresent('blahblah', None, None, None)
        d.addCallback(self.assertEqual, [True, 'No URL'])
        return d

    def test_sendFileToSlave_not_there(self):
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        d = slave.sendFileToSlave('blahblah', None, None, None)
        return assert_fails_with(d, CannotFetchFile)

    def test_sendFileToSlave_actually_there(self):
        tachandler = self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        self.slave_helper.makeCacheFile(tachandler, 'blahblah')
        d = slave.sendFileToSlave('blahblah', None, None, None)
        def check_present(ignored):
            d = slave.ensurepresent('blahblah', None, None, None)
            return d.addCallback(self.assertEqual, [True, 'No URL'])
        d.addCallback(check_present)
        return d

    def test_resumeHost_success(self):
        # On a successful resume resume() fires the returned deferred
        # callback with 'None'.
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()

        # The configuration testing command-line.
        self.assertEqual(
            'echo %(vm_host)s', config.builddmaster.vm_resume_command)

        # On success the response is None.
        def check_resume_success(response):
            out, err, code = response
            self.assertEqual(os.EX_OK, code)
            # XXX: JonathanLange 2010-09-23: We should instead pass the
            # expected vm_host into the client slave. Not doing this now,
            # since the SlaveHelper is being moved around.
            self.assertEqual("%s\n" % slave._vm_host, out)
        d = slave.resume()
        d.addBoth(check_resume_success)
        return d

    def test_resumeHost_failure(self):
        # On a failed resume, 'resumeHost' fires the returned deferred
        # errorback with the `ProcessTerminated` failure.
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()

        # Override the configuration command-line with one that will fail.
        failed_config = """
        [builddmaster]
        vm_resume_command: test "%(vm_host)s = 'no-sir'"
        """
        config.push('failed_resume_command', failed_config)
        self.addCleanup(config.pop, 'failed_resume_command')

        # On failures, the response is a twisted `Failure` object containing
        # a tuple.
        def check_resume_failure(failure):
            out, err, code = failure.value
            # The process will exit with a return code of "1".
            self.assertEqual(code, 1)
        d = slave.resume()
        d.addBoth(check_resume_failure)
        return d

    def test_resumeHost_timeout(self):
        # On a resume timeouts, 'resumeHost' fires the returned deferred
        # errorback with the `TimeoutError` failure.
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()

        # Override the configuration command-line with one that will timeout.
        timeout_config = """
        [builddmaster]
        vm_resume_command: sleep 5
        socket_timeout: 1
        """
        config.push('timeout_resume_command', timeout_config)
        self.addCleanup(config.pop, 'timeout_resume_command')

        # On timeouts, the response is a twisted `Failure` object containing
        # a `TimeoutError` error.
        def check_resume_timeout(failure):
            self.assertIsInstance(failure, Failure)
            out, err, code = failure.value
            self.assertEqual(code, signal.SIGKILL)
        clock = Clock()
        d = slave.resume(clock=clock)
        # Move the clock beyond the socket_timeout but earlier than the
        # sleep 5.  This stops the test having to wait for the timeout.
        # Fast tests FTW!
        clock.advance(2)
        d.addBoth(check_resume_timeout)
        return d


class TestSlaveTimeouts(TestCase):
    # Testing that the methods that call callRemote() all time out
    # as required.

    run_tests_with = AsynchronousDeferredRunTestForBrokenTwisted

    def setUp(self):
        super(TestSlaveTimeouts, self).setUp()
        self.slave_helper = self.useFixture(SlaveTestHelpers())
        self.clock = Clock()
        self.proxy = DeadProxy("url")
        self.slave = self.slave_helper.getClientSlave(
            reactor=self.clock, proxy=self.proxy)

    def assertCancelled(self, d):
        self.clock.advance(config.builddmaster.socket_timeout + 1)
        return assert_fails_with(d, CancelledError)

    def test_timeout_abort(self):
        return self.assertCancelled(self.slave.abort())

    def test_timeout_clean(self):
        return self.assertCancelled(self.slave.clean())

    def test_timeout_echo(self):
        return self.assertCancelled(self.slave.echo())

    def test_timeout_info(self):
        return self.assertCancelled(self.slave.info())

    def test_timeout_status(self):
        return self.assertCancelled(self.slave.status())

    def test_timeout_ensurepresent(self):
        return self.assertCancelled(
            self.slave.ensurepresent(None, None, None, None))

    def test_timeout_build(self):
        return self.assertCancelled(
            self.slave.build(None, None, None, None, None))


class TestSlaveConnectionTimeouts(TestCase):
    # Testing that we can override the default 30 second connection
    # timeout.

    run_test = SynchronousDeferredRunTest

    def setUp(self):
        super(TestSlaveConnectionTimeouts, self).setUp()
        self.slave_helper = self.useFixture(SlaveTestHelpers())
        self.clock = Clock()
        self.proxy = ProxyWithConnectionTimeout("fake_url")
        self.slave = self.slave_helper.getClientSlave(
            reactor=self.clock, proxy=self.proxy)

    def test_connection_timeout(self):
        # The default timeout of 30 seconds should not cause a timeout,
        # only the config value should.
        self.pushConfig('builddmaster', socket_timeout=180)

        d = self.slave.echo()
        # Advance past the 30 second timeout.  The real reactor will
        # never call connectTCP() since we're not spinning it up.  This
        # avoids "connection refused" errors and simulates an
        # environment where the endpoint doesn't respond.
        self.clock.advance(31)
        self.assertFalse(d.called)

        self.clock.advance(config.builddmaster.socket_timeout + 1)
        self.assertTrue(d.called)
        return assert_fails_with(d, CancelledError)

    def test_BuilderSlave_uses_ProxyWithConnectionTimeout(self):
        # Make sure that BuilderSlaves use the custom proxy class.
        slave = BuilderSlave.makeBuilderSlave("url", "host")
        self.assertIsInstance(slave._server, ProxyWithConnectionTimeout)


class TestSlaveWithLibrarian(TestCaseWithFactory):
    """Tests that need more of Launchpad to run."""

    layer = LaunchpadZopelessLayer
    run_tests_with = AsynchronousDeferredRunTestForBrokenTwisted.make_factory(
        timeout=20)

    def setUp(self):
        super(TestSlaveWithLibrarian, self).setUp()
        self.slave_helper = self.useFixture(SlaveTestHelpers())

    def test_ensurepresent_librarian(self):
        # ensurepresent, when given an http URL for a file will download the
        # file from that URL and report that the file is present, and it was
        # downloaded.

        # Use the Librarian because it's a "convenient" web server.
        lf = self.factory.makeLibraryFileAlias(
            'HelloWorld.txt', content="Hello World")
        self.layer.txn.commit()
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        d = slave.ensurepresent(
            lf.content.sha1, lf.http_url, "", "")
        d.addCallback(self.assertEqual, [True, 'Download'])
        return d

    def test_retrieve_files_from_filecache(self):
        # Files that are present on the slave can be downloaded with a
        # filename made from the sha1 of the content underneath the
        # 'filecache' directory.
        content = "Hello World"
        lf = self.factory.makeLibraryFileAlias(
            'HelloWorld.txt', content=content)
        self.layer.txn.commit()
        expected_url = '%s/filecache/%s' % (
            self.slave_helper.BASE_URL, lf.content.sha1)
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        d = slave.ensurepresent(
            lf.content.sha1, lf.http_url, "", "")
        def check_file(ignored):
            d = getPage(expected_url.encode('utf8'))
            return d.addCallback(self.assertEqual, content)
        return d.addCallback(check_file)

    def test_getFiles(self):
        # Test BuilderSlave.getFiles().
        # It also implicitly tests getFile() - I don't want to test that
        # separately because it increases test run time and it's going
        # away at some point anyway, in favour of getFiles().
        contents = ["content1", "content2", "content3"]
        self.slave_helper.getServerSlave()
        slave = self.slave_helper.getClientSlave()
        filemap = {}
        content_map = {}

        def got_files(ignored):
            # Called back when getFiles finishes.  Make sure all the
            # content is as expected.
            got_contents = []
            for sha1 in filemap:
                local_file = filemap[sha1]
                file = open(local_file)
                self.assertEqual(content_map[sha1], file.read())
                file.close()

        def finished_uploading(ignored):
            d = slave.getFiles(filemap)
            return d.addCallback(got_files)

        # Set up some files on the builder and store details in
        # content_map so we can compare downloads later.
        dl = []
        for content in contents:
            filename = content + '.txt'
            lf = self.factory.makeLibraryFileAlias(filename, content=content)
            content_map[lf.content.sha1] = content
            fd, filemap[lf.content.sha1] = tempfile.mkstemp()
            self.addCleanup(os.remove, filemap[lf.content.sha1])
            self.layer.txn.commit()
            d = slave.ensurepresent(lf.content.sha1, lf.http_url, "", "")
            dl.append(d)

        return DeferredList(dl).addCallback(finished_uploading)
