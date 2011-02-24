# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to bug notifications."""

__metaclass__ = type

from itertools import chain
import unittest

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from testtools.matchers import Not
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
    BugNotificationFilter,
    BugNotificationSet,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.mail_helpers import pop_notifications
from lp.testing.matchers import Contains


class TestNotificationRecipientsOfPrivateBugs(unittest.TestCase):
    """Test who get notified of changes to private bugs."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        factory = LaunchpadObjectFactory()
        self.product_owner = factory.makePerson(name="product-owner")
        self.product = factory.makeProduct(owner=self.product_owner)
        self.product_subscriber = factory.makePerson(
            name="product-subscriber")
        self.product.addBugSubscription(
            self.product_subscriber, self.product_subscriber)
        self.bug_subscriber = factory.makePerson(name="bug-subscriber")
        self.bug_owner = factory.makePerson(name="bug-owner")
        self.private_bug = factory.makeBug(
            product=self.product, private=True, owner=self.bug_owner)
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
        self.assertEqual(self.direct_subscribers, notified_people)

    def test_add_comment(self):
        # Comment additions are sent to the direct subscribers only.
        self.private_bug.newMessage(
            self.reporter, subject='subject', content='content')
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(self.direct_subscribers, notified_people)

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
        self.assertEqual(self.direct_subscribers, notified_people)


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


class TestNotificationsLinkToFilters(TestCaseWithFactory):
    """Ensure link to bug subscription filters works from notifications."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestNotificationsLinkToFilters, self).setUp()
        self.bug = self.factory.makeBug()
        message = self.factory.makeMessage()
        self.notification = BugNotification(
            message=message, activity=None, bug=self.bug, is_comment=False,
            date_emailed=None)

    def test_bug_filters_empty(self):
        # When there are no linked bug filters, it returns a ResultSet
        # with no entries.
        self.assertTrue(self.notification.bug_filters.is_empty())

    def test_bug_filters_single(self):
        # With a linked BugSubscriptionFilter, it is returned.
        subscriber=self.factory.makePerson()
        subscription = self.bug.default_bugtask.target.addSubscription(
            subscriber, subscriber)
        bug_filter = subscription.newBugFilter()
        BugNotificationFilter(
            bug_notification=self.notification,
            bug_subscription_filter=bug_filter)

        self.assertContentEqual([bug_filter],
                                self.notification.bug_filters)

    def test_bug_filters_multiple(self):
        # We can have more than one filter matched up with a single
        # notification.
        subscriber=self.factory.makePerson()
        subscription = self.bug.default_bugtask.target.addSubscription(
            subscriber, subscriber)
        bug_filter1 = subscription.newBugFilter()
        bug_filter2 = subscription.newBugFilter()
        BugNotificationFilter(
            bug_notification=self.notification,
            bug_subscription_filter=bug_filter1)
        BugNotificationFilter(
            bug_notification=self.notification,
            bug_subscription_filter=bug_filter2)

        self.assertContentEqual([bug_filter1, bug_filter2],
                                self.notification.bug_filters)

    def test_getFiltersByRecipient_empty(self):
        # When there are no linked bug filters, it returns a ResultSet
        # with no entries.
        subscriber = self.factory.makePerson()
        self.assertTrue(
            self.notification.getFiltersByRecipient(subscriber).is_empty())

    def test_getFiltersByRecipient_other_persons(self):
        # When there are no bug filters for other recipients,
        # it returns a ResultSet with no entries.
        recipient = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        subscription = self.bug.default_bugtask.target.addSubscription(
            subscriber, subscriber)
        bug_filter = subscription.newBugFilter()
        BugNotificationFilter(
            bug_notification=self.notification,
            bug_subscription_filter=bug_filter)
        self.assertTrue(
            self.notification.getFiltersByRecipient(recipient).is_empty())

    def test_getFiltersByRecipient_match(self):
        # When there are no bug filters for other recipients,
        # it returns a ResultSet with no entries.
        subscriber = self.factory.makePerson()
        subscription = self.bug.default_bugtask.target.addSubscription(
            subscriber, subscriber)
        bug_filter = subscription.newBugFilter()
        BugNotificationFilter(
            bug_notification=self.notification,
            bug_subscription_filter=bug_filter)
        self.assertContentEqual(
            [bug_filter],
            self.notification.getFiltersByRecipient(subscriber))


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
            bug=bug, is_comment=False, message=message, recipients=[],
            activity=None)


