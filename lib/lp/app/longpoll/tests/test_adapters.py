# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll adapter tests."""

__metaclass__ = type

from ..adapters import LongPollSubscriber
from ..interfaces import ILongPollSubscriber

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCase


class TestLongPollSubscriber(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_interface(self):
        request = LaunchpadTestRequest()
        subscriber = LongPollSubscriber(request)
        self.assertProvides(subscriber, ILongPollSubscriber)

    def test_subscribe_key(self):
        request = LaunchpadTestRequest()
        subscriber = LongPollSubscriber(request)
        self.assertIsInstance(subscriber.subscribe_key, str)
        self.assertEqual(36, len(subscriber.subscribe_key))

    def test_adapter(self):
        request = LaunchpadTestRequest()
        subscriber = ILongPollSubscriber(request)
        self.assertIsInstance(subscriber, LongPollSubscriber)
        # The same subscriber is returned on subsequent adaptions.
        self.assertIs(subscriber, ILongPollSubscriber(request))

    def test_subscribe_queue(self):
        # LongPollSubscriber creates a new queue with a new unique name.
        pass

    def test_json_cache_populated(self):
        # LongPollSubscriber puts the name of the new queue into the JSON
        # cache.
        pass
