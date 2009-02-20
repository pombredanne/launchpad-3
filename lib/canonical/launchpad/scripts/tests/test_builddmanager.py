# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the renovated slave scanner aka BuilddManager."""

import unittest

from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase

from zope.component import getUtility
from zope.security.management import endInteraction, newInteraction

from canonical.launchpad.interfaces.builder import IBuilderSet
from canonical.launchpad.scripts.builddmanager import (
    BuilddManager, BuilddProxy, RecordingSlave)
from canonical.launchpad.scripts.logger import BufferLogger
from canonical.testing.layers import (
    DatabaseFunctionalLayer, TwistedLayer)


class TestRecordinSlaves(TrialTestCase):

    layer = TwistedLayer

    def setUp(self):
        TrialTestCase.setUp(self)
        self.slave = RecordingSlave('foo', 'http://foo:8221/rpc')

    def testInstantiation(self):
        self.assertEqual('<foo:http://foo:8221/rpc>', repr(self.slave))

    def testEnsurePresent(self):
        self.assertEqual(
            (True, 'Download'),
            self.slave.ensurepresent('boing', 'bar', 'baz'))
        self.assertEqual(
            [('ensurepresent', ('boing', 'bar', 'baz'))],
            self.slave.calls)

    def testBuild(self):
        self.assertEqual(
            ('BuilderStatus.BUILDING', 'boing'),
            self.slave.build('boing', 'bar', 'baz'))
        self.assertEqual(
            [('build', ('boing', 'bar', 'baz'))],
            self.slave.calls)

    def testResume(self):
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


class TestBuilddProxy:

    def __init__(self):
        self.builders_reset = []
        self.dispatch_failures = []

    def scanAllBuilders(self):
        fake_slaves = (
            RecordingSlave(name, 'http://%s:8221/rpc/')
            for name in ['foo', 'bar'])
        return fake_slaves

    def resetBuilder(self, name):
        self.builders_reset.append(name)

    def dispatchFail(self, error, name):
        self.dispatch_failures.append((name, error))


class TestWebProxy:

    def __init__(self, works=True):
        self.works = works
        self.calls = []

    def callRemote(self, *args):
        self.calls.append(args)
        return defer.maybeDeferred(lambda: (self.works, None))


class TestBuilddManager(TrialTestCase):

    layer = TwistedLayer

    def setUp(self):
        TrialTestCase.setUp(self)
        self.manager = BuilddManager()
        self.manager.buildd_proxy = TestBuilddProxy()
        self.stopped = False
        self.test_proxy = TestWebProxy()

    def testStopWhenDone(self):
        self.assertEqual(0, self.manager.running_jobs)

        def game_over():
            self.stopped = True
        self.manager.gameOver = game_over

        self.manager.running_jobs = 2
        self.manager.stopWhenDone('ignore-me')
        self.assertEqual(1, self.manager.running_jobs)
        self.assertFalse(self.stopped)

        self.manager.stopWhenDone('ignore-me')
        self.assertEqual(0, self.manager.running_jobs)
        self.assertTrue(self.stopped, 'Boing')

    def testScannedSlaves(self):
        slaves = self.manager.scan()
        self.assertEqual(['foo', 'bar'], [slave.name for slave in slaves])

    def testCheckResume(self):
        successful_response = ('', '', 0)
        result = self.manager.checkResume(
            successful_response, 'foo')
        self.assertTrue(result)
        self.assertEqual(
            [], self.manager.buildd_proxy.builders_reset)

        failed_response = ('', '', 1)
        result = self.manager.checkResume(
            failed_response, 'foo')
        self.assertFalse(result)
        self.assertEqual(
            ['foo'], self.manager.buildd_proxy.builders_reset)

    def testCheckDispatch(self):
        successful_response = (True, 'cool builder')
        self.manager.checkDispatch(successful_response, 'foo')
        self.assertEqual(
            [], self.manager.buildd_proxy.dispatch_failures)

        failed_response = (False, 'uncool builder')
        self.manager.checkDispatch(failed_response, 'foo')
        self.assertEqual(
            [('foo', 'uncool builder')],
             self.manager.buildd_proxy.dispatch_failures)

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
            [], self.manager.buildd_proxy.builders_reset)
        self.assertEqual(
            [], self.manager.buildd_proxy.dispatch_failures)

        self.test_proxy = TestWebProxy(False)
        result = self.manager.dispatchBuild(True, slave)
        # Reseting only once it enough.
        self.assertEqual(
            [], self.manager.buildd_proxy.builders_reset)
        self.assertEqual(
            [('foo', None), ('foo', None)],
            self.manager.buildd_proxy.dispatch_failures)


class TestBuilddDatabaseProxy(unittest.TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        self.db_proxy = BuilddProxy()

    def testResetBuilder(self):
        newInteraction()
        bob = getUtility(IBuilderSet)['bob']

        job = bob.currentjob
        self.assertEqual(
            u'i386 build of mozilla-firefox 0.9 in ubuntu hoary RELEASE',
            job.build.title)
        endInteraction()

        self.db_proxy.resetBuilder('bob')

        self.assertEqual(None, bob.currentjob)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
