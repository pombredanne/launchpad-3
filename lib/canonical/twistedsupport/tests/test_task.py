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
        self._num_job_factory_calls = 0

    def _job_factory(self):
        self._num_job_factory_calls += 1
        return None

    def makeJobSource(self, interval=None, clock=None):
        if clock is None:
            clock = BrokenClock()
        if interval is None:
            interval = self.factory.getUniqueInteger()
        return PollingJobSource(interval, self._job_factory, clock=clock)

    def test_provides_IJobSource(self):
        # PollingJobSource instances provide IJobSource.
        self.assertProvides(self.makeJobSource(), IJobSource)

    def test_start_commences_polling(self):
        # Calling `start` on a PollingJobSource begins polling the job
        # factory.
        job_source = self.makeJobSource(clock=Clock())
        job_source.start(None)
        self.assertEqual(1, self._num_job_factory_calls)

    def test_start_continues_polling(self):
        # Calling `start` on a PollingJobSource begins polling the job
        # factory. This polling continues over time, once every 'interval'
        # seconds.
        clock = Clock()
        interval = self.factory.getUniqueInteger()
        job_source = self.makeJobSource(interval=interval, clock=clock)
        job_source.start(None)
        self._num_job_factory_calls = 0
        clock.advance(interval)
        self.assertEqual(1, self._num_job_factory_calls)

    def test_stop_stops_polling(self):
        # Calling `stop` after a PollingJobSource has started will stop the
        # polling.
        clock = Clock()
        interval = self.factory.getUniqueInteger()
        job_source = self.makeJobSource(interval=interval, clock=clock)
        job_source.start(None)
        job_source.stop()
        self._num_job_factory_calls = 0
        clock.advance(interval)
        # No more calls were made.
        self.assertEqual(0, self._num_job_factory_calls)

    # XXX: starting multiple times
    # XXX: starting mulitple times with different accept_jobs
    # XXX: stopping multiple times
    # XXX: calling stop before start
    # XXX: the 'accept job' protocol


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
