# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for our task support."""

__metaclass__ = type

import unittest

from canonical.twistedsupport.task import IJobSource, PollingJobSource
from lp.testing import TestCase


class TestPollingJobSource(TestCase):
    """Tests for `PollingJobSource`."""

    def setUp(self):
        TestCase.setUp(self)
        self._num_job_factory_calls = 0

    def _job_factory(self):
        self._num_job_factory_calls += 1
        return None

    def makeJobSource(self):
        # XXX: Passing a positive, non-zero, arbitrary interval.
        return PollingJobSource(5, self._job_factory)

    def test_provides_IJobSource(self):
        # PollingJobSource instances provide IJobSource.
        self.assertProvides(self.makeJobSource(), IJobSource)

    def test_start_commences_polling(self):
        # Calling `start` on a PollingJobSource begins polling the job
        # factory.
        job_source = self.makeJobSource()
        job_source.start(None)
        self.assertEqual(1, self._num_job_factory_calls)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
