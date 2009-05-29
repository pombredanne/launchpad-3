# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []

from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from twisted.python import log

from zope.interface import implements, Interface


class IJobSource(Interface):

    def start(acceptJob):
        pass

    def stop():
        pass


class PollingJobSource:
    """ """

    implements(IJobSource)

    def __init__(self, interval, get_job, clock=None):
        self.interval = interval
        self.get_job = get_job
        if clock is None:
            clock = reactor
        self._clock = clock

    def start(self, acceptJob):
        looping_call = LoopingCall(self.get_job)
        looping_call.clock = self._clock
        looping_call.start(self.interval)



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

