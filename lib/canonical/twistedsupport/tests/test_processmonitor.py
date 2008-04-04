# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0702

"""Tests for ProcessMonitorProtocol and ProcessMonitorProtocolWithTimeout."""

__metaclass__ = type


import StringIO
import sys
import unittest

from twisted.internet import defer, error, task
from twisted.python import failure
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.testing import TwistedLayer
from canonical.twistedsupport.processmonitor import (
    ProcessMonitorProtocol, ProcessMonitorProtocolWithTimeout,
    ProcessProtocolWithTwoStageKill)


def makeFailure(exception_factory, *args, **kwargs):
    """Make a Failure object from the given exception factory.

    Any other arguments are passed straight on to the factory.
    """
    try:
        raise exception_factory(*args, **kwargs)
    except:
        return failure.Failure()


class ProcessTestsMixin:
    """Helpers to allow direct testing of ProcessProtocol subclasses.
    """

    class StubTransport:
        """Stub process transport that implements the minimum we need.

        We're manually manipulating the protocol, so we don't need a real
        transport and associated process.

        A little complexity is required to only call
        self.protocol.processEnded() once.
        """

        only_sigkill_kills = False

        def __init__(self, protocol, clock):
            self.protocol = protocol
            self.clock = clock
            self.calls = []
            self.exited = False

        def loseConnection(self):
            self.calls.append('loseConnection')

        def signalProcess(self, signal_name):
            self.calls.append(('signalProcess', signal_name))
            if self.exited:
                raise error.ProcessExitedAlready
            if not self.only_sigkill_kills or signal_name == 'KILL':
                self.exited = True
                reason = failure.Failure(error.ProcessTerminated())
                self.protocol.processEnded(reason)

    def makeProtocol(self):
        """Construct an `ProcessProtocol` instance to be tested.

        Override this in subclasses."""
        raise NotImplementedError

    def simulateProcessExit(self, clean=True):
        """Pretend the child process we're monitoring has exited."""
        self.protocol.transport.exited = True
        if clean:
            exc = error.ProcessDone(None)
        else:
            exc = error.ProcessTerminated(exitCode=1)
        self.protocol.processEnded(failure.Failure(exc))

    def setUp(self):
        self.termination_deferred = defer.Deferred()
        self.clock = task.Clock()
        self.protocol = self.makeProtocol()
        self.protocol.transport = self.StubTransport(
            self.protocol, self.clock)
        self.protocol.connectionMade()

class TestProcessProtocolWithTwoStageKill(
    ProcessTestsMixin, TrialTestCase):

    """Tests for `ProcessProtocolWithTwoStageKill`."""

    layer = TwistedLayer

    def makeProtocol(self):
        """See `ProcessMonitorProtocolTestsMixin.makeProtocol`."""
        return ProcessProtocolWithTwoStageKill(self.clock)

    def test_interrupt(self):
        # When we call terminateProcess, we send SIGINT to the child
        # process.
        self.protocol.terminateProcess()
        self.assertEqual(
            [('signalProcess', 'INT')],
            self.protocol.transport.calls)

    def test_interruptThenKill(self):
        # If SIGINT doesn't kill the process, we send SIGKILL after a delay.
        self.protocol.transport.only_sigkill_kills = True

        self.protocol.terminateProcess()

        # When the error happens, we SIGINT the process.
        self.assertEqual(
            [('signalProcess', 'INT')],
            self.protocol.transport.calls)

        # After the expected time elapsed, we send SIGKILL.
        self.clock.advance(self.protocol.default_wait_before_kill + 1)
        self.assertEqual(
            [('signalProcess', 'INT'), ('signalProcess', 'KILL')],
            self.protocol.transport.calls)

    def test_processExitClearsTimer(self):
        # If SIGINT doesn't kill the process, we schedule a SIGKILL after a
        # delay.  If the process exits before this delay elapses, we cancel
        # the SIGKILL.
        self.protocol.transport.only_sigkill_kills = True
        self.protocol.terminateProcess()
        saved_delayed_call = self.protocol._sigkill_delayed_call
        self.failUnless(self.protocol._sigkill_delayed_call.active())
        self.simulateProcessExit(clean=False)
        self.failUnless(self.protocol._sigkill_delayed_call is None)
        self.failIf(saved_delayed_call.active())


