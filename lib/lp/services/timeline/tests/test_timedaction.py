# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of the TimedAction class."""

__metaclass__ = type

import datetime

import testtools

from lp.services.timeline.timedaction import TimedAction
from lp.services.timeline.timeline import Timeline


class TestTimedAction(testtools.TestCase):

    def test_starts_now(self):
        action = TimedAction("Sending mail", None)
        self.assertIsInstance(action.start, datetime.datetime)

    def test_finish_sets_duration(self):
        action = TimedAction("Sending mail", None)
        self.assertEqual(None, action.duration)
        action.finish()
        self.assertIsInstance(action.duration, datetime.timedelta)

    def test__init__sets_category(self):
        action = TimedAction("Sending mail", None)
        self.assertEqual("Sending mail", action.category)

    def test__init__sets_detail(self):
        action = TimedAction(None, "fred.jones@example.com")
        self.assertEqual("fred.jones@example.com", action.detail)

    def test_logTuple(self):
        timeline = Timeline()
        action = TimedAction("foo", "bar", timeline)
        # Set variable for deterministic results
        action.start = timeline.baseline + datetime.timedelta(0, 0, 0, 2)
        action.duration = datetime.timedelta(0, 0, 0, 4)
        log_tuple = action.logTuple()
        self.assertEqual(4, len(log_tuple), "!= 4 elements %s" % (log_tuple,))
        # The first element is the start offset in ms.
        self.assertAlmostEqual(2, log_tuple[0])
        # The second element is the end offset in ms.
        self.assertAlmostEqual(6, log_tuple[1])
        self.assertEqual("foo", log_tuple[2])
        self.assertEqual("bar", log_tuple[3])

    def test_logTupleIncomplete(self):
        # Things that start and hit a timeout *may* not get recorded as
        # finishing in normal operation.
        timeline = Timeline()
        action = TimedAction("foo", "bar", timeline)
        # Set variable for deterministic results
        action.start = timeline.baseline + datetime.timedelta(0, 0, 0, 2)
        action._interval_to_now = lambda: datetime.timedelta(0, 0, 0, 3)
        log_tuple = action.logTuple()
        self.assertEqual(4, len(log_tuple), "!= 4 elements %s" % (log_tuple,))
        self.assertAlmostEqual(2, log_tuple[0])
        self.assertAlmostEqual(5, log_tuple[1])
        self.assertEqual("foo", log_tuple[2])
        self.assertEqual("bar", log_tuple[3])
