# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tools for managing long-running or difficult jobs with Twisted."""

__metaclass__ = type
__all__ = [
    'IJobSource',
    'PollingJobSource',
    ]

from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from twisted.python import log

from zope.interface import implements, Interface


class IJobSource(Interface):
    """A source of jobs to do."""

    def start(accept_job):
        """Start generating jobs.

        If `start` has already been called, then this call is silently
        ignored. XXX -- still need to decide this.

        :param accept_job: A single-parameter callable that is called with
            the job only when there is new work to do.
        """

    def stop():
        """Stop generating jobs.

        After this is called, the accept_job callable will not be called,
        until `start` is called again.

        Any subsequent calls to `stop` are silently ignored.
        """


class PollingJobSource:
    """A job source that polls to generate jobs.

    Useful for systems where we need to poll a central server in order to find
    new work to do.
    """

    implements(IJobSource)

    def __init__(self, interval, job_factory, clock=None):
        """Construct a `PollingJobSource`.

        Polls 'job_factory' every 'interval' seconds. 'job_factory' returns
        either None if there's no work to do right now, or some representation
        of the job which is passed to the 'accept_job' callable given to
        `start`.

        :param interval: The length of time between polls in seconds.
        :param job_factory: The polling mechanism. This is a nullary callable
            that can return a Deferred. See above for more details.
        :param clock: An `IReactorTime` implementation that we use to manage
            the interval-based polling. Defaults to using the reactor (i.e.
            actual time).
        """
        self._interval = interval
        self._job_factory = job_factory
        if clock is None:
            clock = reactor
        self._clock = clock

    def start(self, accept_job):
        """See `IJobSource`."""
        self._looping_call = LoopingCall(self._job_factory)
        self._looping_call.clock = self._clock
        self._looping_call.start(self._interval)

    def stop(self):
        """See `IJobSource`."""
        self._looping_call.stop()



class OldPollingJobSource:
    """ """

    implements(IJobSource)

    def __init__(self, interval, get_job):
        self.interval = interval
        self.get_job = get_job
        self._looping_call = None

    def start(self, acceptJob):
        self.stop()
        self._looping_call = LoopingCall(self._poll, acceptJob)
        self._looping_call.start(self.interval)

    def _poll(self, acceptJob):
        def _cb(job):
            if job is not None:
                acceptJob(job)
        d = defer.maybeDeferred(self.get_job)
        d.addCallback(_cb) #.addErrback('XXX')

    def stop(self):
        if self._looping_call is not None:
            self._looping_call.cancel()
            self._looping_call = None


class ParallelLimitedJobSink:
    """ """

    def __init__(self, worker_limit, job_source):
        self.worker_limit = worker_limit
        self.worker_count = 0
        self.job_source = job_source

    def start(self):
        self._terminationDeferred = defer.Deferred()
        self.job_source.start(self.acceptJob)
        return self._terminationDeferred

    def acceptJob(self, job):
        self.worker_count += 1
        if self.worker_count >= self.worker_limit:
            self.source.stop()
        d = job.run()
        # We don't expect these jobs to have interesting return values or
        # failure modes.
        d.addErrback(log.err)
        d.addCallback(self.jobEnded)

    def jobEnded(self, ignored):
        self.worker_count -= 1
        if self.worker_count == 0:
            self._terminationDeferred.callback(None)
        if self.worker_count < self.worker_limit:
            self.start()

