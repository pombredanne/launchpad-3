# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewSubscription"""

from datetime import datetime
import unittest

import pytz

from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.ftests import login
from canonical.launchpad.testing import LaunchpadObjectFactory

class TestCodeReviewSubscription(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        login('test@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.bmp = self.factory.makeProposalToMerge()
        self.subscriber = self.factory.makePerson()
        self.registrant = self.factory.makePerson()

    def test_create_self_subscription(self):
        subscription = self.bmp.createSubscription(self.subscriber)
        cur_time = datetime.now(tz=pytz.timezone('UTC'))
        self.assertEqual(self.bmp, subscription.branch_merge_proposal)
        self.assertEqual(self.subscriber, subscription.person)
        delta = subscription.date_created - cur_time
        seconds_difference = delta.days * 24 * 60 * 60 + delta.seconds
        self.assertAlmostEqual(0, seconds_difference, -1)

    def test_create_other_subscription(self):
        subscription = self.bmp.createSubscription(
            self.subscriber, self.registrant)
        self.assertEqual(self.subscriber, subscription.person)
        self.assertEqual(self.registrant, subscription.registrant)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
