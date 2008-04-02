# Copyright 2008 Canonical Ltd.  All rights reserved.

"""XXX."""

__metaclass__ = type
__all__ = ['ProcessMonitorProtocol', 'ProcessMonitorProtocolWithTimeout']


from twisted.internet import defer, error, reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.protocols.policies import TimeoutMixin
from twisted.python import failure


class ProcessMonitorProtocol(ProcessProtocol):
    """Support for running a process and reporting on its progress.

    The idea is this: you want to run a subprocess.  Occasionally, you want to
    report on what it is doing to some other entity: maybe it's a multistep
    task and you want to update a row in a database to reflect which step it
    is currently on.  This class provides a runNotification() method that
    helps with this.  It takes a callable that performs this notfication,
    maybe returning a deferred.

    Design decisions:

     - The notifications are serialized.  If you call runNotification() with
       two callables, the deferred returned by the first must fire before the
       second callable will be called.

     - A notification failing is treated as a fatal error: the subprocess is
       killed and the 'termination deferred' fired.

     - If a notification fails and the subprocess exits with a non-zero exit
       code, there are two failures that could be reported.  Currently, the
       notification failure 'wins'.

     - The deferred passed into the constructor will not be fired until the
       subprocess has exited and all pending notifications have completed.
       Note that Twisted does not tell us the process has exited until all of
       it's output has been processed.

    :ivar _deferred: The deferred that will be fired when the subprocess
        exits.
    :ivar _clock: A provider of Twisted's IReactorTime, to allow testing that
        does not depend on an external clock.  If a clock is not explicitly
        supplied the reactor is used.
    :ivar _notification_lock: A DeferredLock, used to serialize the
        notifications.
    :ivar _sigkill_delayed_call: When we kill a process, we send SIGINT, wait
        a while and then send SIGKILL if required.  We stash the DelayedCall
        here so that it can be cancelled if the SIGINT causes the process to
        exit.
    :ivar _termination_failure: When we kill the subprocess in response to
        some unexpected error, we report the reason we killed it to
        self._deferred, not that it exited because we killed it.
    """

    def __init__(self, deferred, clock=None):
        """Construct an instance of the protocol, for listening to a worker.

        :param deferred: A Deferred that will be fired when the subprocess has
            finished (either successfully or unsuccesfully).
        :param clock: A provider of Twisted's IReactorTime.  This parameter
            exists to allow testing that does not depend on an external clock.
            If a clock is not passed in explicitly the reactor is used.
        """
        self._deferred = deferred
        if clock is None:
            clock = reactor
        self._clock = clock
        self._notification_lock = defer.DeferredLock()
        self._sigkill_delayed_call = None
        self._termination_failure = None

    def runNotification(self, func, *args):
        """Run a given function in series with other notifications.

        "func(*args)" will be called when any other running or queued
        notifications have completed.  func() may return a Deferred.  Note
        that if func() errors out, this is considered a fatal error and the
        subprocess will be killed.
        """
        def wrapper():
            if self._termination_failure is not None:
                return
            else:
                return defer.maybeDeferred(func, *args).addErrback(
                    self.unexpectedError)
        return self._notification_lock.run(wrapper)

    def unexpectedError(self, failure):
        """Something's gone wrong: kill the subprocess and report failure.

        This method sends SIGINT to the subprocess and schedules a SIGKILL for
        five seconds time in case the SIGINT doesn't kill the process.
        """
        if self._termination_failure is None:
            self._termination_failure = failure
        try:
            self.transport.signalProcess('INT')
        except error.ProcessExitedAlready:
            # The process has already died. Fine.
            pass
        else:
            self._sigkill_delayed_call = self._clock.callLater(
                5, self._sigkill)

    def _sigkill(self):
        """Send SIGKILL to the child process.

        We rely on this killing the process, i.e. we assume that
        processEnded() will be called soon after this.
        """
        self._sigkill_delayed_call = None
        try:
            self.transport.signalProcess('KILL')
        except error.ProcessExitedAlready:
            # The process has already died. Fine.
            pass

    def processEnded(self, reason):
        """See `ProcessProtocol.processEnded`.

        Fires the termination deferred with reason or, if the process died
        because we killed it, why we killed it.
        """
        ProcessProtocol.processEnded(self, reason)
        if self._sigkill_delayed_call is not None:
            self._sigkill_delayed_call.cancel()
            self._sigkill_delayed_call = None

        def fire_final_deferred():
            if self._termination_failure is not None:
                self._deferred.errback(self._termination_failure)
            elif reason.check(error.ProcessDone):
                self._deferred.callback(None)
            else:
                self._deferred.errback(reason)

        self._notification_lock.run(fire_final_deferred)


class ProcessMonitorProtocolWithTimeout(ProcessMonitorProtocol, TimeoutMixin):
    """Support for killing a monitored process after a period of inactivity.

    Note that this class does not define activity in any way: your subclass
    should call resetTimeout() when it deems the subprocess has made progress.

    :ivar _timeout: The subprocess will be killed after this many seconds of
        inactivity.
    """

    def __init__(self, deferred, timeout, clock=None):
        """Construct an instance of the protocol, for listening to a worker.

        :param deferred: Passed to `ProcessMonitorProtocol.__init__`.
        :param timeout: The subprocess will be killed after this many seconds of
            inactivity.
        :param clock: Passed to `ProcessMonitorProtocol.__init__`.
        """
        ProcessMonitorProtocol.__init__(self, deferred, clock)
        self._timeout = timeout

    def callLater(self, period, func):
        """Override TimeoutMixin.callLater so we use self._clock.

        This allows us to write unit tests that don't depend on actual wall
        clock time.
        """
        return self._clock.callLater(period, func)

    def connectionMade(self):
        """Start the timeout counter when connection is made."""
        self.setTimeout(self._timeout)

    def timeoutConnection(self):
        """When a timeout occurs, kill the process and record a TimeoutError.
        """
        self.unexpectedError(failure.Failure(error.TimeoutError()))

    def processEnded(self, reason):
        """See `ProcessMonitorProtocol.processEnded`.

        Cancel the timeout, as the process no longer exists.
        """
        self.setTimeout(None)
        ProcessMonitorProtocol.processEnded(self, reason)

