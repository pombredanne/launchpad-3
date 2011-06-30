# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll adapter tests."""

__metaclass__ = type

from ..adapters import LongPollSubscriber
from ..interfaces import ILongPollSubscriber

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import BaseLayer
from lp.testing import TestCase


class TestLongPollSubscriber(TestCase):

    layer = BaseLayer

    def test_interface(self):
        request = LaunchpadTestRequest()
        subscriber = LongPollSubscriber(request)
        self.assertProvides(subscriber, ILongPollSubscriber)
