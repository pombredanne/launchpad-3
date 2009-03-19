# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for recording changes done to a bug."""

import unittest

from zope.event import notify
from zope.interface import providedBy

from lazr.lifecycle.event import ObjectCreatedEvent, ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot

from canonical.launchpad.database import BugNotification
from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.interfaces.bugtask import (
    BugTaskImportance, BugTaskStatus, IBugTask)
from canonical.launchpad.ftests import login
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing import LaunchpadFunctionalLayer


class TestBugChanges(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.user = self.factory.makePerson(displayname='Arthur Dent')
        self.bug = self.factory.makeBug(owner=self.user)

        product = self.factory.makeProduct(owner=self.user)
        owned_bug = self.factory.makeBug(product=product, owner=self.user)
        self.bug_task = owned_bug.bugtasks[0]
        self.saveOldChanges()
        self.saveOldChanges(bug=owned_bug)

    def saveOldChanges(self, bug=None):
        """Save the old changes to a bug.

        This method should be called after all the setup is done.
        """
        if bug is None:
            bug = self.bug

        self.old_activities = list(bug.activity)
        self.old_notification_ids = [
            notification.id
            for notification in BugNotification.selectBy(bug=bug)]

    def changeAttribute(self, obj, attribute, new_value):
        """Set the value of `attribute` on `obj` to `new_value`.

        :return: The value of `attribute` before modification.
        """
        obj_before_modification = Snapshot(obj, providing=providedBy(obj))
        setattr(obj, attribute, new_value)
        notify(ObjectModifiedEvent(
            obj, obj_before_modification, [attribute], self.user))

        return getattr(obj_before_modification, attribute)

    def assertRecordedChange(self, expected_activity=None,
                             expected_notification=None, bug=None):
        """Assert that things were recorded as expected."""
        if bug is None:
            bug = self.bug

        new_activities = [
            activity for activity in bug.activity
            if activity not in self.old_activities]
        bug_notifications = BugNotification.selectBy(
            bug=bug, orderBy='id')
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

    def test_link_branch(self):
        # Linking a branch to a bug adds both to the activity log and
        # sends an e-mail notification.
        branch = self.factory.makeBranch()
        self.bug.addBranch(branch, self.user)
        added_activity = {
            'person': self.user,
            'whatchanged': 'branch linked',
            'newvalue': branch.bzr_identity,
            }
        added_notification = {
            'text': "** Branch linked: %s" % branch.bzr_identity,
            'person': self.user,
            }
        self.assertRecordedChange(
            expected_activity=added_activity,
            expected_notification=added_notification)

    def test_unlink_branch(self):
        # Unlinking a branch from a bug adds both to the activity log and
        # sends an e-mail notification.
        branch = self.factory.makeBranch()
        self.bug.addBranch(branch, self.user)
        self.saveOldChanges()
        self.bug.removeBranch(branch, self.user)
        added_activity = {
            'person': self.user,
            'whatchanged': 'branch unlinked',
            'oldvalue': branch.bzr_identity,
            }
        added_notification = {
            'text': "** Branch unlinked: %s" % branch.bzr_identity,
            'person': self.user,
            }
        self.assertRecordedChange(
            expected_activity=added_activity,
            expected_notification=added_notification)

    def test_make_private(self):
        # Marking a bug as private adds items to the bug's activity log
        # and notifications.
        bug_before_modification = Snapshot(self.bug, providing=IBug)
        self.bug.setPrivate(True, self.user)
        notify(ObjectModifiedEvent(
            self.bug, bug_before_modification, ['private'], self.user))

        visibility_change_activity = {
            'person': self.user,
            'whatchanged': 'visibility',
            'oldvalue': 'public',
            'newvalue': 'private',
            }

        visibility_change_notification = {
            'text': '** Visibility changed to: Private',
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=visibility_change_activity,
            expected_notification=visibility_change_notification)

    def test_make_public(self):
        # Marking a bug as public adds items to the bug's activity log
        # and notifications.
        private_bug = self.factory.makeBug(private=True)
        self.assertTrue(private_bug.private)

        bug_before_modification = Snapshot(private_bug, providing=IBug)
        private_bug.setPrivate(False, self.user)
        notify(ObjectModifiedEvent(
            private_bug, bug_before_modification, ['private'], self.user))

        visibility_change_activity = {
            'person': self.user,
            'whatchanged': 'visibility',
            'oldvalue': 'private',
            'newvalue': 'public',
            }

        visibility_change_notification = {
            'text': '** Visibility changed to: Public',
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=visibility_change_activity,
            expected_notification=visibility_change_notification,
            bug=private_bug)

    def test_tags_added(self):
        # Adding tags to a bug will add BugActivity and BugNotification
        # entries.
        old_tags = self.changeAttribute(
            self.bug, 'tags', ['first-new-tag', 'second-new-tag'])

        tag_change_activity = {
            'person': self.user,
            'whatchanged': 'tags',
            'oldvalue': '',
            'newvalue': 'first-new-tag second-new-tag',
            }

        tag_change_notification = {
            'person': self.user,
            'text': '** Tags added: first-new-tag second-new-tag',
            }

        self.assertRecordedChange(
            expected_activity=tag_change_activity,
            expected_notification=tag_change_notification)

    def test_tags_removed(self):
        # Removing tags from a bug adds BugActivity and BugNotification
        # entries.
        self.bug.tags = ['first-new-tag', 'second-new-tag']
        self.saveOldChanges()
        old_tags = self.changeAttribute(
            self.bug, 'tags', ['first-new-tag'])

        tag_change_activity = {
            'person': self.user,
            'whatchanged': 'tags',
            'oldvalue': 'first-new-tag second-new-tag',
            'newvalue': 'first-new-tag',
            }

        tag_change_notification = {
            'person': self.user,
            'text': '** Tags removed: second-new-tag',
            }

        self.assertRecordedChange(
            expected_activity=tag_change_activity,
            expected_notification=tag_change_notification)

    def test_mark_as_security_vulnerability(self):
        # Marking a bug as a security vulnerability adds to the bug's
        # activity log and sends a notification.
        self.bug.security_related = False
        self.changeAttribute(self.bug, 'security_related', True)

        security_change_activity = {
            'person': self.user,
            'whatchanged': 'security vulnerability',
            'oldvalue': 'no',
            'newvalue': 'yes',
            }

        security_change_notification = {
            'text': (
                '** This bug has been flagged as '
                'a security vulnerability'),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=security_change_activity,
            expected_notification=security_change_notification)

    def test_unmark_as_security_vulnerability(self):
        # Unmarking a bug as a security vulnerability adds to the
        # bug's activity log and sends a notification.
        self.bug.security_related = True
        self.changeAttribute(self.bug, 'security_related', False)

        security_change_activity = {
            'person': self.user,
            'whatchanged': 'security vulnerability',
            'oldvalue': 'yes',
            'newvalue': 'no',
            }

        security_change_notification = {
            'text': (
                '** This bug is no longer flagged as '
                'a security vulnerability'),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=security_change_activity,
            expected_notification=security_change_notification)

    def test_attachment_added(self):
        # Adding an attachment to a bug adds entries in both BugActivity
        # and BugNotification.
        message = self.factory.makeMessage(owner=self.user)
        self.bug.linkMessage(message)
        self.saveOldChanges()

        attachment = self.factory.makeBugAttachment(
            bug=self.bug, owner=self.user, comment=message)

        attachment_added_activity = {
            'person': self.user,
            'whatchanged': 'attachment added',
            'oldvalue': None,
            'newvalue': '%s %s' % (
                attachment.title, attachment.libraryfile.http_url),
            }

        attachment_added_notification = {
            'person': self.user,
            'text': '** Attachment added: "%s"\n   %s' % (
                attachment.title, attachment.libraryfile.http_url),
            }

        self.assertRecordedChange(
            expected_notification=attachment_added_notification,
            expected_activity=attachment_added_activity)

    def test_attachment_removed(self):
        # Removing an attachment from a bug adds entries in both BugActivity
        # and BugNotification.
        attachment = self.factory.makeBugAttachment(
            bug=self.bug, owner=self.user)
        self.saveOldChanges()
        attachment.removeFromBug(user=self.user)

        attachment_removed_activity = {
            'person': self.user,
            'whatchanged': 'attachment removed',
            'newvalue': None,
            'oldvalue': '%s %s' % (
                attachment.title, attachment.libraryfile.http_url),
            }

        attachment_removed_notification = {
            'person': self.user,
            'text': '** Attachment removed: "%s"\n   %s' % (
                attachment.title, attachment.libraryfile.http_url),
            }

        self.assertRecordedChange(
            expected_notification=attachment_removed_notification,
            expected_activity=attachment_removed_activity)

    def test_change_bugtask_importance(self):
        # When a bugtask's importance is changed, things should happen.
        bug_task_before_modification = Snapshot(
            self.bug_task, providing=providedBy(self.bug_task))
        self.bug_task.transitionToImportance(
            BugTaskImportance.HIGH, user=self.user)
        notify(ObjectModifiedEvent(
            self.bug_task, bug_task_before_modification,
            ['importance'], user=self.user))

        expected_activity = {
            'person': self.user,
            'whatchanged': '%s: importance' % self.bug_task.bugtargetname,
            'oldvalue': 'Undecided',
            'newvalue': 'High',
            'message': None,
            }

        expected_notification = {
            'text': (
                u'** Changed in: %s\n   Importance: Undecided => High' %
                self.bug_task.bugtargetname),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=expected_activity,
            expected_notification=expected_notification,
            bug=self.bug_task.bug)

    def test_change_bugtask_status(self):
        # When a bugtask's status is changed, things should happen.
        bug_task_before_modification = Snapshot(
            self.bug_task, providing=providedBy(self.bug_task))
        self.bug_task.transitionToStatus(
            BugTaskStatus.FIXRELEASED, user=self.user)
        notify(ObjectModifiedEvent(
            self.bug_task, bug_task_before_modification, ['status'],
            user=self.user))

        expected_activity = {
            'person': self.user,
            'whatchanged': '%s: status' % self.bug_task.bugtargetname,
            'oldvalue': 'New',
            'newvalue': 'Fix Released',
            'message': None,
            }

        expected_notification = {
            'text': (
                u'** Changed in: %s\n       Status: New => Fix Released' %
                self.bug_task.bugtargetname),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=expected_activity,
            expected_notification=expected_notification,
            bug=self.bug_task.bug)

    def test_target_bugtask_to_product(self):
        # When a bugtask's target is changed, things should happen.
        bug_task_before_modification = Snapshot(
            self.bug_task, providing=providedBy(self.bug_task))

        new_target = self.factory.makeProduct(owner=self.user)
        self.bug_task.transitionToTarget(new_target)
        notify(ObjectModifiedEvent(
            self.bug_task, bug_task_before_modification,
            ['target', 'product'], user=self.user))

        expected_notification = {
            'text': (
                u'** Changed in: %s\n      '
                'Product: %s => %s' % (
                self.bug_task.bugtargetname,
                bug_task_before_modification.bugtargetdisplayname,
                self.bug_task.bugtargetdisplayname)),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=None,
            expected_notification=expected_notification,
            bug=self.bug_task.bug)

    def test_target_bugtask_to_sourcepackage(self):
        # When a bugtask's target is changed, things should happen.
        target = self.factory.makeDistributionSourcePackage()
        new_target = self.factory.makeDistributionSourcePackage(
            distribution=target.distribution)

        source_package_bug = self.factory.makeBug(owner=self.user)
        source_package_bug_task = source_package_bug.addTask(
            owner=self.user, target=target)
        self.saveOldChanges(source_package_bug)

        bug_task_before_modification = Snapshot(
            source_package_bug_task,
            providing=providedBy(source_package_bug_task))
        source_package_bug_task.transitionToTarget(new_target)

        notify(ObjectModifiedEvent(
            source_package_bug_task, bug_task_before_modification,
            ['target', 'sourcepackagename'], user=self.user))

        expected_notification = {
            'text': (
                u'** Changed in: %s\nSourcepackagename: %s => %s' % (
                source_package_bug_task.bugtargetname,
                bug_task_before_modification.target.name,
                source_package_bug_task.target.name)),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=None,
            expected_notification=expected_notification,
            bug=source_package_bug)

    def test_add_bugwatch_to_bugtask(self):
        # Adding a BugWatch to a bug task only records an entry in the
        # BugNotification table.
        bug_watch = self.factory.makeBugWatch(bug=self.bug_task.bug)
        self.saveOldChanges(bug=self.bug_task.bug)

        self.changeAttribute(self.bug_task, 'bugwatch', bug_watch)

        expected_notification = {
            'text': (
                u'** Changed in: %s\n     Bugwatch: None => %s' % (
                self.bug_task.bugtargetname, bug_watch.title)),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=None,
            expected_notification=expected_notification,
            bug=self.bug_task.bug)

    def test_remove_bugwatch_from_bugtask(self):
        # Removing a BugWatch from a bug task only records an entry in the
        # BugNotification table.
        bug_watch = self.factory.makeBugWatch(bug=self.bug_task.bug)
        self.changeAttribute(self.bug_task, 'bugwatch', bug_watch)
        self.saveOldChanges(bug=self.bug_task.bug)

        self.changeAttribute(self.bug_task, 'bugwatch', None)

        expected_notification = {
            'text': (
                u'** Changed in: %s\n     Bugwatch: %s => None' % (
                self.bug_task.bugtargetname, bug_watch.title)),
            'person': self.user,
            }

        self.assertRecordedChange(
            expected_activity=None,
            expected_notification=expected_notification,
            bug=self.bug_task.bug)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