class TestNotificationsForDuplicates(TestCaseWithFactory):
    """Test who gets notified about actions on duplicate bugs."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestNotificationsForDuplicates, self).setUp(
            user='test@canonical.com')
        self.bug = self.factory.makeBug()
        self.dupe_bug = self.factory.makeBug()
        self.dupe_bug.markAsDuplicate(self.bug)
        self.dupe_subscribers = set().union(
            self.dupe_bug.getDirectSubscribers(),
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


class NotificationForRegistrantsMixin:
    """Mixin for testing when registrants get notified."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(NotificationForRegistrantsMixin, self).setUp(
            user='foo.bar@canonical.com')
        self.pillar_owner = self.factory.makePerson(name="distro-owner")
        self.bug_owner = self.factory.makePerson(name="bug-owner")
        self.pillar = self.makePillar()
        self.bug = self.makeBug()

    def test_notification_uses_malone(self):
        self.pillar.official_malone = True
        direct = self.bug.getDirectSubscribers()
        indirect = self.bug.getIndirectSubscribers()
        self.assertThat(direct, Not(Contains(self.pillar_owner)))
        self.assertThat(indirect, Contains(self.pillar_owner))

    def test_notification_does_not_use_malone(self):
        self.pillar.official_malone = False
        direct = self.bug.getDirectSubscribers()
        indirect = self.bug.getIndirectSubscribers()
        self.assertThat(direct, Not(Contains(self.pillar_owner)))
        self.assertThat(indirect, Not(Contains(self.pillar_owner)))

    def test_status_change_uses_malone(self):
        # Status changes are sent to the direct and indirect subscribers.
        self.pillar.official_malone = True
        [bugtask] = self.bug.bugtasks
        all_subscribers = set(
            [person.name for person in chain(
                    self.bug.getDirectSubscribers(),
                    self.bug.getIndirectSubscribers())])
        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))
        bugtask.transitionToStatus(
            BugTaskStatus.INVALID, self.bug.owner)
        notify(ObjectModifiedEvent(
            bugtask, bugtask_before_modification, ['status'],
            user=self.bug.owner))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(all_subscribers, notified_people)
        self.assertThat(all_subscribers, Contains(self.pillar_owner.name))

    def test_status_change_does_not_use_malone(self):
        # Status changes are sent to the direct and indirect subscribers.
        self.pillar.official_malone = False
        [bugtask] = self.bug.bugtasks
        all_subscribers = set(
            [person.name for person in chain(
                    self.bug.getDirectSubscribers(),
                    self.bug.getIndirectSubscribers())])
        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))
        bugtask.transitionToStatus(
            BugTaskStatus.INVALID, self.bug.owner)
        notify(ObjectModifiedEvent(
            bugtask, bugtask_before_modification, ['status'],
            user=self.bug.owner))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(all_subscribers, notified_people)
        self.assertThat(
            all_subscribers, Not(Contains(self.pillar_owner.name)))


class TestNotificationsForRegistrantsForDistros(
    NotificationForRegistrantsMixin, TestCaseWithFactory):
    """Test when distribution registrants get notified."""

    def makePillar(self):
        return self.factory.makeDistribution(
            owner=self.pillar_owner)

    def makeBug(self):
        return self.factory.makeBug(
            distribution=self.pillar,
            owner=self.bug_owner)


class TestNotificationsForRegistrantsForProducts(
    NotificationForRegistrantsMixin, TestCaseWithFactory):
    """Test when product registrants get notified."""

    def makePillar(self):
        return self.factory.makeProduct(
            owner=self.pillar_owner)

    def makeBug(self):
        return self.factory.makeBug(
            product=self.pillar,
            owner=self.bug_owner)
