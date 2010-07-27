# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the renovated slave scanner aka BuilddManager."""

import os
import signal
import time
import transaction
import unittest

from twisted.internet import defer
from twisted.internet.error import ConnectionClosed
from twisted.internet.task import Clock
from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase as TrialTestCase

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.buildd.tests import BuilddSlaveTestSetup
from canonical.config import config
from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.scripts.logger import BufferLogger
from canonical.testing.layers import (
    LaunchpadScriptLayer, LaunchpadZopelessLayer, TwistedLayer)
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.builder import IBuilderSet
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.manager import (
    BaseDispatchResult, BuilddManager, FailDispatchResult, RecordingSlave,
    ResetDispatchResult, buildd_success_result_map)
from lp.buildmaster.tests.harness import BuilddManagerTestSetup
from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.tests.soyuzbuilddhelpers import BuildingSlave
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher


class TestRecordingSlaves(TrialTestCase):
    """Tests for the recording slave class."""
    layer = TwistedLayer

    def setUp(self):
        """Setup a fresh `RecordingSlave` for tests."""
        TrialTestCase.setUp(self)
        self.slave = RecordingSlave(
            'foo', 'http://foo:8221/rpc', 'foo.host')

    def test_representation(self):
        """`RecordingSlave` has a custom representation.

        It encloses builder name and xmlrpc url for debug purposes.
        """
        self.assertEqual('<foo:http://foo:8221/rpc>', repr(self.slave))

    def assert_ensurepresent(self, func):
        """Helper function to test results from calling ensurepresent."""
        self.assertEqual(
            [True, 'Download'],
            func('boing', 'bar', 'baz'))
        self.assertEqual(
            [('ensurepresent', ('boing', 'bar', 'baz'))],
            self.slave.calls)

    def test_ensurepresent(self):
        """`RecordingSlave.ensurepresent` always succeeds.

        It returns the expected succeed code and records the interaction
        information for later use.
        """
        self.assert_ensurepresent(self.slave.ensurepresent)

    def test_sendFileToSlave(self):
        """RecordingSlave.sendFileToSlave always succeeeds.

        It calls ensurepresent() and hence returns the same results.
        """
        self.assert_ensurepresent(self.slave.sendFileToSlave)

    def test_build(self):
        """`RecordingSlave.build` always succeeds.

        It returns the expected succeed code and records the interaction
        information for later use.
        """
        self.assertEqual(
            ['BuilderStatus.BUILDING', 'boing'],
            self.slave.build('boing', 'bar', 'baz'))
        self.assertEqual(
            [('build', ('boing', 'bar', 'baz'))],
            self.slave.calls)

    def test_resume(self):
        """`RecordingSlave.resume` always returns successs."""
        # Resume isn't requested in a just-instantiated RecordingSlave.
        self.assertFalse(self.slave.resume_requested)

        # When resume is called, it returns the success list and mark
        # the slave for resuming.
        self.assertEqual(['', '', os.EX_OK], self.slave.resume())
        self.assertTrue(self.slave.resume_requested)

    def test_resumeHost_success(self):
        # On a successful resume resumeHost() fires the returned deferred
        # callback with 'None'.

        # The configuration testing command-line.
        self.assertEqual(
            'echo %(vm_host)s', config.builddmaster.vm_resume_command)

        # On success the response is None.
        def check_resume_success(response):
            out, err, code = response
            self.assertEqual(os.EX_OK, code)
            self.assertEqual("%s\n" % self.slave.vm_host, out)
        d = self.slave.resumeSlave()
        d.addBoth(check_resume_success)
        return d

    def test_resumeHost_failure(self):
        # On a failed resume, 'resumeHost' fires the returned deferred
        # errorback with the `ProcessTerminated` failure.

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
        d = self.slave.resumeSlave()
        d.addBoth(check_resume_failure)
        return d

    def test_resumeHost_timeout(self):
        # On a resume timeouts, 'resumeHost' fires the returned deferred
        # errorback with the `TimeoutError` failure.

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
        d = self.slave.resumeSlave(clock=clock)
        # Move the clock beyond the socket_timeout but earlier than the
        # sleep 5.  This stops the test having to wait for the timeout.
        # Fast tests FTW!
        clock.advance(2)
        d.addBoth(check_resume_timeout)
        return d


