# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugSubscription views."""

__metaclass__ = type

from storm.store import Store

from canonical.launchpad.ftests import LaunchpadFormHarness
from canonical.testing.layers import LaunchpadFunctionalLayer

from lp.bugs.browser.bugsubscription import BugSubscriptionSubscribeSelfView
from lp.bugs.model.bugsubscription import BugSubscription
from lp.registry.enum import BugNotificationLevel
from lp.services.features.testing import FeatureFixture
from lp.testing import person_logged_in, TestCaseWithFactory


class BugSubscriptionAdvancedFeaturesTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(BugSubscriptionAdvancedFeaturesTestCase, self).setUp()
        self.useFixture(
            FeatureFixture({
                'malone.advanced-subscriptions.enabled': 'on'}))

    def _getBugSubscriptionForUserAndBug(self, user, bug):
        """Return the BugSubscription for a given user, bug combination."""
        store = Store.of(bug)
        return store.find(
            BugSubscription,
            BugSubscription.person == user,
            BugSubscription.bug == bug).one()

    def test_subscribe_uses_bug_notification_level(self):
        # When a user subscribes to a bug using the advanced features on
        # the Bug +subscribe page, the bug notification level they
        # choose is taken into account.
        bug = self.factory.makeBug()
        # We unsubscribe the bug's owner because if we don't there will
        # be two COMMENTS-level subscribers.
        with person_logged_in(bug.owner):
            bug.unsubscribe(bug.owner, bug.owner)

        for level in BugNotificationLevel.items:
            person = self.factory.makePerson()
            with person_logged_in(person):
                harness = LaunchpadFormHarness(
                    bug.default_bugtask, BugSubscriptionSubscribeSelfView)
                form_data = {
                    'field.subscription': person.name,
                    'field.bug_notification_level': level.name,
                    }
                harness.submit('continue', form_data)

            subscription = self._getBugSubscriptionForUserAndBug(
                person, bug)
            self.assertEqual(
                level, subscription.bug_notification_level,
                "Bug notification level of subscription should be %s, is "
                "actually %s." % (
                    level.name, subscription.bug_notification_level.name))
