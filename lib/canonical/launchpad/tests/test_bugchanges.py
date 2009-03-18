# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for recording changes done to a bug."""

import unittest

from zope.event import notify

from lazr.lifecycle.event import ObjectCreatedEvent

from canonical.launchpad.database import BugNotification
from canonical.launchpad.ftests import login
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing import DatabaseFunctionalLayer


class TestBugChanges(unittest.TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.bug = self.factory.makeBug()
        self.saveOldChanges()

    def saveOldChanges(self):
        """Save the old changes to the bug.

        This method should be called after all the setup is done.
        """
        self.old_activities = list(self.bug.activity)
        self.old_notification_ids = [
            notification.id
            for notification in BugNotification.selectBy(bug=self.bug)]

    def assertRecordedChange(self, expected_activity=None):
        """Assert that things were recorded as expected."""
        new_activities = [
            activity for activity in self.bug.activity
            if activity not in self.old_activities]
        bug_notifications = BugNotification.selectBy(
            bug=self.bug, orderBy='id')
        new_notifications = [
            notification for notification in bug_notifications
            if notification.id not in self.old_notification_ids]
        if expected_activity is None:
            self.assertEqual(len(new_activities), 0)
        else:
            self.assertEqual(len(new_activities), 1)
            [added_activity] = new_activities
            self.assertEqual(
                added_activity.person, expected_activity['person'])
            self.assertEqual(
                added_activity.whatchanged, expected_activity['whatchanged'])
            self.assertEqual(
                added_activity.oldvalue, expected_activity.get('oldvalue'))
            self.assertEqual(
                added_activity.newvalue, expected_activity.get('newvalue'))
            self.assertEqual(
                added_activity.message, expected_activity.get('message'))

        # So far we can only test actions that don't generate an e-mail
        # notification.
        self.assertEqual(len(new_notifications), 0)

    def test_subscribe(self):
        # Subscribing someone to a bug adds an item to the activity log,
        # but doesn't send an e-mail notification.
        user = self.factory.makePerson(displayname='Arthur Dent')
        subscriber = self.factory.makePerson(displayname='Mom')
        bug_subscription = self.bug.subscribe(user, subscriber)
        notify(ObjectCreatedEvent(bug_subscription, user=subscriber))
        subscribe_activity = dict(
            whatchanged='bug',
            message='added subscriber Arthur Dent',
            person=subscriber)
        self.assertRecordedChange(expected_activity=subscribe_activity)

    def test_unsubscribe(self):
        # Unsubscribing someone from a bug adds an item to the activity
        # log, but doesn't send an e-mail notification.
        user = self.factory.makePerson(displayname='Arthur Dent')
        subscriber = self.factory.makePerson(displayname='Mom')
        bug_subscription = self.bug.subscribe(user, subscriber)
        self.saveOldChanges()
        self.bug.unsubscribe(user, subscriber)
        unsubscribe_activity = dict(
            whatchanged='removed subscriber Arthur Dent',
            person=subscriber)
        self.assertRecordedChange(expected_activity=unsubscribe_activity)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
