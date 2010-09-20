# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Builder features."""

import errno
import os
import socket
import xmlrpclib

from testtools.content import Content
from testtools.content_type import UTF8_TEXT

from twisted.trial.unittest import TestCase as TrialTestCase

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.buildd.slave import BuilderStatus
from canonical.buildd.tests.harness import BuilddSlaveTestSetup
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    TwistedLayer,
    )
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.builder import IBuilder, IBuilderSet
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.model.builder import BuilderSlave
from lp.buildmaster.model.buildfarmjobbehavior import IdleBuildBehavior
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.model.binarypackagebuildbehavior import (
    BinaryPackageBuildBehavior,
    )
from lp.soyuz.tests.soyuzbuilddhelpers import (
    AbortedSlave,
    MockBuilder,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


class TestBuilder(TestCaseWithFactory):
    """Basic unit tests for `Builder`."""

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        # Builder provides IBuilder
        builder = self.factory.makeBuilder()
        self.assertProvides(builder, IBuilder)

    def test_default_values(self):
        builder = self.factory.makeBuilder()
        # Make sure the Storm cache gets the values that the database
        # initialises.
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

    def test_updateBuilderStatus_catches_repeated_EINTR(self):
        # A single EINTR return from a socket operation should cause the
        # operation to be retried, not fail/reset the builder.
        builder = removeSecurityProxy(self.factory.makeBuilder())
        builder.handleTimeout = FakeMethod()
        builder.rescueIfLost = FakeMethod()

        def _fake_checkSlaveAlive():
            # Raise an EINTR error for all invocations.
            raise socket.error(errno.EINTR, "fake eintr")

        builder.checkSlaveAlive = _fake_checkSlaveAlive
        builder.updateStatus()

        # builder.updateStatus should eventually have called
        # handleTimeout()
        self.assertEqual(1, builder.handleTimeout.call_count)

    def test_updateBuilderStatus_catches_single_EINTR(self):
        builder = removeSecurityProxy(self.factory.makeBuilder())
        builder.handleTimeout = FakeMethod()
        builder.rescueIfLost = FakeMethod()
        self.eintr_returned = False

        def _fake_checkSlaveAlive():
            # raise an EINTR error for the first invocation only.
            if not self.eintr_returned:
                self.eintr_returned = True
                raise socket.error(errno.EINTR, "fake eintr")

        builder.checkSlaveAlive = _fake_checkSlaveAlive
        builder.updateStatus()

        # builder.updateStatus should never call handleTimeout() for a
        # single EINTR.
        self.assertEqual(0, builder.handleTimeout.call_count)


class Test_rescueBuilderIfLost(TestCaseWithFactory):
    """Tests for lp.buildmaster.model.builder.rescueBuilderIfLost."""

    layer = LaunchpadZopelessLayer

    def test_recovery_of_aborted_slave(self):
        # If a slave is in the ABORTED state, rescueBuilderIfLost should
        # clean it if we don't think it's currently building anything.
        # See bug 463046.
        aborted_slave = AbortedSlave()
        # The slave's clean() method is normally an XMLRPC call, so we
        # can just stub it out and check that it got called.
        aborted_slave.clean = FakeMethod()
        builder = MockBuilder("mock_builder", aborted_slave)
        builder.currentjob = None
        builder.rescueIfLost()

        self.assertEqual(1, aborted_slave.clean.call_count)


class TestFindBuildCandidateBase(TestCaseWithFactory):
    """Setup the test publisher and some builders."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindBuildCandidateBase, self).setUp()
        self.publisher = SoyuzTestPublisher()
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


class TestFindBuildCandidatePPAWithSingleBuilder(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindBuildCandidatePPAWithSingleBuilder, self).setUp()
        self.publisher = SoyuzTestPublisher()
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


class TestFindBuildCandidatePrivatePPA(TestFindBuildCandidatePPABase):

    ppa_joe_private = True

    def test_findBuildCandidate_for_private_ppa(self):
        # If a ppa is private it will be able to have parallel builds
        # for the one architecture.
        next_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('joesppa', build.archive.name)


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
        self.publisher = SoyuzTestPublisher()
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


class TestSlave(TrialTestCase):
    """
    Integration tests for BuilderSlave that verify how it works against a
    real slave server.
    """

    layer = TwistedLayer

    # XXX: JonathanLange 2010-09-20 bug=643521: There are also tests for
    # BuilderSlave in buildd-slave.txt and in other places. The tests here
    # ought to become the canonical tests for BuilderSlave vs running buildd
    # XML-RPC server interaction.

    # The URL for the XML-RPC service set up by `BuilddSlaveTestSetup`.
    TEST_URL = 'http://localhost:8221/rpc/'

    def getServerSlave(self):
        """Set up a test build slave server.

        :return: A `BuilddSlaveTestSetup` object.
        """
        tachandler = BuilddSlaveTestSetup()
        tachandler.setUp()
        # Basically impossible to do this w/ TrialTestCase. But it would be
        # really nice to keep it.
        #
        # def addLogFile(exc_info):
        #     self.addDetail(
        #         'xmlrpc-log-file',
        #         Content(UTF8_TEXT, lambda: open(tachandler.logfile, 'r').read()))
        # self.addOnException(addLogFile)
        self.addCleanup(tachandler.tearDown)
        return tachandler

    def getClientSlave(self):
        """Return a `BuilderSlave` for use in testing.

        Points to a fixed URL that is also used by `BuilddSlaveTestSetup`.
        """
        return BuilderSlave(self.TEST_URL, 'vmhost')

    def makeCacheFile(self, tachandler, filename):
        """Make a cache file available on the remote slave.

        :param tachandler: The TacTestSetup object used to start the remote
            slave.
        :param filename: The name of the file to create in the file cache
            area.
        """
        path = os.path.join(tachandler.root, 'filecache', filename)
        fd = open(path, 'w')
        fd.write('something')
        fd.close()
        self.addCleanup(os.unlink, path)

    def triggerGoodBuild(self, slave, build_id=None):
        """Trigger a good build on 'slave'.

        :param slave: A `BuilderSlave` instance to trigger the build on.
        :param build_id: The build identifier. If not specified, defaults to
            an arbitrary string.
        :type build_id: str
        :return: The build id returned by the slave.
        """
        if build_id is None:
            build_id = 'random-build-id'
        tachandler = self.getServerSlave()
        chroot_file = 'fake-chroot'
        dsc_file = 'thing'
        self.makeCacheFile(tachandler, chroot_file)
        self.makeCacheFile(tachandler, dsc_file)
        return slave.build(
            build_id, 'debian', chroot_file, {'.dsc': dsc_file},
            {'ogrecomponent': 'main'})

    def test_abort(self):
        slave = self.getClientSlave()
        # We need to be in a BUILDING state before we can abort.
        self.triggerGoodBuild(slave)
        result = slave.abort()
        self.assertEqual(result, BuilderStatus.ABORTING)

    def test_build(self):
        # Calling 'build' with an expected builder type, a good build id,
        # valid chroot & filemaps works and returns a BuilderStatus of
        # BUILDING.
        build_id = 'some-id'
        slave = self.getClientSlave()
        result = self.triggerGoodBuild(slave, build_id)
        self.assertEqual([BuilderStatus.BUILDING, build_id], result)

    def test_echo(self):
        # Calling 'echo' contacts the server which returns the arguments we
        # gave it.
        self.getServerSlave()
        slave = self.getClientSlave()
        result = slave.echo('foo', 'bar', 42)
        self.assertEqual(['foo', 'bar', 42], result)

    def test_info(self):
        # Calling 'info' gets some information about the slave.
        self.getServerSlave()
        slave = self.getClientSlave()
        result = slave.info()
        # We're testing the hard-coded values, since the version is hard-coded
        # into the remote slave, the supported build managers are hard-coded
        # into the tac file for the remote slave and config is returned from
        # the configuration file.
        self.assertEqual(
            ['1.0',
             'i386',
             ['sourcepackagerecipe',
              'translation-templates', 'binarypackage', 'debian']],
            result)

    def test_initial_status(self):
        # Calling 'status' returns the current status of the slave. The
        # initial status is IDLE.
        self.getServerSlave()
        slave = self.getClientSlave()
        status = slave.status()
        self.assertEqual([BuilderStatus.IDLE, ''], status)

    def test_status_after_build(self):
        # Calling 'status' returns the current status of the slave. After a
        # build has been triggered, the status is BUILDING.
        slave = self.getClientSlave()
        build_id = 'status-build-id'
        self.triggerGoodBuild(slave, build_id)
        status = slave.status()
        self.assertEqual([BuilderStatus.BUILDING, build_id], status[:2])
        [log_file] = status[2:]
        self.assertIsInstance(log_file, xmlrpclib.Binary)

    def test_ensurepresent_not_there(self):
        # ensurepresent checks to see if a file is there.
        self.getServerSlave()
        slave = self.getClientSlave()
        d = slave.ensurepresent('blahblah', None, None, None)
        d.addCallback(self.assertEqual, [False, 'No URL'])
        return d

    def test_ensurepresent_actually_there(self):
        # ensurepresent checks to see if a file is there.
        tachandler = self.getServerSlave()
        slave = self.getClientSlave()
        self.makeCacheFile(tachandler, 'blahblah')
        d = slave.ensurepresent('blahblah', None, None, None)
        d.addCallback(self.assertEqual, [True, 'No URL'])
        return d
