# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the renovated slave scanner aka BuilddManager."""

import os
import signal
import time
import transaction
import unittest

from twisted.internet import defer, reactor, task
from twisted.internet.error import ConnectionClosed
from twisted.internet.task import Clock, deferLater
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
    BaseDispatchResult, BuilddManager, SlaveScanner, FailDispatchResult,
    NewBuildersScanner, RecordingSlave, ResetDispatchResult,
    buildd_success_result_map)
from lp.buildmaster.tests.harness import BuilddManagerTestSetup
from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.tests.soyuzbuilddhelpers import BuildingSlave
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing import TestCase as LaunchpadTestCase


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


class TestingSlaveScanner(SlaveScanner):
    """Override the dispatch result factories """

    reset_result = TestingResetDispatchResult
    fail_result = TestingFailDispatchResult


class TestSlaveScanner(TrialTestCase):
    """Tests for the actual build slave manager."""
    layer = TwistedLayer

    def setUp(self):
        TrialTestCase.setUp(self)
        self.manager = TestingSlaveScanner("bob", BufferLogger())

        # We will use an instrumented SlaveScanner instance for tests in
        # this context.

        # Stop cyclic execution and record the end of the cycle.
        self.stopped = False

        def testNextCycle():
            self.stopped = True

        self.manager.scheduleNextScanCycle = testNextCycle

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
        def testslaveConversationEnded():
            pass
        self._realslaveConversationEnded = self.manager.slaveConversationEnded
        self.manager.slaveConversationEnded = testslaveConversationEnded

    def assertIsDispatchReset(self, result):
        self.assertTrue(
            isinstance(result, TestingResetDispatchResult),
            'Dispatch failure did not result in a ResetBuildResult object')

    def assertIsDispatchFail(self, result):
        self.assertTrue(
            isinstance(result, TestingFailDispatchResult),
            'Dispatch failure did not result in a FailBuildResult object')

    def test_checkResume(self):
        """`SlaveScanner.checkResume` is chained after resume requests.

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
        slave.resumeSlave = lambda: deferLater(
            reactor, 0, defer.fail, Failure(('out', 'err', 1)))

        # Make the manager log the reset result calls.
        self.manager.reset_result = LoggingResetResult

        # We only care about this one slave. Reset the list of manager
        # deferreds in case setUp did something unexpected.
        self.manager._deferred_list = []

        # Here, we're patching the slaveConversationEnded method so we can
        # get an extra callback at the end of it, so we can
        # verify that the reset_result was really called.
        def _slaveConversationEnded():
            d = self._realslaveConversationEnded()
            return d.addCallback(
                lambda ignored: self.assertEqual([slave], reset_result_calls))
        self.manager.slaveConversationEnded = _slaveConversationEnded

        self.manager.resumeAndDispatch(slave)

    def test_failed_to_resume_slave_ready_for_reset(self):
        # When a slave fails to resume, the manager has a Deferred in its
        # Deferred list that is ready to fire with a ResetDispatchResult.

        # Make a failing slave that is requesting a resume.
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')
        slave.resume_requested = True
        slave.resumeSlave = lambda: defer.fail(Failure(('out', 'err', 1)))

        # We only care about this one slave. Reset the list of manager
        # deferreds in case setUp did something unexpected.
        self.manager._deferred_list = []
        # Restore the slaveConversationEnded method. It's very relevant to
        # this test.
        self.manager.slaveConversationEnded = self._realslaveConversationEnded
        self.manager.resumeAndDispatch(slave)
        [d] = self.manager._deferred_list

        # The Deferred for our failing slave should be ready to fire
        # successfully with a ResetDispatchResult.
        def check_result(result):
            self.assertIsInstance(result, ResetDispatchResult)
            self.assertEqual(slave, result.slave)
            self.assertFalse(result.processed)
        return d.addCallback(check_result)

    def testCheckDispatch(self):
        """`SlaveScanner.checkDispatch` is chained after dispatch requests.

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

    def test_initiateDispatch(self):
        """Check `dispatchBuild` in various scenarios.

        When there are no recording slaves (i.e. no build got dispatched
        in scan()) it simply finishes the cycle.

        When there is a recording slave with pending slave calls, they are
        performed and if they all succeed the cycle is finished with no
        errors.

        On slave call failure the chain is stopped immediately and an
        FailDispatchResult is collected while finishing the cycle.
        """
        def check_no_events(results):
            errors = [
                r for s, r in results if isinstance(r, BaseDispatchResult)]
            self.assertEqual(0, len(errors))

        def check_events(results):
            [error] = [r for s, r in results if r is not None]
            self.assertEqual(
                '<foo:http://foo.buildd:8221/> failure (very broken slave)',
                repr(error))
            self.assertTrue(error.processed)

        def _wait_on_deferreds_then_check_no_events():
            dl = self._realslaveConversationEnded()
            dl.addCallback(check_no_events)

        def _wait_on_deferreds_then_check_events():
            dl = self._realslaveConversationEnded()
            dl.addCallback(check_events)

        # A functional slave charged with some interactions.
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')
        slave.ensurepresent('arg1', 'arg2', 'arg3')
        slave.build('arg1', 'arg2', 'arg3')

        # If the previous step (resuming) has failed nothing gets dispatched.
        reset_result = ResetDispatchResult(slave)
        result = self.manager.initiateDispatch(reset_result, slave)
        self.assertTrue(result is reset_result)
        self.assertFalse(slave.resume_requested)
        self.assertEqual(0, len(self.manager._deferred_list))

        # Operation with the default (funcional slave), no resets or
        # failures results are triggered.
        slave.resume()
        result = self.manager.initiateDispatch(None, slave)
        self.assertEqual(None, result)
        self.assertTrue(slave.resume_requested)
        self.assertEqual(
            [('ensurepresent', 'arg1', 'arg2', 'arg3'),
             ('build', 'arg1', 'arg2', 'arg3')],
            self.test_proxy.calls)
        self.assertEqual(2, len(self.manager._deferred_list))

        # Monkey patch the slaveConversationEnded method so we can chain a
        # callback to check the end of the result chain.
        self.manager.slaveConversationEnded = \
            _wait_on_deferreds_then_check_no_events
        events = self.manager.slaveConversationEnded()

        # Create a broken slave and insert interaction that will
        # cause the builder to be marked as fail.
        self.test_proxy = TestingXMLRPCProxy('very broken slave')
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/', 'foo.host')
        slave.ensurepresent('arg1', 'arg2', 'arg3')
        slave.build('arg1', 'arg2', 'arg3')

        result = self.manager.initiateDispatch(None, slave)
        self.assertEqual(None, result)
        self.assertEqual(3, len(self.manager._deferred_list))
        self.assertEqual(
            [('ensurepresent', 'arg1', 'arg2', 'arg3')],
            self.test_proxy.calls)

        # Monkey patch the slaveConversationEnded method so we can chain a
        # callback to check the end of the result chain.
        self.manager.slaveConversationEnded = \
            _wait_on_deferreds_then_check_events
        events = self.manager.slaveConversationEnded()

        return events


