# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of the TimedAction class."""

__metaclass__ = type

import datetime

import testtools

from lp.services.timeline.nestingtimedaction import NestingTimedAction
from lp.services.timeline.timeline import Timeline


class TestNestingTimedAction(testtools.TestCase):

    def test_finish_adds_action(self):
        timeline = Timeline()
        action = NestingTimedAction("Sending mail", None, timeline)
        action.finish()
        self.assertEqual(1, len(timeline.actions))
        self.assertEqual(datetime.timedelta(), timeline.actions[-1].duration)

    def test__init__sets_duration(self):
        action = NestingTimedAction("Sending mail", None)
        self.assertEqual(datetime.timedelta(), action.duration)
