# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugSubscription views."""

__metaclass__ = type

from canonical.launchpad.ftests import LaunchpadFormHarness
from canonical.testing.layers import LaunchpadFunctionalLayer

from lp.bugs.browser.bugsubscription import BugSubscriptionSubscribeSelfView
from lp.registry.enum import BugNotificationLevel
from lp.testing import (
    feature_flags,
    person_logged_in,
    set_feature_flag,
    TestCaseWithFactory,
    )


class BugSubscriptionAdvancedFeaturesTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(BugSubscriptionAdvancedFeaturesTestCase, self).setUp()
        with feature_flags():
            set_feature_flag(u'malone.advanced-subscriptions.enabled', u'on')

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

        subscription = bug.getSubscriptionForPerson(person)
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

    def test_user_can_update_subscription(self):
        # A user can update their bug subscription using the
        # BugSubscriptionSubscribeSelfView.
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        with feature_flags():
            with person_logged_in(person):
                bug.subscribe(person, person, BugNotificationLevel.COMMENTS)
                # Now the person updates their subscription so they're
                # subscribed at the METADATA level.
                level = BugNotificationLevel.METADATA
                harness = LaunchpadFormHarness(
                    bug.default_bugtask, BugSubscriptionSubscribeSelfView)
                form_data = {
                    'field.subscription': 'update-subscription',
                    'field.bug_notification_level': level.name,
                    }
                harness.submit('continue', form_data)
                self.assertFalse(harness.hasErrors())

        subscription = bug.getSubscriptionForPerson(person)
        self.assertEqual(
            BugNotificationLevel.METADATA,
            subscription.bug_notification_level,
            "Bug notification level of subscription should be METADATA, is "
            "actually %s." % subscription.bug_notification_level.name)

    def test_user_can_unsubscribe(self):
        # A user can unsubscribe from a bug using the
        # BugSubscriptionSubscribeSelfView.
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        with feature_flags():
            with person_logged_in(person):
                bug.subscribe(person, person)
                harness = LaunchpadFormHarness(
                    bug.default_bugtask, BugSubscriptionSubscribeSelfView)
                form_data = {
                    'field.subscription': person.name,
                    }
                harness.submit('continue', form_data)

        subscription = bug.getSubscriptionForPerson(person)
        self.assertIs(
            None, subscription,
            "There should be no BugSubscription for this person.")

    def test_field_values_set_correctly_for_existing_subscriptions(self):
        # When a user who is already subscribed to a bug visits the
        # BugSubscriptionSubscribeSelfView, its bug_notification_level
        # field will be set according to their current susbscription
        # level.
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        with feature_flags():
            with person_logged_in(person):
                # We subscribe using the harness rather than doing it
                # directly so that we don't have to commit() between
                # subscribing and checking the default value.
                level = BugNotificationLevel.METADATA
                harness = LaunchpadFormHarness(
                    bug.default_bugtask, BugSubscriptionSubscribeSelfView)
                form_data = {
                    'field.subscription': person.name,
                    'field.bug_notification_level': level.name,
                    }
                harness.submit('continue', form_data)

                # The default value for the bug_notification_level field
                # should now be the same as the level used to subscribe
                # above.
                harness = LaunchpadFormHarness(
                    bug.default_bugtask, BugSubscriptionSubscribeSelfView)
                bug_notification_level_widget = (
                    harness.view.widgets['bug_notification_level'])
                default_notification_level_value = (
                    bug_notification_level_widget._getDefault())
                self.assertEqual(
                    BugNotificationLevel.METADATA,
                    default_notification_level_value,
                    "Default value for bug_notification_level should be "
                    "METADATA, is actually %s" % default_notification_level_value)