class TestingXMLRPCProxy:
    """This class mimics a twisted XMLRPC Proxy class."""

    def __init__(self, failure_info=None):
        self.calls = []
        self.failure_info = failure_info
        self.works = failure_info is None

    def callRemote(self, *args):
        self.calls.append(args)
        if self.works:
            result = buildd_success_result_map.get(args[0])
        else:
            result = 'boing'
        return defer.succeed([result, self.failure_info])


class TestingResetDispatchResult(ResetDispatchResult):
    """Override the evaluation method to simply annotate the call."""

    def __init__(self, slave, info=None):
        ResetDispatchResult.__init__(self, slave, info)
        self.processed = False

    def __call__(self):
        self.processed = True


class TestingFailDispatchResult(FailDispatchResult):
    """Override the evaluation method to simply annotate the call."""

    def __init__(self, slave, info=None):
        FailDispatchResult.__init__(self, slave, info)
        self.processed = False

    def __call__(self):
        self.processed = True


class TestingBuilddManager(BuilddManager):
    """Override the dispatch result factories """

    reset_result = TestingResetDispatchResult
    fail_result = TestingFailDispatchResult


class TestBuilddManager(TrialTestCase):
    """Tests for the actual build slave manager."""
    layer = TwistedLayer

    def setUp(self):
        TrialTestCase.setUp(self)
        self.manager = TestingBuilddManager()
        self.manager.logger = BufferLogger()

        # We will use an instrumented BuilddManager instance for tests in
        # this context.

        # Stop cyclic execution and record the end of the cycle.
        self.stopped = False
        def testNextCycle():
            self.stopped = True
        self.manager.nextCycle = testNextCycle

        # Return the testing Proxy version.
        self.test_proxy = TestingXMLRPCProxy()
        def testGetProxyForSlave(slave):
            return self.test_proxy
        self.manager._getProxyForSlave = testGetProxyForSlave

        # Deactivate the 'scan' method.
        def testScan():
            pass
        self.manager.scan = testScan

        # Stop automatic collection of dispatching results.
        def testSlaveDone(slave):
            pass
        self._realSlaveDone = self.manager.slaveDone
        self.manager.slaveDone = testSlaveDone

    def testFinishCycle(self):
        """Check if the chain is terminated and database updates are done.

        'BuilddManager.finishCycle' verifies the number of active deferreds
        and once they cease it performs all needed database updates (builder
        reset or failure) synchronously and call `BuilddManager.nextCycle`.
        """
        # There are no active deferreds in a just instantiated BuilddManager.
        self.assertEqual(0, len(self.manager._deferreds))

        # Fill the deferred list with events we can check later.
        reset_me = TestingResetDispatchResult(
            RecordingSlave('foo', 'http://foo', 'foo.host'))
        fail_me = TestingFailDispatchResult(
            RecordingSlave('bar', 'http://bar', 'bar.host'), 'boingo')
        self.manager._deferreds.extend(
            [defer.succeed(reset_me), defer.succeed(fail_me), defer.fail()])

        # When `finishCycle` is called, and it is called after all build
        # slave interaction, active deferreds are consumed.
        events = self.manager.finishCycle()
        def check_events(results):
            # The cycle was stopped (and in the production the next cycle
            # would have being scheduled).
            self.assertTrue(self.stopped)

            # The stored list of events from this cycle was consumed.
            self.assertEqual(0, len(self.manager._deferreds))

            # We have exactly 2 BaseDispatchResult events.
            [reset, fail] = [
                r for s, r in results if isinstance(r, BaseDispatchResult)]

            # They corresponds to the ones created above and were already
            # processed.
            self.assertEqual(
                '<foo:http://foo> reset failure', repr(reset))
            self.assertTrue(reset.processed)
            self.assertEqual(
                '<bar:http://bar> failure (boingo)', repr(fail))
            self.assertTrue(fail.processed)

        events.addCallback(check_events)
        return events

    def assertIsDispatchReset(self, result):
        self.assertTrue(
            isinstance(result, TestingResetDispatchResult),
            'Dispatch failure did not result in a ResetBuildResult object')

    def assertIsDispatchFail(self, result):
        self.assertTrue(
            isinstance(result, TestingFailDispatchResult),
            'Dispatch failure did not result in a FailBuildResult object')

    def test_checkResume(self):
        """`BuilddManager.checkResume` is chained after resume requests.

        If the resume request succeed it returns None, otherwise it returns
        a `ResetBuildResult` (the one in the test context) that will be
        collect and evaluated later.

        See `RecordingSlave.resumeHost` for more information about the resume
        result contents.
        """
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')

        successful_response = ['', '', os.EX_OK]
        result = self.manager.checkResume(successful_response, slave)
        self.assertEqual(
            None, result, 'Successful resume checks should return None')

        failed_response = ['stdout', 'stderr', 1]
        result = self.manager.checkResume(failed_response, slave)
        self.assertIsDispatchReset(result)
        self.assertEqual(
            '<foo:http://foo.buildd:8221/> reset failure', repr(result))
        self.assertEqual(
            result.info, "stdout\nstderr")

    def test_fail_to_resume_slave_resets_slave(self):
        # If an attempt to resume and dispatch a slave fails, we reset the
        # slave by calling self.reset_result(slave)().

        reset_result_calls = []
        class LoggingResetResult(BaseDispatchResult):
            """A DispatchResult that logs calls to itself.

            This *must* subclass BaseDispatchResult, otherwise finishCycle()
            won't treat it like a dispatch result.
            """
            def __init__(self, slave, info=None):
                self.slave = slave
            def __call__(self):
                reset_result_calls.append(self.slave)

        # Make a failing slave that is requesting a resume.
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')
        slave.resume_requested = True
        slave.resumeSlave = lambda: defer.fail(Failure(('out', 'err', 1)))

        # Make the manager log the reset result calls.
        self.manager.reset_result = LoggingResetResult
        # Restore the slaveDone method. It's very relevant to this test.
        self.manager.slaveDone = self._realSlaveDone
        # We only care about this one slave. Reset the list of manager
        # deferreds in case setUp did something unexpected.
        self.manager._deferreds = []

        self.manager.resumeAndDispatch([slave])
        # Note: finishCycle isn't generally called by external users, normally
        # resumeAndDispatch or slaveDone calls it. However, these calls
        # swallow the Deferred that finishCycle returns, and we need that
        # Deferred to make sure this test completes properly.
        d = self.manager.finishCycle()
        return d.addCallback(
            lambda ignored: self.assertEqual([slave], reset_result_calls))

    def test_failed_to_resume_slave_ready_for_reset(self):
        # When a slave fails to resume, the manager has a Deferred in its
        # Deferred list that is ready to fire with a ResetDispatchResult.

        # Make a failing slave that is requesting a resume.
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')
        slave.resume_requested = True
        slave.resumeSlave = lambda: defer.fail(Failure(('out', 'err', 1)))

        # We only care about this one slave. Reset the list of manager
        # deferreds in case setUp did something unexpected.
        self.manager._deferreds = []
        # Restore the slaveDone method. It's very relevant to this test.
        self.manager.slaveDone = self._realSlaveDone
        self.manager.resumeAndDispatch([slave])
        [d] = self.manager._deferreds

        # The Deferred for our failing slave should be ready to fire
        # successfully with a ResetDispatchResult.
        def check_result(result):
            self.assertIsInstance(result, ResetDispatchResult)
            self.assertEqual(slave, result.slave)
            self.assertFalse(result.processed)
        return d.addCallback(check_result)

    def testCheckDispatch(self):
        """`BuilddManager.checkDispatch` is chained after dispatch requests.

        If the dispatch request fails or a unknown method is given, it
        returns a `FailDispatchResult` (in the test context) that will
        be evaluated later.

        Builders will be marked as failed if the following responses
        categories are received.

         * Legitimate slave failures: when the response is a list with 2
           elements but the first element ('status') does not correspond to
           the expected 'success' result. See `buildd_success_result_map`.

         * Unexpected (code) failures: when the given 'method' is unknown
           or the response isn't a 2-element list or Failure instance.

        Communication failures (a twisted `Failure` instance) will simply
        cause the builder to be reset, a `ResetDispatchResult` object is
        returned. In other words, network failures are ignored in this
        stage, broken builders will be identified and marked as so
        during 'scan()' stage.

        On success dispatching it returns None.
        """
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')

        # Successful legitimate response, None is returned.
        successful_response = [
            buildd_success_result_map.get('ensurepresent'), 'cool builder']
        result = self.manager.checkDispatch(
            successful_response, 'ensurepresent', slave)
        self.assertEqual(
            None, result, 'Successful dispatch checks should return None')

        # Failed legitimate response, results in a `FailDispatchResult`.
        failed_response = [False, 'uncool builder']
        result = self.manager.checkDispatch(
            failed_response, 'ensurepresent', slave)
        self.assertIsDispatchFail(result)
        self.assertEqual(
            '<foo:http://foo.buildd:8221/> failure (uncool builder)',
            repr(result))

        # Twisted Failure response, results in a `ResetDispatchResult`.
        twisted_failure = Failure(ConnectionClosed('Boom!'))
        result = self.manager.checkDispatch(
            twisted_failure, 'ensurepresent', slave)
        self.assertIsDispatchReset(result)
        self.assertEqual(
            '<foo:http://foo.buildd:8221/> reset failure', repr(result))

        # Unexpected response, results in a `FailDispatchResult`.
        unexpected_response = [1, 2, 3]
        result = self.manager.checkDispatch(
            unexpected_response, 'build', slave)
        self.assertIsDispatchFail(result)
        self.assertEqual(
            '<foo:http://foo.buildd:8221/> failure '
            '(Unexpected response: [1, 2, 3])', repr(result))

        # Unknown method was given, results in a `FailDispatchResult`
        result = self.manager.checkDispatch(
            successful_response, 'unknown-method', slave)
        self.assertIsDispatchFail(result)
        self.assertEqual(
            '<foo:http://foo.buildd:8221/> failure '
            '(Unknown slave method: unknown-method)', repr(result))

    def testDispatchBuild(self):
        """Check `dispatchBuild` in various scenarios.

        When there are no recording slaves (i.e. no build got dispatched
        in scan()) it simply finishes the cycle.

        When there is a recording slave with pending slave calls, they are
        performed and if they all succeed the cycle is finished with no
        errors.

        On slave call failure the chain is stopped immediately and an
        FailDispatchResult is collected while finishing the cycle.
        """
        # A functional slave charged with some interactions.
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')
        slave.ensurepresent('arg1', 'arg2', 'arg3')
        slave.build('arg1', 'arg2', 'arg3')

        # If the previous step (resuming) has failed nothing gets dispatched.
        reset_result = ResetDispatchResult(slave)
        result = self.manager.dispatchBuild(reset_result, slave)
        self.assertTrue(result is reset_result)
        self.assertFalse(slave.resume_requested)
        self.assertEqual(0, len(self.manager._deferreds))

        # Operation with the default (funcional slave), no resets or
        # failures results are triggered.
        slave.resume()
        result = self.manager.dispatchBuild(None, slave)
        self.assertEqual(None, result)
        self.assertTrue(slave.resume_requested)
        self.assertEqual(
            [('ensurepresent', 'arg1', 'arg2', 'arg3'),
             ('build', 'arg1', 'arg2', 'arg3')],
            self.test_proxy.calls)
        self.assertEqual(2, len(self.manager._deferreds))

        events = self.manager.finishCycle()
        def check_no_events(results):
            errors = [
                r for s, r in results if isinstance(r, BaseDispatchResult)]
            self.assertEqual(0, len(errors))
        events.addCallback(check_no_events)

        # Create a broken slave and insert interaction that will
        # cause the builder to be marked as fail.
        self.test_proxy = TestingXMLRPCProxy('very broken slave')
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')
        slave.ensurepresent('arg1', 'arg2', 'arg3')
        slave.build('arg1', 'arg2', 'arg3')

        result = self.manager.dispatchBuild(None, slave)
        self.assertEqual(None, result)
        self.assertEqual(1, len(self.manager._deferreds))
        self.assertEqual(
            [('ensurepresent', 'arg1', 'arg2', 'arg3')],
            self.test_proxy.calls)

        events = self.manager.finishCycle()
        def check_events(results):
            [error] = [r for s, r in results if r is not None]
            self.assertEqual(
                '<foo:http://foo.buildd:8221/> failure (very broken slave)',
                repr(error))
            self.assertTrue(error.processed)

        events.addCallback(check_events)

        return events


