# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the renovated slave scanner aka BuilddManager."""

import os
import transaction
import unittest

from twisted.internet import defer
from twisted.internet.error import ConnectionClosed
from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase as TrialTestCase

from zope.component import getUtility

from canonical.buildd.tests import BuilddSlaveTestSetup
from canonical.config import config
from canonical.buildmaster.manager import (
    BaseDispatchResult, BuilddManager, FailDispatchResult, RecordingSlave,
    ResetDispatchResult, buildd_success_result_map)
from canonical.launchpad.ftests import ANONYMOUS, login
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.interfaces.buildqueue import IBuildQueueSet
from lp.registry.interfaces.distribution import IDistributionSet
from canonical.launchpad.scripts.logger import BufferLogger
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from canonical.testing.layers import (
    LaunchpadZopelessLayer, TwistedLayer)


class TestRecordingSlaves(TrialTestCase):
    """Tests for the recording slave class."""
    layer = TwistedLayer

    def setUp(self):
        """Setup a fresh `RecordingSlave` for tests."""
        TrialTestCase.setUp(self)
        self.slave = RecordingSlave(
            'foo', 'http://foo:8221/rpc', 'foo.host')

    def testInstantiation(self):
        """`RecordingSlave` has a custom representation.

        It encloses builder name and xmlrpc url for debug purposes.
        """
        self.assertEqual('<foo:http://foo:8221/rpc>', repr(self.slave))

    def testEnsurePresent(self):
        """`RecordingSlave.ensurepresent` always succeeds.

        It returns the expected succeed code and records the interaction
        information for later use.
        """
        self.assertEqual(
            [True, 'Download'],
            self.slave.ensurepresent('boing', 'bar', 'baz'))
        self.assertEqual(
            [('ensurepresent', ('boing', 'bar', 'baz'))],
            self.slave.calls)

    def testBuild(self):
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

    def testResume(self):
        """`RecordingSlave.resumeHost` returns a deferred resume request."""
        # Resume isn't requested in a just-instantiated RecordingSlave.
        self.assertFalse(self.slave.resume_requested)

        # When resume is called, it returns the success list and mark
        # the slave for resuming.
        self.assertEqual(['', '', os.EX_OK], self.slave.resume())
        self.assertTrue(self.slave.resume_requested)

        # The configuration testing command-line.
        self.assertEqual(
            'echo %(vm_host)s', config.builddmaster.vm_resume_command)

        # When executed it returns the expected output.
        def check_resume_success(response):
            out, err, code = response
            self.assertEqual(os.EX_OK, code)
            self.assertEqual('', err)
            self.assertEqual('foo.host', out.strip())

        d1 = self.slave.resumeSlave()
        d1.addCallback(check_resume_success)

        # Override the configuration command-line with one that will fail.
        failed_config = """
        [builddmaster]
        vm_resume_command: test "%(vm_host)s = 'no-sir'"
        """
        config.push('vm_resume_command', failed_config)

        def check_resume_failure(response):
            out, err, code = response
            self.assertNotEqual(os.EX_OK, code)
            self.assertEqual('', err)
            self.assertEqual('', out)
            config.pop('vm_resume_command')

        d2 = self.slave.resumeSlave()
        d2.addCallback(check_resume_failure)

        return defer.DeferredList([d1, d2])


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
                '<foo:http://foo> reset', repr(reset))
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

    def testCheckResume(self):
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

        failed_response = ['', '', os.EX_USAGE]
        result = self.manager.checkResume(failed_response, slave)
        self.assertIsDispatchReset(result)
        self.assertEqual(
            '<foo:http://foo.buildd:8221/> reset', repr(result))

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
            '<foo:http://foo.buildd:8221/> reset', repr(result))

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
        unused = test_publisher.setUpDefaultDistroSeries(hoary)
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
              ('11-2',
               'debian', '0feca720e2c29dafb2c900713ba560e03b758711',
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
        self.assertTrue(job.buildstart is None)
        self.assertEqual(job.build.buildstate, BuildStatus.NEEDSBUILD)

    def testScanRescuesJobFromBrokenBuilder(self):
        # The job assigned to a broken builder is rescued.

        # Sampledata builder is broken and is holding a active job.
        broken_builder = getUtility(IBuilderSet)['bob']
        self.assertFalse(broken_builder.builderok)
        lost_job = broken_builder.currentjob
        self.assertTrue(lost_job is not None)
        self.assertEqual(lost_job.builder, broken_builder)
        self.assertTrue(lost_job.buildstart is not None)
        self.assertEqual(lost_job.build.buildstate, BuildStatus.BUILDING)

        # Run 'scan' and check its result.
        LaunchpadZopelessLayer.switchDbUser(config.builddmaster.dbuser)
        manager = self._getManager()
        d = defer.maybeDeferred(manager.scan)
        d.addCallback(self._checkJobRescued, broken_builder, lost_job)
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
        self.assertEqual(
            'i386 build of mozilla-firefox 0.9 in ubuntu hoary RELEASE',
            job.build.title)

        self.assertEqual('BUILDING', job.build.buildstate.name)
        self.assertNotEqual(None, job.builder)
        self.assertNotEqual(None, job.buildstart)
        self.assertNotEqual(None, job.logtail)

        transaction.commit()

        return builder, job.id

    def assertJobIsClean(self, job_id):
        """Re-fetch the `IBuildQueue` record and check if it's clean."""
        job = getUtility(IBuildQueueSet).get(job_id)
        self.assertEqual('NEEDSBUILD', job.build.buildstate.name)
        self.assertEqual(None, job.builder)
        self.assertEqual(None, job.buildstart)
        self.assertEqual(None, job.logtail)

    def testResetDispatchResult(self):
        """`ResetDispatchResult` clean any existing jobs.

        Although it keeps the builder active in pool.
        """
        builder, job_id = self._getBuilder('bob')

        # Setup a interaction to satisfy 'write_transaction' decorator.
        login(ANONYMOUS)
        slave = RecordingSlave(builder.name, builder.url, builder.vm_host)
        result = ResetDispatchResult(slave)
        result()

        self.assertJobIsClean(job_id)

        self.assertTrue(builder.builderok)
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
