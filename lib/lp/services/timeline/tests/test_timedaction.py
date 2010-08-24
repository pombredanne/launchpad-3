# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of the TimedAction class."""

__metaclass__ = type

import datetime

import testtools

from lp.services.timeline.timedaction import TimedAction


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