class TestBuilddManagerScan(TrialTestCase):
    """Tests `BuilddManager.scan` method.

    This method uses the old framework for scanning and dispatching builds.
    """
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup TwistedLayer, TrialTestCase and BuilddSlaveTest.

        Also adjust the sampledata in a way a build can be dispatched to
        'bob' builder.
        """
        TwistedLayer.testSetUp()
        TrialTestCase.setUp(self)
        BuilddSlaveTestSetup().setUp()

        # Creating the required chroots needed for dispatching.
        login('foo.bar@canonical.com')
        test_publisher = SoyuzTestPublisher()
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher.setUpDefaultDistroSeries(hoary)
        test_publisher.addFakeChroots()
        login(ANONYMOUS)

    def tearDown(self):
        BuilddSlaveTestSetup().tearDown()
        TrialTestCase.tearDown(self)
        TwistedLayer.testTearDown()

    def _resetBuilder(self, builder):
        """Reset the given builder and it's job."""
        login('foo.bar@canonical.com')

        builder.builderok = True
        job = builder.currentjob
        if job is not None:
            job.reset()

        transaction.commit()
        login(ANONYMOUS)

    def assertBuildingJob(self, job, builder, logtail=None):
        """Assert the given job is building on the given builder."""
        from lp.services.job.interfaces.job import JobStatus
        if logtail is None:
            logtail = 'Dummy sampledata entry, not processing'

        self.assertTrue(job is not None)
        self.assertEqual(job.builder, builder)
        self.assertTrue(job.date_started is not None)
        self.assertEqual(job.job.status, JobStatus.RUNNING)
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        self.assertEqual(build.status, BuildStatus.BUILDING)
        self.assertEqual(job.logtail, logtail)

    def _getManager(self):
        """Instantiate a BuilddManager object.

        Replace its default logging handler by a testing version.
        """
        manager = BuilddManager()

        for handler in manager.logger.handlers:
            manager.logger.removeHandler(handler)
        manager.logger = BufferLogger()
        manager.logger.name = 'slave-scanner'

        return manager

    def _checkDispatch(self, recording_slaves, builder):
        """`BuilddManager.scan` return a list of `RecordingSlaves`.

        The single slave returned should match the given builder and
        contain interactions that should be performed asynchronously for
        properly dispatching the sampledata job.
        """
        self.assertEqual(
            len(recording_slaves), 1, "Unexpected recording_slaves.")
        [slave] = recording_slaves

        self.assertEqual(slave.name, builder.name)
        self.assertEqual(slave.url, builder.url)
        self.assertEqual(slave.vm_host, builder.vm_host)

        self.assertEqual(
            [('ensurepresent',
              ('0feca720e2c29dafb2c900713ba560e03b758711',
               'http://localhost:58000/93/fake_chroot.tar.gz',
               '', '')),
             ('ensurepresent',
              ('4e3961baf4f56fdbc95d0dd47f3c5bc275da8a33',
               'http://localhost:58000/43/alsa-utils_1.0.9a-4ubuntu1.dsc',
               '', '')),
             ('build',
              ('6358a89e2215e19b02bf91e2e4d009640fae5cf8',
               'binarypackage', '0feca720e2c29dafb2c900713ba560e03b758711',
               {'alsa-utils_1.0.9a-4ubuntu1.dsc':
                '4e3961baf4f56fdbc95d0dd47f3c5bc275da8a33'},
               {'arch_indep': True,
                'archive_private': False,
                'archive_purpose': 'PRIMARY',
                'archives':
                ['deb http://ftpmaster.internal/ubuntu hoary main'],
                'ogrecomponent': 'main',
                'suite': u'hoary'}))],
            slave.calls, "Job was not properly dispatched.")

    def testScanDispatchForResetBuilder(self):
        # A job gets dispatched to the sampledata builder after it's reset.

        # Reset sampledata builder.
        builder = getUtility(IBuilderSet)['bob']
        self._resetBuilder(builder)

        # Run 'scan' and check its result.
        LaunchpadZopelessLayer.switchDbUser(config.builddmaster.dbuser)
        manager = self._getManager()
        d = defer.maybeDeferred(manager.scan)
        d.addCallback(self._checkDispatch, builder)
        return d

    def _checkNoDispatch(self, recording_slaves, builder):
        """Assert that no dispatch has occurred.

        'recording_slaves' is empty, so no interations would be passed
        to the asynchonous dispatcher and the builder remained active
        and IDLE.
        """
        self.assertEqual(
            len(recording_slaves), 0, "Unexpected recording_slaves.")

        builder = getUtility(IBuilderSet).get(builder.id)
        self.assertTrue(builder.builderok)
        self.assertTrue(builder.currentjob is None)

    def testNoDispatchForMissingChroots(self):
        # When a required chroot is not present the `scan` method
        # should not return any `RecordingSlaves` to be processed
        # and the builder used should remain active and IDLE.

        # Reset sampledata builder.
        builder = getUtility(IBuilderSet)['bob']
        self._resetBuilder(builder)

        # Remove hoary/i386 chroot.
        login('foo.bar@canonical.com')
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        pocket_chroot = hoary.getDistroArchSeries('i386').getPocketChroot()
        removeSecurityProxy(pocket_chroot).chroot = None
        transaction.commit()
        login(ANONYMOUS)

        # Run 'scan' and check its result.
        LaunchpadZopelessLayer.switchDbUser(config.builddmaster.dbuser)
        manager = self._getManager()
        d = defer.maybeDeferred(manager.scan)
        d.addCallback(self._checkNoDispatch, builder)
        return d

    def _checkJobRescued(self, recording_slaves, builder, job):
        """`BuilddManager.scan` rescued the job.

        Nothing gets dispatched,  the 'broken' builder remained disabled
        and the 'rescued' job is ready to be dispatched.
        """
        self.assertEqual(
            len(recording_slaves), 0, "Unexpected recording_slaves.")

        builder = getUtility(IBuilderSet).get(builder.id)
        self.assertFalse(builder.builderok)

        job = getUtility(IBuildQueueSet).get(job.id)
        self.assertTrue(job.builder is None)
        self.assertTrue(job.date_started is None)
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        self.assertEqual(build.status, BuildStatus.NEEDSBUILD)

    def testScanRescuesJobFromBrokenBuilder(self):
        # The job assigned to a broken builder is rescued.

        # Sampledata builder is enabled and is assigned to an active job.
        builder = getUtility(IBuilderSet)['bob']
        self.assertTrue(builder.builderok)
        job = builder.currentjob
        self.assertBuildingJob(job, builder)

        # Disable the sampledata builder
        login('foo.bar@canonical.com')
        builder.builderok = False
        transaction.commit()
        login(ANONYMOUS)

        # Run 'scan' and check its result.
        LaunchpadZopelessLayer.switchDbUser(config.builddmaster.dbuser)
        manager = self._getManager()
        d = defer.maybeDeferred(manager.scan)
        d.addCallback(self._checkJobRescued, builder, job)
        return d

    def _checkJobUpdated(self, recording_slaves, builder, job):
        """`BuilddManager.scan` updates legitimate jobs.

        Job is kept assigned to the active builder and its 'logtail' is
        updated.
        """
        self.assertEqual(
            len(recording_slaves), 0, "Unexpected recording_slaves.")

        builder = getUtility(IBuilderSet).get(builder.id)
        self.assertTrue(builder.builderok)

        job = getUtility(IBuildQueueSet).get(job.id)
        self.assertBuildingJob(job, builder, logtail='This is a build log')

    def testScanUpdatesBuildingJobs(self):
        # The job assigned to a broken builder is rescued.

        # Enable sampledata builder attached to an appropriate testing
        # slave. It will respond as if it was building the sampledata job.
        builder = getUtility(IBuilderSet)['bob']

        login('foo.bar@canonical.com')
        builder.builderok = True
        builder.setSlaveForTesting(BuildingSlave(build_id='8-1'))
        transaction.commit()
        login(ANONYMOUS)

        job = builder.currentjob
        self.assertBuildingJob(job, builder)

        # Run 'scan' and check its result.
        LaunchpadZopelessLayer.switchDbUser(config.builddmaster.dbuser)
        manager = self._getManager()
        d = defer.maybeDeferred(manager.scan)
        d.addCallback(self._checkJobUpdated, builder, job)
        return d


