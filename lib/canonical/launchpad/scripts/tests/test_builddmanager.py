# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the renovated slave scanner aka BuilddManager."""

import unittest

import transaction

from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase

from zope.component import getUtility

from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces.builder import IBuilderSet
from canonical.launchpad.interfaces.buildqueue import IBuildQueueSet
from canonical.launchpad.scripts.builddmanager import (
    BaseBuilderRequest, BuilddManager, FailBuilderRequest, RecordingSlave,
    ResetBuilderRequest)
from canonical.launchpad.scripts.logger import BufferLogger
from canonical.testing.layers import (
    DatabaseFunctionalLayer, TwistedLayer)


class TestRecordingSlaves(TrialTestCase):
    """Tests for the recording slave class."""
    layer = TwistedLayer

    def setUp(self):
        """Setup a fresh `RecordingSlave` for tests."""
        TrialTestCase.setUp(self)
        self.slave = RecordingSlave('foo', 'http://foo:8221/rpc')

    def testInstantiation(self):
        """`RecordingSlave` has a custom representation.

        It encloses builder name and xmlrpc url for debug purposes.
        """
        self.assertEqual('<foo:http://foo:8221/rpc>', repr(self.slave))

    def testEnsurePresent(self):
        """`RecordingSlave.ensurepresent` always succeed.

        It returns the expected succeed code and records the interation
        information for later use.
        """
        self.assertEqual(
            (True, 'Download'),
            self.slave.ensurepresent('boing', 'bar', 'baz'))
        self.assertEqual(
            [('ensurepresent', ('boing', 'bar', 'baz'))],
            self.slave.calls)

    def testBuild(self):
        """`RecordingSlave.build` always succeed.

        It returns the expected succeed code and records the interation
        information for later use.
        """
        self.assertEqual(
            ('BuilderStatus.BUILDING', 'boing'),
            self.slave.build('boing', 'bar', 'baz'))
        self.assertEqual(
            [('build', ('boing', 'bar', 'baz'))],
            self.slave.calls)

    def testResume(self):
        """`RecordingSlave.resumeHost` returns a deferred resume request."""
        cmd_argv = 'echo hello world'.split()
        logger = BufferLogger()

        self.assertFalse(self.slave.resume)

        self.assertEqual(
            ('', '', 0), self.slave.resumeHost(logger, cmd_argv))
        self.assertTrue(self.slave.resume)
        self.assertEqual(
            ['echo', 'hello', 'world'], self.slave.resume_argv)
        self.assertEqual(
            'DEBUG: Recording slave reset request for %s http://foo:8221/rpc',
            logger.buffer.getvalue().strip())

        def check_resume(response):
            out, err, code = response
            self.assertEqual(0, code)
            self.assertEqual('', err)
            self.assertEqual('hello world', out.strip())

        d = self.slave.resumeSlaveHost()
        d.addCallback(check_resume)
        return d


class TestingXMLRPCProxy:
    """This class mimics a twisted XMLRPC Proxy class."""

    def __init__(self, failure_info=None):
        self.calls = []
        self.failure_info = failure_info
        self.works = failure_info is None

    def callRemote(self, *args):
        self.calls.append(args)
        return defer.maybeDeferred(lambda: (self.works, self.failure_info))


class TestingResetBuilderRequest(ResetBuilderRequest):

    def __call__(self):
        pass


class TestingFailBuilderRequest(FailBuilderRequest):

    def __call__(self):
        pass


class TestingBuilddManager(BuilddManager):

    reset_request = TestingResetBuilderRequest
    fail_request = TestingFailBuilderRequest