class TestProcessMonitorProtocol(
    ProcessTestsMixin, TrialTestCase):
    """Tests for `ProcessMonitorProtocol`."""

    layer = TwistedLayer

    def makeProtocol(self):
        """See `ProcessMonitorProtocolTestsMixin.makeProtocol`."""
        return ProcessMonitorProtocol(
            self.termination_deferred, self.clock)

    def test_processTermination(self):
        # The protocol fires a Deferred when the child process terminates.
        self.simulateProcessExit()
        # The only way this test can realistically fail is by hanging.
        return self.termination_deferred

    def test_terminatesWithError(self):
        # When the child process terminates with a non-zero exit code, pass on
        # the error.
        self.simulateProcessExit(clean=False)
        return self.assertFailure(
            self.termination_deferred, error.ProcessTerminated)

    def test_unexpectedError(self):
        # unexpectedError() sends SIGINT to the child process but the
        # termination deferred is fired with originally passed-in failure.
        self.protocol.unexpectedError(
            makeFailure(RuntimeError, 'error message'))
        self.assertEqual(
            [('signalProcess', 'INT')],
            self.protocol.transport.calls)
        return self.assertFailure(
            self.termination_deferred, RuntimeError)

    def test_runNotification(self):
        # The first call to runNotification just runs the passed function.
        calls = []
        self.protocol.runNotification(calls.append, 'called')
        self.assertEqual(calls, ['called'])

    def test_runNotificationFailure(self):
        # If a notification function fails, the child process is killed and
        # the manner of failure reported.
        def fail():
            raise RuntimeError
        self.protocol.runNotification(fail)
        self.assertEqual(
            [('signalProcess', 'INT')],
            self.protocol.transport.calls)
        return self.assertFailure(
            self.termination_deferred, RuntimeError)

    def test_runNotificationSerialization(self):
        # If two calls are made to runNotification, the second function passed
        # is not called until any deferred returned by the first one fires.
        deferred = defer.Deferred()
        calls = []
        self.protocol.runNotification(lambda : deferred)
        self.protocol.runNotification(calls.append, 'called')
        self.assertEqual(calls, [])
        deferred.callback(None)
        self.assertEqual(calls, ['called'])

    def test_failingNotificationCancelsPendingNotifications(self):
        # A failed notification prevents any further notifications from being
        # run.  Specifically, if a notification returns a deferred which
        # subsequently errbacks, any notifications which have been requested
        # in the mean time are not run.
        deferred = defer.Deferred()
        calls = []
        self.protocol.runNotification(lambda : deferred)
        self.protocol.runNotification(calls.append, 'called')
        self.assertEqual(calls, [])
        deferred.errback(makeFailure(RuntimeError))
        self.assertEqual(calls, [])
        return self.assertFailure(
            self.termination_deferred, RuntimeError)

    def test_waitForPendingNotification(self):
        # Don't fire the termination deferred until all notifications are
        # complete, even if the process has died.
        deferred = defer.Deferred()
        self.protocol.runNotification(lambda : deferred)
        self.simulateProcessExit()
        notificaion_pending = True
        self.termination_deferred.addCallback(
            lambda ignored: self.failIf(notificaion_pending))
        notificaion_pending = False
        deferred.callback(None)
        return self.termination_deferred

    def test_pendingNotificationFails(self):
        # If the process exits cleanly while a notification is pending and the
        # notification subsequently fails, the notification's failure is
        # passed on to the termination deferred.
        deferred = defer.Deferred()
        self.protocol.runNotification(lambda : deferred)
        self.simulateProcessExit()
        deferred.errback(makeFailure(RuntimeError))
        return self.assertFailure(
            self.termination_deferred, RuntimeError)

    def test_uncleanExitAndPendingNotificationFails(self):
        # If the process exits with a non-zero exit code while a
        # notification is pending and the notification subsequently
        # fails, the ProcessTerminated is still passed on to the
        # termination deferred.
        # XXX MichaelHudson 2008-04-02: The notification failure will be
        # log.err()ed, which spews to stderr, forcing hacks.  This can be
        # tested nicely when we upgrade Twisted.
        stringio = StringIO.StringIO()
        saved_stderr = sys.stderr
        def set_stderr(result, stream):
            sys.stderr = stream
            return result

        def test_body(ignored):
            deferred = defer.Deferred()
            self.protocol.runNotification(lambda : deferred)
            self.simulateProcessExit(clean=False)
            deferred.errback(makeFailure(RuntimeError))
            return self.assertFailure(
                self.termination_deferred, error.ProcessTerminated)

        return defer.succeed(None).addCallback(
            set_stderr, stringio).addCallback(
            test_body).addBoth(
            set_stderr, saved_stderr)

    def test_unexpectedErrorAndNotificationFailure(self):
        # If unexpectedError is called while a notification is pending and the
        # notification subsequently fails, the first failure "wins" and is
        # passed on to the termination deferred.
        # XXX MichaelHudson 2008-04-02: The notification failure will be
        # log.err()ed, which spews to stderr, forcing hacks.  This can be
        # tested nicely when we upgrade Twisted.
        stringio = StringIO.StringIO()
        saved_stderr = sys.stderr
        def set_stderr(result, stream):
            sys.stderr = stream
            return result

        def test_body(ignored):
            deferred = defer.Deferred()
            self.protocol.runNotification(lambda : deferred)
            self.protocol.unexpectedError(makeFailure(TypeError))
            deferred.errback(makeFailure(RuntimeError))
            return self.assertFailure(
                self.termination_deferred, TypeError)

        return defer.succeed(None).addCallback(
            set_stderr, stringio).addCallback(
            test_body).addBoth(
            set_stderr, saved_stderr)

class TestProcessMonitorProtocolWithTimeout(
    ProcessTestsMixin, TrialTestCase):
    """Tests for `ProcessMonitorProtocolWithTimeout`."""

    layer = TwistedLayer

    timeout = 5

    def makeProtocol(self):
        """See `ProcessMonitorProtocolTestsMixin.makeProtocol`."""
        return ProcessMonitorProtocolWithTimeout(
            self.termination_deferred, self.timeout, self.clock)

    def test_timeoutWithoutProgress(self):
        # If we don't receive any messages after the configured timeout
        # period, then we kill the child process.
        self.clock.advance(self.timeout + 1)
        return self.assertFailure(
            self.termination_deferred, error.TimeoutError)

    def test_resetTimeout(self):
        # Calling resetTimeout resets the timeout.
        self.clock.advance(self.timeout - 1)
        self.protocol.resetTimeout()
        self.clock.advance(2)
        self.simulateProcessExit()
        return self.termination_deferred

    def test_processExitingResetsTimeout(self):
        # When the process exits, the timeout is reset.
        deferred = defer.Deferred()
        self.protocol.runNotification(lambda : deferred)
        self.clock.advance(self.timeout - 1)
        self.simulateProcessExit()
        self.clock.advance(2)
        deferred.callback(None)
        return self.termination_deferred

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
