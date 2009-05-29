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

    def makeJobSource(self, clock=None):
        # XXX: Passing a positive, non-zero, arbitrary interval.
        if clock is None:
            clock = BrokenClock()
        return PollingJobSource(5, self._job_factory, clock=clock)

    def test_provides_IJobSource(self):
        # PollingJobSource instances provide IJobSource.
        self.assertProvides(self.makeJobSource(), IJobSource)

    def test_start_commences_polling(self):
        # Calling `start` on a PollingJobSource begins polling the job
        # factory.
        clock = Clock()
        job_source = self.makeJobSource()
        job_source.start(None)
        self.assertEqual(1, self._num_job_factory_calls)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
