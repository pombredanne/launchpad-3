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

    def test_nested_start_permitted(self):
        # When explicitly requested a nested start can be done
        timeline = Timeline()
        action = timeline.start("Calling openid", "hostname", allow_nested=True)
        child = timeline.start("SQL Callback", "SELECT...")

    def test_nested_start_is_not_transitive(self):
        # nesting is explicit at each level - not inherited.
        timeline = Timeline()
        action = timeline.start("Calling openid", "hostname", allow_nested=True)
        child = timeline.start("SQL Callback", "SELECT...")
        self.assertRaises(OverlappingActionError, timeline.start,
            "Sending mail", "Noone")

    def test_multiple_nested_children_permitted(self):
        # nesting is not reset by each action that is added.
        timeline = Timeline()
        action = timeline.start("Calling openid", "hostname", allow_nested=True)
        child = timeline.start("SQL Callback", "SELECT...")
        child.finish()
        child = timeline.start("SQL Callback", "SELECT...")

    def test_multiple_starts_after_nested_group_prevented(self):
        # nesting stops being permitted when the nesting action is finished.
        timeline = Timeline()
        action = timeline.start("Calling openid", "hostname", allow_nested=True)
        action.finish()
        child = timeline.start("SQL Callback", "SELECT...")
        self.assertRaises(OverlappingActionError, timeline.start,
            "Sending mail", "Noone")

    def test_nesting_within_nesting_permitted(self):
        timeline = Timeline()
        action = timeline.start("Calling openid", "hostname", allow_nested=True)
        middle = timeline.start("Calling otherlibrary", "", allow_nested=True)
        child = timeline.start("SQL Callback", "SELECT...")

    def test_finishing_nested_within_nested_leaves_outer_nested_nesting(self):
        timeline = Timeline()
        action = timeline.start("Calling openid", "hostname", allow_nested=True)
        middle = timeline.start("Calling otherlibrary", "", allow_nested=True)
        middle.finish()
        child = timeline.start("SQL Callback", "SELECT...")

    def test_nested_actions_recorded_as_two_zero_length_actions(self):
        timeline = Timeline()
        action = timeline.start("Calling openid", "hostname", allow_nested=True)
        child = timeline.start("SQL Callback", "SELECT...")
        child.finish()
        action.finish()
        self.assertEqual(3, len(timeline.actions))
        self.assertEqual(datetime.timedelta(), timeline.actions[0].duration)
        self.assertEqual(datetime.timedelta(), timeline.actions[2].duration)

    def test_nested_category_labels(self):
        # To identify start/stop pairs '-start' and '-stop' are put onto the
        # category of nested actions:
        timeline = Timeline()
        action = timeline.start("Calling openid", "hostname", allow_nested=True)
        action.finish()
        self.assertEqual('Calling openid-start', timeline.actions[0].category)
        self.assertEqual('Calling openid-stop', timeline.actions[1].category)

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
