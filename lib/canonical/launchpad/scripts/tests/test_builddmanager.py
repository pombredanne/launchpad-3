# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for ..."""

import unittest

from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.launchpad.scripts.builddmanager import (
    BuilddManager, RecordingSlave)
from canonical.launchpad.scripts.logger import BufferLogger
from canonical.testing.layers import TwistedLayer


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

    def scanAllBuilders(self):
        fake_slaves = (
            RecordingSlave(name, 'http://%s:8221/rpc/')
            for name in ['foo', 'bar'])
        return fake_slaves

    def resetBuilder(self, name):
        pass

    def dispatchFail(self, error, name):
        pass


class TestBuilddManager(TrialTestCase):

    layer = TwistedLayer

    def setUp(self):
        TrialTestCase.setUp(self)

        self.manager = BuilddManager()
        self.manager.buildd_proxy = TestBuilddProxy()

    def tearDown(self):
        TrialTestCase.tearDown(self)

    def testScannedSlaves(self):
        def check_slaves(slaves):
            self.assertEqual(
                ['foo', 'bar'], [slave.name for slave in slaves])
        d = defer.maybeDeferred(self.manager.scan)
        d.addCallback(check_slaves)
        return d


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
