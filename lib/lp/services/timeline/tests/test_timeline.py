# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of the Timeline class."""

__metaclass__ = type

import datetime

import testtools

from lp.services.timeline.timedaction import TimedAction
from lp.services.timeline.timeline import OverlappingActionError, Timeline


class TestTimeline(testtools.TestCase):

    def test_start_returns_action(self):
        timeline = Timeline()
        action = timeline.start("Sending mail", "Noone")
        self.assertIsInstance(action, TimedAction)
        self.assertEqual("Sending mail", action.category)
        self.assertEqual("Noone", action.detail)
        self.assertEqual(None, action.duration)
        self.assertEqual(timeline, action.timeline)

    def test_can_supply_list(self):
        actions = "foo"
        timeline = Timeline(actions)
        self.assertEqual(actions, timeline.actions)

    def test_start_with_unfinished_action_fails(self):
        # A design constraint of timeline says that overlapping actions are not
        # permitted. See the Timeline docstrings.
        timeline = Timeline()
        action = timeline.start("Sending mail", "Noone")
        self.assertRaises(OverlappingActionError, timeline.start,
            "Sending mail", "Noone")

    def test_start_after_finish_works(self):
        timeline = Timeline()
        action = timeline.start("Sending mail", "Noone")
        action.finish()
        action = timeline.start("Sending mail", "Noone")
        action.finish()
        self.assertEqual(2, len(timeline.actions))

    def test_baseline(self):
        timeline = Timeline()
        self.assertIsInstance(timeline.baseline, datetime.datetime)
