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

        self.test_proxy = TestXMLRPCProxy()
        self.stopped = False

    def testStopWhenDone(self):
        """Check if the chain is terminated and database updates are done.

        'BuilddManager.stopWhenDone' verifies the number of 'running_jobs'
        and once they cease it performs all needed database updates (builder
        reset or failure) synchronously and call `BuilddManager.gameOver`.
        """
        # 'running_jobs' is ZERO on a just intantiated BuilddManager.
        self.assertEqual(0, self.manager.running_jobs)

        # We will instrument the `gameOver` method and schedule one reset
        # and one failure update.
        def game_over():
            self.stopped = True
        self.manager.gameOver = game_over
        self.manager.builders_to_reset = ['foo']
        self.manager.builders_to_fail = [('bar', 'boingo')]

        # When `stopWhenDone` is called, and it is called after all build
        # slave interation, `running_job` is decremented. If there are still
        # jobs running nothing is done.
        self.manager.running_jobs = 2
        self.manager.stopWhenDone('ignore-me')
        self.assertEqual(1, self.manager.running_jobs)
        self.assertFalse(self.stopped)
        self.assertEqual(
            [], self.manager.helper.builders_reset)
        self.assertEqual(
            [], self.manager.helper.builders_failed)

        # When there are no more running jobs the reset and failure database
        # updates requests are performed and the `gameOver` method is called.
        self.manager.stopWhenDone('ignore-me')
        self.assertEqual(0, self.manager.running_jobs)
        self.assertTrue(self.stopped)
        self.assertEqual(
            ['foo'], self.manager.helper.builders_reset)
        self.assertEqual(
            [('bar', 'boingo')], self.manager.helper.builders_failed)

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
        successful_response = ('', '', 0)
        result = self.manager.checkResume(
            successful_response, 'foo')
        self.assertTrue(result)
        self.assertEqual(
            [], self.manager.builders_to_reset)

        failed_response = ('', '', 1)
        result = self.manager.checkResume(
            failed_response, 'foo')
        self.assertFalse(result)
        self.assertEqual(
            ['foo'], self.manager.builders_to_reset)

    def testCheckDispatch(self):
        """`BuilddManager.checkDispatch` is chained after dispatch requests.

        If the dispatch request fails it schedules the build for database
        failure update.
        """
        successful_response = (True, 'cool builder')
        self.manager.checkDispatch(successful_response, 'foo')
        self.assertEqual(
            [], self.manager.builders_to_fail)

        failed_response = (False, 'uncool builder')
        self.manager.checkDispatch(failed_response, 'foo')
        self.assertEqual(
            [('foo', 'uncool builder')],
             self.manager.builders_to_fail)

    def testDispatchBuild(self):
        slave = RecordingSlave('foo', 'http://foo.buildd:8221/')
        slave.ensurepresent('boing', 'bar', 'baz')
        slave.build('boing', 'bar', 'baz')

        result = self.manager.dispatchBuild(False, slave)
        self.assertFalse(result)
        self.assertEqual(0, self.manager.running_jobs)

        def getTestProxy(slave):
            return self.test_proxy

        self.manager._getProxyForSlave = getTestProxy

        result = self.manager.dispatchBuild(True, slave)
        self.assertTrue(result)
        self.assertEqual(2, self.manager.running_jobs)
        self.assertEqual(
            [('ensurepresent', 'boing', 'bar', 'baz'),
             ('build', 'boing', 'bar', 'baz')],
            self.test_proxy.calls)
        self.assertEqual(
            [], self.manager.builders_to_reset)
        self.assertEqual(
            [], self.manager.builders_to_fail)

        self.test_proxy = TestXMLRPCProxy('very broken slave')
        result = self.manager.dispatchBuild(True, slave)
        # Reseting only once is enough.
        self.assertEqual(
            [], self.manager.builders_to_reset)
        self.assertEqual(
            [('foo', 'very broken slave'), ('foo', 'very broken slave')],
            self.manager.builders_to_fail)


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
