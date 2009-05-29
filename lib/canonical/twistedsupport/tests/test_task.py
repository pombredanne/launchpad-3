# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for our task support."""

__metaclass__ = type

import unittest

from twisted.internet.interfaces import IReactorTime
from twisted.internet.task import Clock

from zope.interface import implements

from canonical.twistedsupport.task import IJobSource, PollingJobSource
from lp.testing import TestCase


class BrokenClock:
    """A deliberately broken clock to ensure tests do not invoke the reactor.

    We don't want tests to invoke the reactor, because that is changing global
    state.
    """

    implements(IReactorTime)

    def _reactor_call(self, *args, **kwargs):
        raise AssertionError(
            'Test should not use the reactor: (args=%s, kwargs=%s)'
            % (args, kwargs))

    callLater = _reactor_call
    seconds = _reactor_call
    cancelCallLater = _reactor_call
    getDelayedCalls = _reactor_call


class TestPollingJobSource(TestCase):
    """Tests for `PollingJobSource`."""

    def setUp(self):
        TestCase.setUp(self)
        self._num_job_producer_calls = 0

    def _default_job_consumer(self, job):
        # For many tests, we can safely ignore jobs.
        pass

    def _default_job_producer(self):
        self._num_job_producer_calls += 1
        return None

    def makeJobSource(self, job_producer=None, interval=None, clock=None):
        if job_producer is None:
            job_producer = self._default_job_producer
        if clock is None:
            clock = Clock()
        if interval is None:
            interval = self.factory.getUniqueInteger()
        return PollingJobSource(interval, job_producer, clock=clock)

    def test_provides_IJobSource(self):
        # PollingJobSource instances provide IJobSource.
        self.assertProvides(self.makeJobSource(), IJobSource)

    def test_start_commences_polling(self):
        # Calling `start` on a PollingJobSource begins polling the job
        # factory.
        job_source = self.makeJobSource()
        job_source.start(self._default_job_consumer)
        self.assertEqual(1, self._num_job_producer_calls)

    def test_start_continues_polling(self):
        # Calling `start` on a PollingJobSource begins polling the job
        # factory. This polling continues over time, once every 'interval'
        # seconds.
        clock = Clock()
        interval = self.factory.getUniqueInteger()
        job_source = self.makeJobSource(interval=interval, clock=clock)
        job_source.start(self._default_job_consumer)
        self._num_job_producer_calls = 0
        clock.advance(interval)
        self.assertEqual(1, self._num_job_producer_calls)

    def test_stop_stops_polling(self):
        # Calling `stop` after a PollingJobSource has started will stop the
        # polling.
        clock = Clock()
        interval = self.factory.getUniqueInteger()
        job_source = self.makeJobSource(interval=interval, clock=clock)
        job_source.start(self._default_job_consumer)
        job_source.stop()
        self._num_job_producer_calls = 0
        clock.advance(interval)
        # No more calls were made.
        self.assertEqual(0, self._num_job_producer_calls)

    def test_start_multiple_times(self):
        # Starting a job source multiple times polls immediately and resets
        # the polling loop to start from now.
        pass

    def test_job_consumer_called_when_factory_produces_job(self):
        # The job_consumer passed to start is called when the factory produces
        # a job.
        jobs = ['foo', 'bar']
        jobs_called = []
        job_source = self.makeJobSource(job_producer=iter(jobs).next)
        job_source.start(jobs_called.append)
        self.assertEqual([jobs[0]], jobs_called)

    def test_job_consumer_not_called_when_factory_doesnt_produce(self):
        # The job_consumer passed to start is *not* called when the factory
        # returns None (implying there are no jobs to do right now).
        job_producer = lambda: None
        jobs_called = []
        job_source = self.makeJobSource(job_producer=job_producer)
        job_source.start(jobs_called.append)
        self.assertEqual([], jobs_called)


    # XXX: starting multiple times
    # XXX: starting mulitple times with different accept_jobs
    # XXX: stopping multiple times
    # XXX: calling stop before start

    # XXX: should these be deferred-y tests?
    # XXX: rename 'job' to 'task'


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
