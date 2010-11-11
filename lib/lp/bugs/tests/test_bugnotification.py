# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to bug notifications."""

__metaclass__ = type

import unittest

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from zope.event import notify
from zope.interface import providedBy

from canonical.config import config
from canonical.launchpad.database.message import MessageSet
from canonical.launchpad.ftests import login
from canonical.testing import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    IUpstreamBugTask,
    )
from lp.bugs.model.bugnotification import (
    BugNotification,
    BugNotificationSet,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.mail_helpers import pop_notifications


class TestNotificationRecipientsOfPrivateBugs(unittest.TestCase):
    """Test who get notified of changes to private bugs."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        factory = LaunchpadObjectFactory()
        self.product = factory.makeProduct()
        self.product_subscriber = factory.makePerson()
        self.product.addBugSubscription(
            self.product_subscriber, self.product_subscriber)
        self.bug_subscriber = factory.makePerson()
        self.private_bug = factory.makeBug(product=self.product, private=True)
        self.reporter = self.private_bug.owner
        self.private_bug.subscribe(self.bug_subscriber, self.reporter)
        [self.product_bugtask] = self.private_bug.bugtasks
        self.direct_subscribers = set(
            person.name for person in [self.bug_subscriber, self.reporter])

    def test_status_change(self):
        # Status changes are sent to the direct subscribers only.
        bugtask_before_modification = Snapshot(
            self.product_bugtask, providing=providedBy(self.product_bugtask))
        self.product_bugtask.transitionToStatus(
            BugTaskStatus.INVALID, self.private_bug.owner)
        notify(ObjectModifiedEvent(
            self.product_bugtask, bugtask_before_modification, ['status'],
            user=self.reporter))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(notified_people, self.direct_subscribers)

    def test_add_comment(self):
        # Comment additions are sent to the direct subscribers only.
        self.private_bug.newMessage(
            self.reporter, subject='subject', content='content')
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(notified_people, self.direct_subscribers)

    def test_bug_edit(self):
        # Bug edits are sent to direct the subscribers only.
        bug_before_modification = Snapshot(
            self.private_bug, providing=providedBy(self.private_bug))
        self.private_bug.description = 'description'
        notify(ObjectModifiedEvent(
            self.private_bug, bug_before_modification, ['description'],
            user=self.reporter))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(notified_people, self.direct_subscribers)


class TestNotificationsSentForBugExpiration(TestCaseWithFactory):
    """Ensure that question subscribers are notified about bug expiration."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestNotificationsSentForBugExpiration, self).setUp(
            user='test@canonical.com')
        # We need a product, a bug for this product, a question linked
        # to the bug and a subscriber.
        self.product = self.factory.makeProduct()
        self.bug = self.factory.makeBug(product=self.product)
        question = self.factory.makeQuestion(target=self.product)
        self.subscriber = self.factory.makePerson()
        question.subscribe(self.subscriber)
        question.linkBug(self.bug)
        # Flush pending notifications for question creation.
        pop_notifications()
        self.layer.switchDbUser(config.malone.expiration_dbuser)

    def test_notifications_for_question_subscribers(self):
        # Ensure that notifications are sent to subscribers of a
        # question linked to the expired bug.
        bugtask = self.bug.default_bugtask
        bugtask_before_modification = Snapshot(
            bugtask, providing=IUpstreamBugTask)
        bugtask.transitionToStatus(BugTaskStatus.EXPIRED, self.product.owner)
        bug_modified = ObjectModifiedEvent(
            bugtask, bugtask_before_modification, ["status"])
        notify(bug_modified)
        self.assertContentEqual(
            [self.product.owner.preferredemail.email,
             self.subscriber.preferredemail.email],
            [mail['To'] for mail in pop_notifications()])


class TestNotificationProcessingWithoutRecipients(TestCaseWithFactory):
    """Adding notificatons without any recipients does not cause any harm.

    In some cases, we may have attempts to send bug notifications for bugs
    that do not have any notification recipients.
    """

    layer = LaunchpadZopelessLayer

    def test_addNotification_without_recipients(self):
        # We can call BugNotificationSet.addNotification() with a empty
        # recipient list.
        #
        # No explicit assertion is necessary in this test -- we just want
        # to be sure that calling BugNotificationSet.addNotification()
        # does not lead to an exception caused by an SQL syntax error for
        # a command that ends with "VALUES ;"
        bug = self.factory.makeBug()
        message = MessageSet().fromText(
            subject='subject', content='content')
        BugNotificationSet().addNotification(
            bug=bug, is_comment=False, message=message, recipients=[])


class TestNotificationsForDuplicates(TestCaseWithFactory):
    """Test who gets notified about actions on duplicate bugs."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestNotificationsForDuplicates, self).setUp(
            user='test@canonical.com')
        self.bug = self.factory.makeBug()
        self.dupe_bug = self.factory.makeBug()
        self.dupe_bug.markAsDuplicate(self.bug)
        self.dupe_subscribers = set(
            self.dupe_bug.getDirectSubscribers() +
            self.dupe_bug.getIndirectSubscribers())

    def test_comment_notifications(self):
        # New comments are only sent to subscribers of the duplicate
        # bug, not to subscribers of the master bug.
        self.dupe_bug.newMessage(
            self.dupe_bug.owner, subject='subject', content='content')
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        recipients = set(
            recipient.person
            for recipient in latest_notification.recipients)
        self.assertEqual(self.dupe_subscribers, recipients)

    def test_duplicate_edit_notifications(self):
        # Bug edits for a duplicate are sent to duplicate subscribers only.
        bug_before_modification = Snapshot(
            self.dupe_bug, providing=providedBy(self.dupe_bug))
        self.dupe_bug.description = 'A changed description'
        notify(ObjectModifiedEvent(
            self.dupe_bug, bug_before_modification, ['description'],
            user=self.dupe_bug.owner))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        recipients = set(
            recipient.person
            for recipient in latest_notification.recipients)
        self.assertEqual(self.dupe_subscribers, recipients)

    def test_branch_linked_notification(self):
        # Notices for branches linked to a duplicate are sent only
        # to subscribers of the duplicate.
        #
        # No one should really do this, but this case covers notices
        # provided by the Bug.addChange mechanism.
        branch = self.factory.makeBranch(owner=self.dupe_bug.owner)
        self.dupe_bug.linkBranch(branch, self.dupe_bug.owner)
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        recipients = set(
            recipient.person
            for recipient in latest_notification.recipients)
        self.assertEqual(self.dupe_subscribers, recipients)
