# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Twisted TestCase that doesn't interfere with existing signal handlers."""

__metaclass__ = type

__all__ = ['TwistedTestCase']

from unittest import TestSuite, TestCase, TestLoader, TestResult
import signal

from twisted.trial.unittest import TestCase as TrialTestCase


class TwistedTestCase(TrialTestCase):

    def run(self, result):
        # Record the signal handlers that Twisted will override (see
        # _handleSignals in twisted/internet/posixreactorbase.py).
        sigint = signal.getsignal(signal.SIGINT)
        sigterm = signal.getsignal(signal.SIGTERM)
        sigchld = signal.getsignal(signal.SIGCHLD)
        try:
            # TrialTestCase will start a reactor, which will install some signal
            # handlers.
            return TrialTestCase.run(self, result)
        finally:
            # Restore the original signal handlers
            signal.signal(signal.SIGINT, sigint)
            signal.signal(signal.SIGTERM, sigterm)
            signal.signal(signal.SIGCHLD, sigchld)


class TestCaseThatChangesSignals(TwistedTestCase):

    def clobber(self):
        # clobber SIGINT, SIGTERM and SIGCHLD, because other Twisted test cases
        # may have already run, so this sets a unique test handler that cannot
        # exist elsewhere.
        def dummy_handler(signal, frame):
            pass
        signal.signal(signal.SIGINT, dummy_handler)
        signal.signal(signal.SIGTERM, dummy_handler)
        signal.signal(signal.SIGCHLD, dummy_handler)

    # our "test" methods don't have test_ prefixes so that test runners don't
    # accidentally discover them.
    def a_test_that_passes(self):
        self.clobber()

    def a_test_that_fails(self):
        self.clobber()
        self.fail()

    def a_test_that_errors(self):
        self.clobber()
        1/0


class SignalRestorationTestCase(TestCase):

    def test_signals(self):
        # Grab the current SIGINT, SIGTERM, SIGCHLD handlers.
        sigint = signal.getsignal(signal.SIGINT)
        sigterm = signal.getsignal(signal.SIGTERM)
        sigchld = signal.getsignal(signal.SIGCHLD)

        # Construct the test cases.
        passing_test_case = TestCaseThatChangesSignals('a_test_that_passes')
        fails_test_case = TestCaseThatChangesSignals('a_test_that_fails')
        error_test_case = TestCaseThatChangesSignals('a_test_that_errors')

        result = TestResult()
        # Constructing the test case shouldn't change the signal handlers
        self.assertSignalsUnchanged(sigint, sigterm, sigchld)

        for testcase in [passing_test_case, fails_test_case, error_test_case]:
            # Run the test case
            testcase(result)

            # The signals should be restored, even though the test case clobbered
            # them.
            self.assertSignalsUnchanged(sigint, sigterm, sigchld)

    def assertSignalsUnchanged(self, sigint, sigterm, sigchld):
        self.assertEqual(sigint, signal.getsignal(signal.SIGINT))
        self.assertEqual(sigterm, signal.getsignal(signal.SIGTERM))
        self.assertEqual(sigchld, signal.getsignal(signal.SIGCHLD))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)


