# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the base TestCase classes."""

__metaclass__ = type

import unittest
from lp.testing import TestCase


class LoggingResult(unittest.TestResult):
    """TestResult that logs its event to a list."""

    def __init__(self, log):
        self._events = log
        super(LoggingResult, self).__init__()

    def startTest(self, test):
        self._events.append(('startTest', test))
        super(LoggingResult, self).startTest(test)

    def stopTest(self, test):
        self._events.append(('stopTest', test))
        super(LoggingResult, self).stopTest(test)

    def addFailure(self, test, error):
        self._events.append(('addFailure', test, error))
        super(LoggingResult, self).addFailure(test, error)

    def addError(self, test, error):
        self._events.append(('addError', test, error))
        super(LoggingResult, self).addError(test, error)

    def addSuccess(self, test):
        self._events.append(('addSuccess', test))
        super(LoggingResult, self).addSuccess(test)


class TestAddCleanup(unittest.TestCase):
    """Tests for TestCase.addCleanup."""

    class LoggingTest(TestCase):
        """A test that logs calls to setUp, runTest and tearDown."""

        def setUp(self):
            self._calls = ['setUp']

        def brokenSetUp(self):
            # A tearDown that deliberately fails.
            self._calls = ['brokenSetUp']
            raise RuntimeError('Deliberate Failure')

        def runTest(self):
            self._calls.append('runTest')

        def tearDown(self):
            self._calls.append('tearDown')

    def setUp(self):
        self._result_calls = []
        self.test = TestAddCleanup.LoggingTest('runTest')
        self.logging_result = LoggingResult(self._result_calls)

    def assertErrorLogEqual(self, messages):
        self.assertEqual(messages, [call[0] for call in self._result_calls])

    def assertTestLogEqual(self, messages):
        """Assert that the call log equals `messages`."""
        self.assertEqual(messages, self.test._calls)

    def logAppender(self, message):
        """Return a cleanup that appends `message` to the tests log.

        Cleanups are callables that are added to a test by addCleanup. To
        verify that our cleanups run in the right order, we add strings to a
        list that acts as a log. This method returns a cleanup that will add
        the given message to that log when run.
        """
        self.test._calls.append(message)

    def test_fixture(self):
        # A normal run of self.test logs 'setUp', 'runTest' and 'tearDown'.
        # This test doesn't test addCleanup itself, it just sanity checks the
        # fixture.
        self.test.run(self.logging_result)
        self.assertTestLogEqual(['setUp', 'runTest', 'tearDown'])

    def test_cleanup_run_before_tearDown(self):
        # Cleanup functions added with 'addCleanup' are called before tearDown
        # runs.
        self.test.addCleanup(self.logAppender, 'cleanup')
        self.test.run(self.logging_result)
        self.assertTestLogEqual(['setUp', 'runTest', 'cleanup', 'tearDown'])

    def test_add_cleanup_called_if_setUp_fails(self):
        # Cleanup functions added with 'addCleanup' are called even if setUp
        # fails. Note that tearDown has a different behavior: it is only
        # called when setUp succeeds.
        self.test.setUp = self.test.brokenSetUp
        self.test.addCleanup(self.logAppender, 'cleanup')
        self.test.run(self.logging_result)
        self.assertTestLogEqual(['brokenSetUp', 'cleanup'])

    def test_addCleanup_called_in_reverse_order(self):
        # Cleanup functions added with 'addCleanup' are called in reverse
        # order.
        #
        # One of the main uses of addCleanup is to dynamically create
        # resources that need some sort of explicit tearDown. Often one
        # resource will be created in terms of another, e.g.,
        #     self.first = self.makeFirst()
        #     self.second = self.makeSecond(self.first)
        #
        # When this happens, we generally want to clean up the second resource
        # before the first one, since the second depends on the first.
        self.test.addCleanup(self.logAppender, 'first')
        self.test.addCleanup(self.logAppender, 'second')
        self.test.run(self.logging_result)
        self.assertTestLogEqual(
            ['setUp', 'runTest', 'second', 'first', 'tearDown'])

    def test_tearDown_runs_after_cleanup_failure(self):
        # tearDown runs even if a cleanup function fails.
        self.test.addCleanup(lambda: 1/0)
        self.test.run(self.logging_result)
        self.assertTestLogEqual(['setUp', 'runTest', 'tearDown'])

    def test_cleanups_continue_running_after_error(self):
        # All cleanups are always run, even if one or two of them fail.
        self.test.addCleanup(self.logAppender, 'first')
        self.test.addCleanup(lambda: 1/0)
        self.test.addCleanup(self.logAppender, 'second')
        self.test.run(self.logging_result)
        self.assertTestLogEqual(
            ['setUp', 'runTest', 'second', 'first', 'tearDown'])

    def test_error_in_cleanups_are_captured(self):
        # If a cleanup raises an error, we want to record it and fail the
        # test, even though we go on to run other cleanups.
        self.test.addCleanup(lambda: 1/0)
        self.test.run(self.logging_result)
        self.assertErrorLogEqual(['startTest', 'addError', 'stopTest'])

    def test_keyboard_interrupt_not_caught(self):
        # If a cleanup raises KeyboardInterrupt, it gets reraised.
        def raiseKeyboardInterrupt():
            raise KeyboardInterrupt()
        self.test.addCleanup(raiseKeyboardInterrupt)
        self.assertRaises(
            KeyboardInterrupt, self.test.run, self.logging_result)

    def test_multipleErrorsReported(self):
        # Errors from all failing cleanups are reported.
        self.test.addCleanup(lambda: 1/0)
        self.test.addCleanup(lambda: 1/0)
        self.test.run(self.logging_result)
        self.assertErrorLogEqual(
            ['startTest', 'addError', 'addError', 'stopTest'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