class TestDispatchResult(unittest.TestCase):
    """Tests `BaseDispatchResult` variations.

    Variations of `BaseDispatchResult` when evaluated update the database
    information according to their purpose.
    """

    layer = LaunchpadZopelessLayer

    def _getBuilder(self, name):
        """Return a fixed `IBuilder` instance from the sampledata.

        Ensure it's active (builderok=True) and it has a in-progress job.
        """
        login('foo.bar@canonical.com')

        builder = getUtility(IBuilderSet)[name]
        builder.builderok = True

        job = builder.currentjob
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        self.assertEqual(
            'i386 build of mozilla-firefox 0.9 in ubuntu hoary RELEASE',
            build.title)

        self.assertEqual('BUILDING', build.status.name)
        self.assertNotEqual(None, job.builder)
        self.assertNotEqual(None, job.date_started)
        self.assertNotEqual(None, job.logtail)

        transaction.commit()

        return builder, job.id

    def assertJobIsClean(self, job_id):
        """Re-fetch the `IBuildQueue` record and check if it's clean."""
        job = getUtility(IBuildQueueSet).get(job_id)
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        self.assertEqual('NEEDSBUILD', build.status.name)
        self.assertEqual(None, job.builder)
        self.assertEqual(None, job.date_started)
        self.assertEqual(None, job.logtail)

    def testResetDispatchResult(self):
        """`ResetDispatchResult` clean any existing jobs.

        Although it keeps the builder active in pool.
        """
        builder, job_id = self._getBuilder('bob')
        builder.builderok = True

        # Setup a interaction to satisfy 'write_transaction' decorator.
        login(ANONYMOUS)
        slave = RecordingSlave(builder.name, builder.url, builder.vm_host)
        result = ResetDispatchResult(slave)
        result()

        self.assertJobIsClean(job_id)

        # XXX Julian
        # Disabled test until bug 586362 is fixed.
        #self.assertFalse(builder.builderok)
        self.assertEqual(None, builder.currentjob)

    def testFailDispatchResult(self):
        """`FailDispatchResult` excludes the builder from pool.

        It marks the build as failed (builderok=False) and clean any
        existing jobs.
        """
        builder, job_id = self._getBuilder('bob')

        # Setup a interaction to satisfy 'write_transaction' decorator.
        login(ANONYMOUS)
        slave = RecordingSlave(builder.name, builder.url, builder.vm_host)
        result = FailDispatchResult(slave, 'does not work!')
        result()

        self.assertJobIsClean(job_id)

        self.assertFalse(builder.builderok)
        self.assertEqual(None, builder.currentjob)
        self.assertEqual('does not work!', builder.failnotes)


