# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewSubscription"""

import unittest

import pytz

from canonical.database.sqlbase import cursor
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
        self.assertEqual(self.bmp, subscription.branch_merge_proposal)
        self.assertEqual(self.subscriber, subscription.person)
        cur = cursor()
        cur.execute("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';")
        [database_now] = cur.fetchone()
        database_now = database_now.replace(tzinfo=pytz.timezone('UTC'))
        self.assertEqual(database_now,
                         subscription.date_created)

    def test_create_other_subscription(self):
        subscription = self.bmp.createSubscription(
            self.subscriber, self.registrant)
        self.assertEqual(self.subscriber, subscription.person)
        self.assertEqual(self.registrant, subscription.registrant)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