class TestBuilddManager(TrialTestCase):
    """Tests for the actual build slave manager."""
    layer = TwistedLayer

    def setUp(self):
        TrialTestCase.setUp(self)
        self.manager = TestingBuilddManager()
        self.manager.logger = BufferLogger()

        # We will use an intrumented BuilddManager.
        self.stopped = False
        def testNextCycle():
            self.stopped = True
        self.manager.nextCycle = testNextCycle

        self.test_proxy = TestingXMLRPCProxy()
        def testGetProxyForSlave(slave):
            return self.test_proxy
        self.manager._getProxyForSlave = testGetProxyForSlave

        def testScan():
            return (RecordingSlave(name, 'http://%s:8221/rpc/')
                    for name in ['foo', 'bar'])
        self.manager.scan = testScan

        def testSlaveDone(slave):
            pass
        self.manager.slaveDone = testSlaveDone

    def testFinishCycle(self):
        """Check if the chain is terminated and database updates are done.

        'BuilddManager.stopWhenDone' verifies the number of active deferreds
        and once they cease it performs all needed database updates (builder
        reset or failure) synchronously and call `BuilddManager.gameOver`.
        """
        # There are no active deferreds in a just intantiated BuilddManager.
        self.assertEqual(0, len(self.manager._deferreds))

        # Fill the deferred list with events we can check later.
        reset_me = TestingResetBuilderRequest(
            RecordingSlave('foo', 'http://foo'))
        fail_me = TestingFailBuilderRequest(
            RecordingSlave('bar', 'http://bar'), 'boingo')
        self.manager._deferreds.extend(
            [defer.succeed(reset_me), defer.succeed(fail_me), defer.fail()])

        # When `finishCycle` is called, and it is called after all build
        # slave interation, active deferreds are consumed.
        events = self.manager.finishCycle()
        def check_events(results):
            self.assertTrue(self.stopped)
            [reset, fail] = [
                r for s, r in results if isinstance(r, BaseBuilderRequest)]
            self.assertEqual(
                '<foo:http://foo> reset', repr(reset))
            self.assertEqual(
                '<bar:http://bar> failure (boingo)', repr(fail))
        events.addCallback(check_events)
        return events

    def testScannedSlaves(self):
        """`BuilddManager.scan` return a list of `RecordingSlaves`.

        The returned slaves contain interactions that should be performed
        asynchronously.
        """
        slaves = self.manager.scan()
        self.assertEqual(['foo', 'bar'], [slave.name for slave in slaves])

    def testCheckResume(self):
        """`BuilddManager.checkResume` is chained after resume requests.

        If the resume request succeed it returns None, otherwise it returns
        a `ResetBuildRequest` (the one in the test context) that will be
        collect and evaluated later.

        See `RecordingSlave.resumeHost` for more information about the resume
        result contents.
        """
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/')

        successful_response = ('', '', 0)
        result = self.manager.checkResume(
            successful_response, slave)
        self.assertEqual(None, result)

        failed_response = ('', '', 1)
        result = self.manager.checkResume(
            failed_response, slave)
        self.assertTrue(isinstance(result, TestingResetBuilderRequest))
        self.assertEqual(
            '<foo:http://foo.buildd:8221/> reset', repr(result))

    def testCheckDispatch(self):
        """`BuilddManager.checkDispatch` is chained after dispatch requests.

        If the dispatch request fails it returns a `FailBuilderRequest`
        (in the test context) that will be evaluated later. On success
        dispatching it returns None.
        """
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/')
        successful_response = (True, 'cool builder')
        result = self.manager.checkDispatch(successful_response, slave)
        self.assertEqual(None, result)

        failed_response = (False, 'uncool builder')
        result = self.manager.checkDispatch(failed_response, slave)
        self.assertTrue(isinstance(result, TestingFailBuilderRequest))
        self.assertEqual(
            '<foo:http://foo.buildd:8221/> failure (uncool builder)',
            repr(result))

    def testDispatchBuild(self):
        # A functional slave charged with some interactions.
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/')
        slave.ensurepresent('boing', 'bar', 'baz')
        slave.build('boing', 'bar', 'baz')

        # If the previous step (resuming) has failed nothing gets dispatched.
        result = self.manager.dispatchBuild('ERROR', slave)
        self.assertEqual('ERROR', result)
        self.assertEqual(0, len(self.manager._deferreds))

        # Operation with the default (funcional slave), no resets or
        # failures are triggered.
        result = self.manager.dispatchBuild(None, slave)
        self.assertEqual(None, result)
        self.assertEqual(
            [('ensurepresent', 'boing', 'bar', 'baz'),
             ('build', 'boing', 'bar', 'baz')],
            self.test_proxy.calls)
        self.assertEqual(2, len(self.manager._deferreds))

        events = self.manager.finishCycle()
        def check_events(results):
            errors = [
                r for s, r in results if isinstance(r, BaseBuilderRequest)]
            self.assertEqual(0, len(errors))
        events.addCallback(check_events)

        # Create a broken slave and insert interaction that will
        # cause the builder to be marked as fail.
        self.test_proxy = TestingXMLRPCProxy('very broken slave')
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/')
        slave.ensurepresent('boing', 'bar', 'baz')
        slave.build('boing', 'bar', 'baz')

        result = self.manager.dispatchBuild(None, slave)
        self.assertEqual(None, result)
        self.assertEqual(1, len(self.manager._deferreds))
        self.assertEqual(
            [('ensurepresent', 'boing', 'bar', 'baz')],
            self.test_proxy.calls)

        events = self.manager.finishCycle()
        def check_events(results):
            [error] = [r for s, r in results if r is not None]
            self.assertEqual(
                '<foo:http://foo.buildd:8221/> failure (very broken slave)',
                repr(error))
        events.addCallback(check_events)

        return events


class TestBuilderRequest(unittest.TestCase):
    """Tests `BaseBuilderRequest` variations."""

    layer = DatabaseFunctionalLayer

    def _getBuilder(self):
        """Return a fixed `IBuilder` instance from the sampledata.

        Ensure it's active (builderok=True) and it has a in-progress job.
        """
        login('foo.bar@canonical.com')

        builder = getUtility(IBuilderSet)['bob']
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

    def testResetBuilderRequest(self):
        """`ResetBuilderRequest` clean any existing jobs.

        Although it keeps the builder active in pool.
        """
        builder, job_id = self._getBuilder()

        login(ANONYMOUS)
        slave = RecordingSlave(builder.name, builder.url)
        request = ResetBuilderRequest(slave)
        request()

        self.assertJobIsClean(job_id)

        self.assertTrue(builder.builderok)
        self.assertEqual(None, builder.currentjob)

    def testFailBuilderRequest(self):
        """`FailBuilderRequest` excludes the builder from pool.

        It marks the build as failed (builderok=False) and clean any
        existing jobs.
        """
        builder, job_id = self._getBuilder()

        login(ANONYMOUS)
        slave = RecordingSlave(builder.name, builder.url)
        request = FailBuilderRequest(slave, 'does not work!')
        request()

        self.assertJobIsClean(job_id)

        self.assertFalse(builder.builderok)
        self.assertEqual(None, builder.currentjob)
        self.assertEqual('does not work!', builder.failnotes)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