def is_file_growing(filename, poll_interval=1, poll_repeat=10):
    """Poll the file size to see if it grows."""
    last_size = None
    for poll in range(poll_repeat+1):
        try:
            statinfo = os.stat(filename)
            if last_size is None:
                last_size = statinfo.st_size
            elif statinfo.st_size > last_size:
                return True
            else:
                # The file should not be shrinking.
                assert statinfo.st_size == last_size
        except OSError:
            if poll == poll_repeat:
                # Propagate only on the last loop, i.e. give up.
                raise
        time.sleep(poll_interval)
    return False


class TestBuilddManagerScript(unittest.TestCase):

    layer = LaunchpadScriptLayer

    def testBuilddManagerRuns(self):
        # The `buildd-manager.tac` starts and stops correctly.
        BuilddManagerTestSetup().setUp()
        BuilddManagerTestSetup().tearDown()

    def testBuilddManagerLogging(self):
        # The twistd process loggs as execpected.
        test_setup = BuilddManagerTestSetup()
        logfilepath = test_setup.logfile
        test_setup.setUp()
        # The process loggs to its logfile.
        self.assertTrue(is_file_growing(logfilepath))
        # After rotating the log, the process keeps using the old file, no
        # new file is created.
        rotated_logfilepath = logfilepath+'.1'
        os.rename(logfilepath, rotated_logfilepath)
        self.assertTrue(is_file_growing(rotated_logfilepath))
        self.assertFalse(os.access(logfilepath, os.F_OK))
        # Upon receiving the USR1 signal, the process will re-open its log
        # file at the old location.
        test_setup.sendSignal(signal.SIGUSR1)
        self.assertTrue(is_file_growing(logfilepath))
        self.assertTrue(os.access(rotated_logfilepath, os.F_OK))
        test_setup.tearDown()

    def testBuilddManagerLoggingNoRotation(self):
        # The twistd process does not perform its own rotation.
        # By default twistd will rotate log files that grow beyond
        # 1000000 bytes but this is deactivated for the buildd manager.
        test_setup = BuilddManagerTestSetup()
        logfilepath = test_setup.logfile
        rotated_logfilepath = logfilepath+'.1'
        # Prefill the log file to just under 1000000 bytes.
        test_setup.precreateLogfile(
            "2010-07-27 12:36:54+0200 [-] Starting scanning cycle.\n", 18518)
        test_setup.setUp()
        # The process loggs to the logfile.
        self.assertTrue(is_file_growing(logfilepath))
        # No rotation occured.
        self.assertFalse(
            os.access(rotated_logfilepath, os.F_OK),
            "Twistd's log file was rotated by twistd.")
        test_setup.tearDown()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
