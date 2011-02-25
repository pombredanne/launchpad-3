# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Tests for construction bug notification emails for sending."""

__metaclass__ = type

from datetime import datetime
import unittest

import pytz
from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.database.sqlbase import commit
from lp.bugs.model.bugtask import BugTask
from canonical.launchpad.helpers import get_contact_email_addresses
from canonical.launchpad.interfaces.message import IMessageSet
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.bugs.interfaces.bug import (
    IBug,
    IBugSet,
    )
from lp.bugs.mail.bugnotificationrecipients import BugNotificationRecipients
from lp.bugs.scripts.bugnotification import (
    get_email_notifications,
    notification_batches,
    notification_comment_batches,
    )
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProductSet


class MockBug:
    """A bug which has only the attributes get_email_notifications() needs."""
    implements(IBug)

    duplicateof = None
    private = False
    security_related = False
    messages = []

    def __init__(self, id, owner):
        self.id = id
        self.initial_message = getUtility(IMessageSet).fromText(
            'Bug Title', 'Initial message.', owner=owner)
        self.owner = owner
        self.bugtasks = []
        self.tags = []

    @property
    def title(self):
        return "Mock Bug #%s" % self.id

    def getBugNotificationRecipients(self, duplicateof=None):
        recipients = BugNotificationRecipients()
        no_priv = getUtility(IPersonSet).getByEmail(
            'no-priv@canonical.com')
        recipients.addDirectSubscriber(no_priv)
        return recipients

    def __eq__(self, other):
        """Compare by id to make different subclasses of MockBug be equal."""
        return self.id == other.id


class ExceptionBug(MockBug):
    """A bug which causes an exception to be raised."""

    def getBugNotificationRecipients(self, duplicateof=None):
        raise Exception('FUBAR')


class DBExceptionBug(MockBug):
    """A bug which causes a DB constraint to be triggered."""

    def getBugNotificationRecipients(self, duplicateof=None):
        # Trigger a DB constraint, resulting in the transaction being
        # unusable.
        firefox = getUtility(IProductSet).getByName('firefox')
        bug_one = getUtility(IBugSet).get(1)
        BugTask(bug=bug_one, product=firefox, owner=self.owner)


class MockBugNotificationRecipient:
    """A mock BugNotificationRecipient for testing."""

    def __init__(self):
        self.person = getUtility(IPersonSet).getByEmail(
            'no-priv@canonical.com')
        self.reason_header = 'Test Rationale'
        self.reason_body = 'Test Reason'


class MockBugNotification:
    """A mock BugNotification used for testing.

    Using a real BugNotification won't allow us to set the bug to a mock
    object.
    """

    def __init__(self, message, bug, is_comment, date_emailed):
        self.message = message
        self.bug = bug
        self.is_comment = is_comment
        self.date_emailed = date_emailed
        self.recipients = [MockBugNotificationRecipient()]


