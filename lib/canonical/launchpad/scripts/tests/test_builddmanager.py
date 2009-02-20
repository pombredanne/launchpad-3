# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the renovated slave scanner aka BuilddManager."""

import unittest

import transaction

from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase

from zope.component import getUtility

from canonical.launchpad.ftests import login, logout
from canonical.launchpad.interfaces.builder import IBuilderSet
from canonical.launchpad.interfaces.buildqueue import IBuildQueueSet
from canonical.launchpad.scripts.builddmanager import (
    BuilddManager, BuilddManagerHelper, RecordingSlave)
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


class TestBuilddManagerHelper:
    """This class mimics the BuilddManagerHelper class."""

    def __init__(self):
        self.builders_reset = []
        self.builders_failed = []

    def scanAllBuilders(self):
        fake_slaves = (
            RecordingSlave(name, 'http://%s:8221/rpc/')
            for name in ['foo', 'bar'])
        return fake_slaves

    def resetBuilder(self, name):
        self.builders_reset.append(name)

    def failBuilder(self, name, info):
        self.builders_failed.append((name, info))


class TestXMLRPCProxy:
    """This class mimics a twisted XMLRPC Proxy class."""

    def __init__(self, failure_info=None):
        self.calls = []
        self.failure_info = failure_info
        self.works = failure_info is None

    def callRemote(self, *args):
        self.calls.append(args)
        return defer.maybeDeferred(lambda: (self.works, self.failure_info))


class TestBuilddManager(TrialTestCase):
    """Tests for the actual build slave manager."""
    layer = TwistedLayer

    def setUp(self):
        TrialTestCase.setUp(self)
        self.manager = BuilddManager()
        self.manager.helper = TestBuilddManagerHelper()

        # We will instrument the `gameOver` method and schedule one reset
        # and one failure update.
        self.stopped = False
        def game_over():
            self.stopped = True
        self.manager.gameOver = game_over

        self.test_proxy = TestXMLRPCProxy()
        def getTestProxy(slave):
            return self.test_proxy
        self.manager._getProxyForSlave = getTestProxy

    def testFinishCycle(self):
        """Check if the chain is terminated and database updates are done.

        'BuilddManager.stopWhenDone' verifies the number of active deferreds
        and once they cease it performs all needed database updates (builder
        reset or failure) synchronously and call `BuilddManager.gameOver`.
        """
        # There are no active deferreds in a just intantiated BuilddManager.
        self.assertEqual(0, len(self.manager._deferreds))

        self.manager.builders_to_reset = ['foo']
        self.manager.builders_to_fail = [('bar', 'boingo')]

        # When `finishCycle` is called, and it is called after all build
        # slave interation, active deferreds are consumed.
        self.manager._deferreds.extend(
            [defer.succeed(True), defer.fail()])
        wait_for = self.manager.finishCycle()

        self.assertTrue(self.stopped)
        self.assertEqual(
            ['foo'], self.manager.helper.builders_reset)
        self.assertEqual(
            [('bar', 'boingo')], self.manager.helper.builders_failed)

        return wait_for

    def testScannedSlaves(self):
        """`BuilddManager.scan` return a list of `RecordingSlaves`.

        The returned slaves contain interactions that should be performed
        asynchronously.
        """
        slaves = self.manager.scan()
        self.assertEqual(['foo', 'bar'], [slave.name for slave in slaves])

    def testCheckResume(self):
        """`BuilddManager.checkResume` is chained after resume requests.

        If the resume request succeed it returns True, otherwise it returns
        False and schedule the build for database reset.

        See `RecordingSlave.resumeHost` for more information about the resume
        result contents.
        """
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/')
        successful_response = ('', '', 0)
        result = self.manager.checkResume(
            successful_response, slave)
        self.assertTrue(result)
        self.assertEqual(
            [], self.manager.builders_to_reset)

        failed_response = ('', '', 1)
        result = self.manager.checkResume(
            failed_response, slave)
        self.assertFalse(result)
        self.assertEqual(
            ['foo'], self.manager.builders_to_reset)

    def testCheckDispatch(self):
        """`BuilddManager.checkDispatch` is chained after dispatch requests.

        If the dispatch request fails it schedules the build for database
        failure update.
        """
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/')
        successful_response = (True, 'cool builder')
        self.manager.checkDispatch(successful_response, slave)
        self.assertEqual(
            [], self.manager.builders_to_fail)

        failed_response = (False, 'uncool builder')
        self.manager.checkDispatch(failed_response, slave)
        self.assertEqual(
            [('foo', 'uncool builder')],
             self.manager.builders_to_fail)

    def testDispatchBuildSuccess(self):
        # A functional slave charged with some interactions.
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/')
        slave.ensurepresent('boing', 'bar', 'baz')
        slave.build('boing', 'bar', 'baz')

        # If the previous step (resuming) has failed nothing gets dispatched.
        result = self.manager.dispatchBuild(False, slave)
        self.assertFalse(result)
        self.assertEqual(0, len(self.manager._deferreds))

        # Operation with the default (funcional slave), not resets or
        # failures are triggered.
        result = self.manager.dispatchBuild(True, slave)
        self.assertTrue(result)
        self.assertEqual(2, len(self.manager._deferreds))
        self.assertEqual(
            [('ensurepresent', 'boing', 'bar', 'baz'),
             ('build', 'boing', 'bar', 'baz')],
            self.test_proxy.calls)
        self.assertEqual(
            [], self.manager.builders_to_reset)
        self.assertEqual(
            [], self.manager.builders_to_fail)

        # Consume the previous interations.
        ignore = self.manager.finishCycle()

        # Create a broken slave and insert interaction that will
        # cause the builder to be marked as fail.
        self.test_proxy = TestXMLRPCProxy('very broken slave')
        slave.ensurepresent('boing', 'bar', 'baz')
        slave.build('boing', 'bar', 'baz')

        result = self.manager.dispatchBuild(True, slave)
        self.assertEqual(
            [], self.manager.builders_to_reset)
        self.assertEqual(
            [('foo', 'very broken slave')],
            self.manager.builders_to_fail)

        return self.manager.finishCycle()


class TestBuilddDatabaseHelper(unittest.TestCase):
    """Tests for the buildd manager helper class."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        self.db_helper = BuilddManagerHelper()

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
        logout()

        return builder, job.id

    def assertJobIsClean(self, job_id):
        """Re-fetch the `IBuildQueue` record and check if it's clean."""
        login('foo.bar@canonical.com')
        job = getUtility(IBuildQueueSet).get(job_id)
        self.assertEqual('NEEDSBUILD', job.build.buildstate.name)
        self.assertEqual(None, job.builder)
        self.assertEqual(None, job.buildstart)
        self.assertEqual(None, job.logtail)
        logout()

    def testResetBuilder(self):
        """`BuilddManagerHelper.resetBuilder` clean any existing jobs.

        Although it keeps the builder active in pool.
        """
        builder, job_id = self._getBuilder()

        self.db_helper.resetBuilder(builder.name)

        self.assertTrue(builder.builderok)
        self.assertEqual(None, builder.currentjob)

        self.assertJobIsClean(job_id)

    def testFailBuilder(self):
        """`BuilddManagerHelper.failBuilder` excludes the builder from pool.

        It marks the build as failed (builderok=False) and clean any
        existing jobs.
        """
        builder, job_id = self._getBuilder()

        self.db_helper.failBuilder(builder.name, 'does not work!')

        self.assertFalse(builder.builderok)
        self.assertEqual(None, builder.currentjob)
        self.assertEqual('does not work!', builder.failnotes)

        self.assertJobIsClean(job_id)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
