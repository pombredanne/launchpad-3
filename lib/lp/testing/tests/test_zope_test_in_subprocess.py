# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `lp.testing.ZopeTestInSubProcess`."""

__metaclass__ = type

import os
import unittest

from lp.testing import ZopeTestInSubProcess


class PidRecordingLayer:

    def __init__(self, test):
        self.test = test
        self.pid_in_init = os.getpid()
        # These are needed to satisfy the requirements of the
        # byzantine Zope layer machinery.
        self.__name__ = self.__class__.__name__
        self.__bases__ = self.__class__.__bases__

    def setUp(self):
        # Runs in the parent process.
        self.pid_in_setUp = os.getpid()
        assert self.pid_in_init == self.pid_in_setUp, (
            "layer.setUp() not called in parent process.")

    def tearDown(self):
        # Runs in the parent process.
        self.pid_in_tearDown = os.getpid()
        assert self.pid_in_init == self.pid_in_tearDown, (
            "layer.tearDown() not called in parent process.")

    def testSetUp(self):
        # Runs in the child process.
        self.pid_in_testSetUp = os.getpid()
        assert self.pid_in_init != self.pid_in_testSetUp, (
            "layer.testSetUp() called in parent process.")

    def testTearDown(self):
        # Runs in the child process.
        self.pid_in_testTearDown = os.getpid()
        assert self.pid_in_testSetUp == self.pid_in_testTearDown, (
            "layer.testTearDown() not called in same process as testSetUp().")


class TestZopeTestInSubProcess(ZopeTestInSubProcess, unittest.TestCase):

    def __init__(self, method_name='runTest'):
        # Runs in the parent process.
        super(TestZopeTestInSubProcess, self).__init__(method_name)
        self.pid_in_init = os.getpid()
        self.layer = PidRecordingLayer(self)

    def setUp(self):
        # Runs in the child process.
        super(TestZopeTestInSubProcess, self).setUp()
        self.pid_in_setUp = os.getpid()
        self.failUnlessEqual(
            self.layer.pid_in_testSetUp, self.pid_in_setUp,
            "test.setUp() not called in same process as layer.testSetUp().")

    def test(self):
        # Runs in the child process.
        self.pid_in_test = os.getpid()
        self.failUnlessEqual(
            self.pid_in_setUp, self.pid_in_test,
            "test method not run in same process as setUp().")

    def tearDown(self):
        # Runs in the child process.
        super(TestZopeTestInSubProcess, self).tearDown()
        self.pid_in_tearDown = os.getpid()
        self.failUnlessEqual(
            self.pid_in_setUp, self.pid_in_tearDown,
            "tearDown() not run in same process as setUp().")


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(
        loader.loadTestsFromTestCase(
            TestZopeTestInSubProcess))
    return suite