class TestGetEmailNotifications(unittest.TestCase):
    """Tests for the exception handling in get_email_notifications()."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up some mock bug notifications to use."""
        self.layer.switchDbUser(config.malone.bugnotification_dbuser)
        sample_person = getUtility(IPersonSet).getByEmail(
            'test@canonical.com')
        self.now = datetime.now(pytz.timezone('UTC'))

        # A normal comment notification for bug 1
        msg = getUtility(IMessageSet).fromText(
            'Subject', "Comment on bug 1", owner=sample_person)
        self.bug_one_notification = MockBugNotification(
            message=msg, bug=MockBug(1, sample_person),
            is_comment=True, date_emailed=None)

        # Another normal comment notification for bug one.
        msg = getUtility(IMessageSet).fromText(
            'Subject', "Comment on bug 1", owner=sample_person)
        self.bug_one_another_notification = MockBugNotification(
            message=msg, bug=MockBug(1, sample_person),
            is_comment=True, date_emailed=None)

        # A comment notification for bug one which raises an exception.
        msg = getUtility(IMessageSet).fromText(
            'Subject', "Comment on bug 1", owner=sample_person)
        self.bug_one_exception_notification = MockBugNotification(
            message=msg, bug=ExceptionBug(1, sample_person),
            is_comment=True, date_emailed=None)

        # A comment notification for bug one which raises a DB exception.
        msg = getUtility(IMessageSet).fromText(
            'Subject', "Comment on bug 1", owner=sample_person)
        self.bug_one_dbexception_notification = MockBugNotification(
            message=msg, bug=DBExceptionBug(1, sample_person),
            is_comment=True, date_emailed=None)

        # We need to commit the transaction, since the error handling
        # will abort the current transaction.
        commit()

    def _getAndCheckSentNotifications(self, notifications_to_send):
        """Return the notifications that were successfully sent.

        It calls get_email_notifications() with the supplied
        notifications and return the ones that were actually sent. It
        also checks that the notifications got sent to the correct
        addresses.
        """
        email_notifications = get_email_notifications(notifications_to_send)
        to_addresses = set()
        sent_notifications = []
        for notifications, messages in email_notifications:
            for message in messages:
                to_addresses.add(message['to'])
            recipients = {}
            for notification in notifications:
                for recipient in notification.recipients:
                    for address in get_contact_email_addresses(
                        recipient.person):
                        recipients[address] = recipient
            expected_to_addresses = recipients.keys()
            self.assertEqual(
                sorted(expected_to_addresses), sorted(to_addresses))
            sent_notifications += notifications
        return sent_notifications

    def test_catch_simple_exception_last(self):
        # Make sure that the first notification is sent even if the
        # last one causes an exception to be raised.
        notifications_to_send = [
            self.bug_one_notification,
            self.bug_one_exception_notification,
            ]
        sent_notifications = self._getAndCheckSentNotifications(
            notifications_to_send)
        self.assertEqual(sent_notifications, notifications_to_send)

    def test_catch_simple_exception_in_the_middle(self):
        # Make sure that the first and last notifications are sent even
        # if the middle one causes an exception to be raised.
        notifications_to_send = [
            self.bug_one_notification,
            self.bug_one_exception_notification,
            self.bug_one_another_notification,
            ]
        sent_notifications = self._getAndCheckSentNotifications(
            notifications_to_send)
        self.assertEqual(
            sent_notifications,
            notifications_to_send)

    def test_catch_db_exception_last(self):
        # Make sure that the first notification is sent even if the
        # last one causes an exception to be raised. Also make sure that
        # the current transaction is in a usable state.
        notifications_to_send = [
            self.bug_one_notification,
            self.bug_one_dbexception_notification,
            ]
        sent_notifications = self._getAndCheckSentNotifications(
            notifications_to_send)
        self.assertEqual(sent_notifications, notifications_to_send)

        # The transaction should have been rolled back and restarted
        # properly, so getting something from the database shouldn't
        # cause any errors.
        bug_four = getUtility(IBugSet).get(4)
        self.assertEqual(bug_four.id, 4)

    def test_catch_db_exception_in_the_middle(self):
        # Make sure that the first and last notifications are sent even
        # if the middle one causes an exception to be raised. Also make
        # sure that the current transaction is in a usable state.
        notifications_to_send = [
            self.bug_one_notification,
            self.bug_one_dbexception_notification,
            self.bug_one_another_notification,
            ]
        sent_notifications = self._getAndCheckSentNotifications(
            notifications_to_send)
        self.assertEqual(
            sent_notifications, notifications_to_send)

        # The transaction should have been rolled back and restarted
        # properly, so getting something from the database shouldn't
        # cause any errors.
        bug_four = getUtility(IBugSet).get(4)
        self.assertEqual(bug_four.id, 4)


class FakeNotification:
    """Used by TestNotificationCommentBatches and TestNotificationBatches."""

    class Message(object):
        pass

    def __init__(self, is_comment=False, bug=None, owner=None):
        self.is_comment = is_comment
        self.bug = bug
        self.message = self.Message()
        self.message.owner = owner


class TestNotificationCommentBatches(unittest.TestCase):
    """Tests of `notification_comment_batches`."""

    def test_with_nothing(self):
        # Nothing is generated if an empty list is passed in.
        self.assertEquals([], list(notification_comment_batches([])))

    def test_with_one_non_comment_notification(self):
        # Given a single non-comment notification, a single tuple is
        # generated.
        notification = FakeNotification(False)
        self.assertEquals(
            [(1, notification)],
            list(notification_comment_batches([notification])))

    def test_with_one_comment_notification(self):
        # Given a single comment notification, a single tuple is generated.
        notification = FakeNotification(True)
        self.assertEquals(
            [(1, notification)],
            list(notification_comment_batches([notification])))

    def test_with_two_notifications_comment_first(self):
        # Given two notifications, one a comment, one not, and the comment
        # first, two tuples are generated, both in the same group.
        notification1 = FakeNotification(True)
        notification2 = FakeNotification(False)
        notifications = [notification1, notification2]
        self.assertEquals(
            [(1, notification1), (1, notification2)],
            list(notification_comment_batches(notifications)))

    def test_with_two_notifications_comment_last(self):
        # Given two notifications, one a comment, one not, and the comment
        # last, two tuples are generated, both in the same group.
        notification1 = FakeNotification(False)
        notification2 = FakeNotification(True)
        notifications = [notification1, notification2]
        self.assertEquals(
            [(1, notification1), (1, notification2)],
            list(notification_comment_batches(notifications)))

    def test_with_three_notifications_comment_in_middle(self):
        # Given three notifications, one a comment, two not, and the comment
        # in the middle, three tuples are generated, all in the same group.
        notification1 = FakeNotification(False)
        notification2 = FakeNotification(True)
        notification3 = FakeNotification(False)
        notifications = [notification1, notification2, notification3]
        self.assertEquals(
            [(1, notification1), (1, notification2), (1, notification3)],
            list(notification_comment_batches(notifications)))

    def test_with_more_notifications(self):
        # Given four notifications - non-comment, comment, non-comment,
        # comment - four tuples are generated. The first three notifications
        # are in the first group, the last notification is in a group on its
        # own.
        notification1 = FakeNotification(False)
        notification2 = FakeNotification(True)
        notification3 = FakeNotification(False)
        notification4 = FakeNotification(True)
        notifications = [
            notification1, notification2,
            notification3, notification4,
            ]
        self.assertEquals(
            [(1, notification1), (1, notification2),
             (1, notification3), (2, notification4)],
            list(notification_comment_batches(notifications)))


