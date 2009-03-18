# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for recording changes done to a bug."""

import unittest

from zope.event import notify

from lazr.lifecycle.event import ObjectCreatedEvent, ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot

from canonical.launchpad.database import BugNotification
from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing import DatabaseFunctionalLayer


class TestBugChanges(unittest.TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.bug = self.factory.makeBug()
        self.user = self.factory.makePerson(displayname='Arthur Dent')
        self.saveOldChanges()

    def saveOldChanges(self):
        """Save the old changes to the bug.

        This method should be called after all the setup is done.
        """
        self.old_activities = list(self.bug.activity)
        self.old_notification_ids = [
            notification.id
            for notification in BugNotification.selectBy(bug=self.bug)]

    def changeAttribute(self, obj, attribute, new_value):
        """Set the value of `attribute` on `obj` to `new_value`.

        :return: The value of `attribute` before modification.
        """
        obj_before_modification = Snapshot(obj, providing=IBug)
        setattr(obj, attribute, new_value)
        notify(ObjectModifiedEvent(
            obj, obj_before_modification, [attribute], self.user))

        return getattr(obj_before_modification, attribute)

    def assertRecordedChange(self, expected_activity=None,
                             expected_notification=None):
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

        if expected_notification is None:
            self.assertEqual(len(new_notifications), 0)
        else:
            self.assertEqual(len(new_notifications), 1)
            [added_notification] = new_notifications
            self.assertEqual(
                added_notification.message.text_contents,
                expected_notification['text'])
            self.assertEqual(
                added_notification.message.owner,
                expected_notification['person'])
            self.assertFalse(added_notification.is_comment)

    def test_subscribe(self):
        # Subscribing someone to a bug adds an item to the activity log,
        # but doesn't send an e-mail notification.
        subscriber = self.factory.makePerson(displayname='Mom')
        bug_subscription = self.bug.subscribe(self.user, subscriber)
        notify(ObjectCreatedEvent(bug_subscription, user=subscriber))
        subscribe_activity = dict(
            whatchanged='bug',
            message='added subscriber Arthur Dent',
            person=subscriber)
        self.assertRecordedChange(expected_activity=subscribe_activity)

    def test_unsubscribe(self):
        # Unsubscribing someone from a bug adds an item to the activity
        # log, but doesn't send an e-mail notification.
        subscriber = self.factory.makePerson(displayname='Mom')
        bug_subscription = self.bug.subscribe(self.user, subscriber)
        self.saveOldChanges()
        self.bug.unsubscribe(self.user, subscriber)
        unsubscribe_activity = dict(
            whatchanged='removed subscriber Arthur Dent',
            person=subscriber)
        self.assertRecordedChange(expected_activity=unsubscribe_activity)

    def test_title_changed(self):
        # Changing the title of a Bug adds items to the activity log and
        # the Bug's notifications.
        old_title = self.changeAttribute(self.bug, 'title', '42')

        title_change_activity = {
            'whatchanged': 'summary',
            'oldvalue': old_title,
            'newvalue': "42",
            'person': self.user,
            }

        title_change_notification = {
            'text': (
                "** Summary changed:\n\n"
                "- %s\n"
                "+ 42" % old_title),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=title_change_activity,
            expected_notification=title_change_notification)

    def test_description_changed(self):
        # Changing the description of a Bug adds items to the activity
        # log and the Bug's notifications.
        old_description = self.changeAttribute(
            self.bug, 'description', 'Hello, world')

        description_change_activity = {
            'person': self.user,
            'whatchanged': 'description',
            'oldvalue': old_description,
            'newvalue': 'Hello, world',
            }

        description_change_notification = {
            'text': (
                "** Description changed:\n\n"
                "- %s\n"
                "+ Hello, world" % old_description),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_notification=description_change_notification,
            expected_activity=description_change_activity)

    def test_bugwatch_added(self):
        # Adding a BugWatch to a bug adds items to the activity
        # log and the Bug's notifications.
        bugtracker = self.factory.makeBugTracker()
        bug_watch = self.bug.addWatch(bugtracker, '42', self.user)

        bugwatch_activity = {
            'person': self.user,
            'whatchanged': 'bug watch added',
            'newvalue': bug_watch.url,
            }

        bugwatch_notification = {
            'text': (
                "** Bug watch added: %s #%s\n"
                "   %s" % (
                    bug_watch.bugtracker.title, bug_watch.remotebug,
                    bug_watch.url)),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_notification=bugwatch_notification,
            expected_activity=bugwatch_activity)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