class TestSlaveScannerScan(TrialTestCase):
    """Tests `SlaveScanner.scan` method.

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
        """Instantiate a SlaveScanner object.

        Replace its default logging handler by a testing version.
        """
        manager = SlaveScanner("bob", BufferLogger())
        manager.logger.name = 'slave-scanner'

        return manager

    def _checkDispatch(self, slave, builder):
        """`SlaveScanner.scan` returns a `RecordingSlave`.

        The single slave returned should match the given builder and
        contain interactions that should be performed asynchronously for
        properly dispatching the sampledata job.
        """
        self.assertFalse(
            slave is None, "Unexpected recording_slaves.")

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
                'arch_tag': 'i386',
                'archive_private': False,
                'archive_purpose': 'PRIMARY',
                'archives':
                ['deb http://ftpmaster.internal/ubuntu hoary main'],
                'build_debug_symbols': False,
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

    def _checkNoDispatch(self, recording_slave, builder):
        """Assert that no dispatch has occurred.

        'recording_slave' is None, so no interations would be passed
        to the asynchonous dispatcher and the builder remained active
        and IDLE.
        """
        self.assertTrue(
            recording_slave is None, "Unexpected recording_slave.")

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

    def _checkJobRescued(self, slave, builder, job):
        """`SlaveScanner.scan` rescued the job.

        Nothing gets dispatched,  the 'broken' builder remained disabled
        and the 'rescued' job is ready to be dispatched.
        """
        self.assertTrue(
            slave is None, "Unexpected slave.")

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

    def _checkJobUpdated(self, slave, builder, job):
        """`SlaveScanner.scan` updates legitimate jobs.

        Job is kept assigned to the active builder and its 'logtail' is
        updated.
        """
        self.assertTrue(slave is None, "Unexpected slave.")

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


class TestBuilddManager(TrialTestCase):

    layer = LaunchpadZopelessLayer

    def _stub_out_scheduleNextScanCycle(self):
        # stub out the code that adds a callLater, so that later tests
        # don't get surprises.
        self.patch(SlaveScanner, 'scheduleNextScanCycle', FakeMethod())

    def test_addScanForBuilders(self):
        # Test that addScanForBuilders generates NewBuildersScanner objects.
        self._stub_out_scheduleNextScanCycle()

        manager = BuilddManager()
        builder_names = set(
            builder.name for builder in getUtility(IBuilderSet))
        scanners = manager.addScanForBuilders(builder_names)
        scanner_names = set(scanner.builder_name for scanner in scanners)
        self.assertEqual(builder_names, scanner_names)

    def test_startService_adds_NewBuildersScanner(self):
        # When startService is called, the manager will start up a
        # NewBuildersScanner object.
        self._stub_out_scheduleNextScanCycle()
        clock = task.Clock()
        manager = BuilddManager(clock=clock)

        # Replace scan() with FakeMethod so we can see if it was called.
        manager.new_builders_scanner.scan = FakeMethod()

        manager.startService()
        advance = NewBuildersScanner.SCAN_INTERVAL + 1
        clock.advance(advance)
        self.assertNotEqual(0, manager.new_builders_scanner.scan.call_count)


class TestNewBuilders(TrialTestCase):
    """Test detecting of new builders."""

    layer = LaunchpadZopelessLayer

    def _getScanner(self, manager=None, clock=None):
        return NewBuildersScanner(manager=manager, clock=clock)

    def test_init_stores_existing_builders(self):
        # Make sure that NewBuildersScanner initialises itself properly
        # by storing a list of existing builders.
        all_builders = [builder.name for builder in getUtility(IBuilderSet)]
        builder_scanner = self._getScanner()
        self.assertEqual(all_builders, builder_scanner.current_builders)

    def test_scheduleScan(self):
        # Test that scheduleScan calls the "scan" method.
        clock = task.Clock()
        builder_scanner = self._getScanner(clock=clock)
        builder_scanner.scan = FakeMethod()
        builder_scanner.scheduleScan()

        advance = NewBuildersScanner.SCAN_INTERVAL + 1
        clock.advance(advance)
        self.assertNotEqual(
            0, builder_scanner.scan.call_count,
            "scheduleScan did not schedule anything")

    def test_checkForNewBuilders(self):
        # Test that checkForNewBuilders() detects a new builder

        # The basic case, where no builders are added.
        builder_scanner = self._getScanner()
        self.assertEqual([], builder_scanner.checkForNewBuilders())

        # Add two builders and ensure they're returned.
        new_builders = ["scooby", "lassie"]
        factory = LaunchpadObjectFactory()
        for builder_name in new_builders:
            factory.makeBuilder(name=builder_name)
        self.assertEqual(
            new_builders, builder_scanner.checkForNewBuilders())

    def test_scan(self):
        # See if scan detects new builders and schedules the next scan.

        # stub out the addScanForBuilders and scheduleScan methods since
        # they use callLater; we only want to assert that they get
        # called.
        def fake_checkForNewBuilders():
            return "new_builders"

        def fake_addScanForBuilders(new_builders):
            self.assertEqual("new_builders", new_builders)

        clock = task.Clock()
        builder_scanner = self._getScanner(BuilddManager(), clock=clock)
        builder_scanner.checkForNewBuilders = fake_checkForNewBuilders
        builder_scanner.manager.addScanForBuilders = fake_addScanForBuilders
        builder_scanner.scheduleScan = FakeMethod()

        builder_scanner.scan()
        advance = NewBuildersScanner.SCAN_INTERVAL + 1
        clock.advance(advance)
        self.assertNotEqual(
            0, builder_scanner.scheduleScan.call_count,
            "scheduleScan did not get called")


def is_file_growing(filepath, poll_interval=1, poll_repeat=10):
    """Poll the file size to see if it grows.

    Checks the size of the file in given intervals and returns True as soon as
    it sees the size increase between two polls. If the size does not
    increase after a given number of polls, the function returns False.
    If the file does not exist, the function silently ignores that and waits
    for it to appear on the next pall. If it has not appeared by the last
    poll, the exception is propagated.
    Program execution is blocked during polling.

    :param filepath: The path to the file to be palled.
    :param poll_interval: The number of seconds in between two polls.
    :param poll_repeat: The number times to repeat the polling, so the size is
        polled a total of poll_repeat+1 times. The default values create a
        total poll time of 11 seconds. The BuilddManager logs
        "scanning cycles" every 5 seconds so these settings should see an
        increase if the process is logging to this file.
    """
    last_size = None
    for poll in range(poll_repeat+1):
        try:
            statinfo = os.stat(filepath)
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


class TestBuilddManagerScript(LaunchpadTestCase):

    layer = LaunchpadScriptLayer

    def testBuilddManagerRuns(self):
        # The `buildd-manager.tac` starts and stops correctly.
        BuilddManagerTestSetup().setUp()
        BuilddManagerTestSetup().tearDown()

    # XXX Julian 2010-08-06 bug=614275
    # These next 2 tests are in the wrong place, they should be near the
    # implementation of RotatableFileLogObserver and not depend on the
    # behaviour of the buildd-manager.  I've disabled them here because
    # they prevented me from landing this branch which reduces the
    # logging output.

    def disabled_testBuilddManagerLogging(self):
        # The twistd process logs as execpected.
        test_setup = BuilddManagerTestSetup()
        logfilepath = test_setup.logfile
        test_setup.setUp()
        self.addCleanup(test_setup.tearDown)
        # The process logs to its logfile.
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

    def disabled_testBuilddManagerLoggingNoRotation(self):
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
        self.addCleanup(test_setup.tearDown)
        # The process logs to the logfile.
        self.assertTrue(is_file_growing(logfilepath))
        # No rotation occured.
        self.assertFalse(
            os.access(rotated_logfilepath, os.F_OK),
            "Twistd's log file was rotated by twistd.")