class TestNotificationBatches(unittest.TestCase):
    """Tests of `notification_batches`."""

    def test_with_nothing(self):
        # Nothing is generated if an empty list is passed in.
        self.assertEquals([], list(notification_batches([])))

    def test_with_one_non_comment_notification(self):
        # Given a single non-comment notification, a single batch is
        # generated.
        notification = FakeNotification(False)
        self.assertEquals(
            [[notification]],
            list(notification_batches([notification])))

    def test_with_one_comment_notification(self):
        # Given a single comment notification, a single batch is generated.
        notification = FakeNotification(True)
        self.assertEquals(
            [[notification]],
            list(notification_batches([notification])))

    def test_with_two_notifications_comment_first(self):
        # Given two similar notifications, one a comment, one not, and the
        # comment first, a single batch is generated.
        notification1 = FakeNotification(True)
        notification2 = FakeNotification(False)
        notifications = [notification1, notification2]
        self.assertEquals(
            [[notification1, notification2]],
            list(notification_batches(notifications)))

    def test_with_two_notifications_comment_last(self):
        # Given two similar notifications, one a comment, one not, and the
        # comment last, a single batch is generated.
        notification1 = FakeNotification(False)
        notification2 = FakeNotification(True)
        notifications = [notification1, notification2]
        self.assertEquals(
            [[notification1, notification2]],
            list(notification_batches(notifications)))

    def test_with_three_notifications_comment_in_middle(self):
        # Given three similar notifications, one a comment, two not, and the
        # comment in the middle, one batch is generated.
        notification1 = FakeNotification(False)
        notification2 = FakeNotification(True)
        notification3 = FakeNotification(False)
        notifications = [notification1, notification2, notification3]
        self.assertEquals(
            [[notification1, notification2, notification3]],
            list(notification_batches(notifications)))

    def test_with_more_notifications(self):
        # Given four similar notifications - non-comment, comment,
        # non-comment, comment - two batches are generated. The first three
        # notifications are in the first batch.
        notification1 = FakeNotification(False)
        notification2 = FakeNotification(True)
        notification3 = FakeNotification(False)
        notification4 = FakeNotification(True)
        notifications = [
            notification1, notification2,
            notification3, notification4,
            ]
        self.assertEquals(
            [[notification1, notification2, notification3], [notification4]],
            list(notification_batches(notifications)))

    def test_notifications_for_same_bug(self):
        # Batches are grouped by bug.
        notifications = [FakeNotification(bug=1) for number in range(5)]
        observed = list(notification_batches(notifications))
        self.assertEquals([notifications], observed)

    def test_notifications_for_different_bugs(self):
        # Batches are grouped by bug.
        notifications = [FakeNotification(bug=number) for number in range(5)]
        expected = [[notification] for notification in notifications]
        observed = list(notification_batches(notifications))
        self.assertEquals(expected, observed)

    def test_notifications_for_same_owner(self):
        # Batches are grouped by owner.
        notifications = [FakeNotification(owner=1) for number in range(5)]
        observed = list(notification_batches(notifications))
        self.assertEquals([notifications], observed)

    def test_notifications_for_different_owners(self):
        # Batches are grouped by owner.
        notifications = [
            FakeNotification(owner=number) for number in range(5)]
        expected = [[notification] for notification in notifications]
        observed = list(notification_batches(notifications))
        self.assertEquals(expected, observed)

    def test_notifications_with_mixed_bugs_and_owners(self):
        # Batches are grouped by bug and owner.
        notifications = [
            FakeNotification(bug=1, owner=1),
            FakeNotification(bug=1, owner=2),
            FakeNotification(bug=2, owner=2),
            FakeNotification(bug=2, owner=1),
            ]
        expected = [[notification] for notification in notifications]
        observed = list(notification_batches(notifications))
        self.assertEquals(expected, observed)

    def test_notifications_with_mixed_bugs_and_owners_2(self):
        # Batches are grouped by bug and owner.
        notifications = [
            FakeNotification(bug=1, owner=1),
            FakeNotification(bug=1, owner=1),
            FakeNotification(bug=2, owner=2),
            FakeNotification(bug=2, owner=2),
            ]
        expected = [notifications[0:2], notifications[2:4]]
        observed = list(notification_batches(notifications))
        self.assertEquals(expected, observed)

    def test_notifications_with_mixed_bugs_owners_and_comments(self):
        # Batches are grouped by bug, owner and comments.
        notifications = [
            FakeNotification(is_comment=False, bug=1, owner=1),
            FakeNotification(is_comment=False, bug=1, owner=1),
            FakeNotification(is_comment=True, bug=1, owner=1),
            FakeNotification(is_comment=False, bug=1, owner=2),
            ]
        expected = [notifications[0:3], notifications[3:4]]
        observed = list(notification_batches(notifications))
        self.assertEquals(expected, observed)
