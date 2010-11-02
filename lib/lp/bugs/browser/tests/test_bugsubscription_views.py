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
from lp.testing import (
    feature_flags,
    person_logged_in,
    set_feature_flag,
    TestCaseWithFactory,
    )


class BugSubscriptionAdvancedFeaturesTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

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

        # We don't display BugNotificationLevel.NOTHING as an option.
        # This is tested below.
        with feature_flags():
            set_feature_flag(u'malone.advanced-subscriptions.enabled', u'on')
            displayed_levels = [
                level for level in BugNotificationLevel.items
                if level != BugNotificationLevel.NOTHING]
            for level in displayed_levels:
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

    def test_nothing_is_not_a_valid_level(self):
        # BugNotificationLevel.NOTHING isn't considered valid when
        # someone is trying to subscribe.
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        with feature_flags():
            set_feature_flag(u'malone.advanced-subscriptions.enabled', u'on')
            with person_logged_in(person):
                level = BugNotificationLevel.NOTHING
                harness = LaunchpadFormHarness(
                    bug.default_bugtask, BugSubscriptionSubscribeSelfView)
                form_data = {
                    'field.subscription': person.name,
                    'field.bug_notification_level': level.name,
                    }
                harness.submit('continue', form_data)
                self.assertTrue(harness.hasErrors())
                self.assertEqual(
                    'Invalid value',
                    harness.getFieldError('bug_notification_level'),
                    "The view should treat BugNotificationLevel.NOTHING "
                    "as an invalid value.")
