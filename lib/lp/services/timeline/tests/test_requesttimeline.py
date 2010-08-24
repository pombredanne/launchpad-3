# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of requesttimeline."""

__metaclass__ = type

import testtools
from zope.publisher.browser import TestRequest

from lp.services.timeline.requesttimeline import get_request_timeline
from lp.services.timeline.timeline import OverlappingActionError, Timeline


class TestRequestTimeline(testtools.TestCase):

    def test_new_request_get_request_timeline_works(self):
        req = TestRequest()
        timeline = get_request_timeline(req)
        self.assertIsInstance(timeline, Timeline)

    def test_same_timeline_repeated_calls(self):
        req = TestRequest()
        timeline = get_request_timeline(req)
        self.assertEqual(timeline, get_request_timeline(req))
