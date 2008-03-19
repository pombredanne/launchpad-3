# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Twisted TestCase that doesn't interfere with existing signal handlers."""

__metaclass__ = type

__all__ = ['TwistedTestCase']

import signal
import thread
from unittest import TestCase, TestLoader, TestResult

from canonical.testing import TwistedLayer
from canonical.twistedsupport import MethodDeferrer

from twisted.trial.unittest import TestCase as TrialTestCase

from zope.interface import Interface


class TwistedTestCase(TrialTestCase):
    """Base test case to use for Twisted tests."""

    layer = TwistedLayer


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


class TestMethodDeferrer(TwistedTestCase):

    layer = TwistedLayer

    class IFoo(Interface):
        def foo(x):
            """Returns `x`."""

        def checkThreadID(self, main_thread_id):
            """Raise an error if the current thread is the main thread."""

    class Foo:

        def __init__(self):
            self.log = []

        def checkThreadID(self, main_thread_id):
            if thread.get_ident() == main_thread_id:
                raise AssertionError("Not running in thread")

        def foo(self, x):
            self.log.append(('foo', x))
            return x

        def bar(self, x):
            self.log.append(('bar', x))
            return x


    def setUp(self):
        self.original = self.Foo()
        self.wrapped = MethodDeferrer(self.original, self.IFoo)

    def checkLog(self, pass_through, expected_log):
        self.assertEqual(self.original.log, expected_log)
        return pass_through

    def test_callsUnderlying(self):
        # Calling a published method on an object wrapped with a
        # MethodDeferrer calls the underlying method.
        deferred = self.wrapped.foo(42)
        deferred.addCallback(self.assertEqual, 42)
        deferred.addCallback(self.checkLog, [('foo', 42)])
        return deferred

    def test_onlyAllowsPublishedMethods(self):
        # If you try to call a method that isn't advertised on an interface
        # provided to MethodDeferrer, you will get an AttributeError.
        self.assertRaises(AttributeError, lambda: self.wrapped.bar(42))

    def test_checkRunningInThread(self):
        # Of course, the wrapped methods actually do run in separate threads.
        # We have to check this in a somewhat unusual way. The wrapped method
        # itself does the checking, as it is the only one that knows what
        # thread its in.
        main_thread_id = thread.get_ident()
        self.wrapped.checkThreadID(main_thread_id)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)


