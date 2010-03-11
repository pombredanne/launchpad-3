# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `lp.testing.ZopeTestInSubProcess`."""

__metaclass__ = type

import functools
import os
import unittest

from lp.testing import ZopeTestInSubProcess


def record_pid(method):
    """Decorator that records the pid at method invocation."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        setattr(self, 'pid_in_%s' % method.__name__, os.getpid())
        return method(self, *args, **kwargs)
    return wrapper


class TestZopeTestInSubProcessLayer:

    @record_pid
    def __init__(self, test):
        self.test = test
        # These are needed to satisfy the requirements of the
        # byzantine Zope layer machinery.
        self.__name__ = self.__class__.__name__
        self.__bases__ = self.__class__.__bases__

    @record_pid
    def setUp(self):
        # Runs in the parent process.
        assert self.pid_in___init__ == self.pid_in_setUp, (
            "layer.setUp() not called in parent process.")

    @record_pid
    def tearDown(self):
        # Runs in the parent process.
        assert self.pid_in___init__ == self.pid_in_tearDown, (
            "layer.tearDown() not called in parent process.")

    @record_pid
    def testSetUp(self):
        # Runs in the child process.
        assert self.pid_in___init__ != self.pid_in_testSetUp, (
            "layer.testSetUp() called in parent process.")

    @record_pid
    def testTearDown(self):
        # Runs in the child process.
        assert self.pid_in_testSetUp == self.pid_in_testTearDown, (
            "layer.testTearDown() not called in same process as testSetUp().")


class TestZopeTestInSubProcess(ZopeTestInSubProcess, unittest.TestCase):

    @record_pid
    def __init__(self, method_name='runTest'):
        # Runs in the parent process.
        super(TestZopeTestInSubProcess, self).__init__(method_name)
        self.layer = TestZopeTestInSubProcessLayer(self)

    @record_pid
    def setUp(self):
        # Runs in the child process.
        super(TestZopeTestInSubProcess, self).setUp()
        self.failUnlessEqual(
            self.layer.pid_in_testSetUp, self.pid_in_setUp,
            "test.setUp() not called in same process as layer.testSetUp().")

    @record_pid
    def test(self):
        # Runs in the child process.
        self.failUnlessEqual(
            self.pid_in_setUp, self.pid_in_test,
            "test method not run in same process as setUp().")

    @record_pid
    def tearDown(self):
        # Runs in the child process.
        super(TestZopeTestInSubProcess, self).tearDown()
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
