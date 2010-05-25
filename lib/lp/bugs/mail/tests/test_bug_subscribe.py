# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Bug subscription-related email tests."""

from unittest import TestLoader

from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory


class TestSubscribedBySomeoneElseNotification(TestCaseWithFactory):
    """Test emails sent when subscribed by someone else."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Run the tests as a logged-in user.
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def test_subscribed_by_someone_else(self):
        bug = self.factory.makeBug()
        person_subscribing = self.factory.makePerson()
        person_subscribed = self.factory.makePerson()
        bug_subscription = bug.subscribe(
            person_subscribed, person_subscribing, suppress_notify=False)
        self.assertEqual(bug_subscription.person, person_subscribed)
        self.assertEqual(bug_subscription.subscribed_by, person_subscribing)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
