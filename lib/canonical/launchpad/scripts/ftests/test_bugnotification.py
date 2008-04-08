# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Tests for construction bug notification emails for sending."""

__metaclass__ = type

from datetime import datetime
import unittest

import pytz
from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.database import BugTask
from canonical.launchpad.helpers import contactEmailAddresses
from canonical.launchpad.interfaces import (
    IBug, IBugSet, IMessageSet, IPersonSet, IProductSet)
from canonical.launchpad.mailnotification import BugNotificationRecipients
from canonical.launchpad.scripts.bugnotification import (
    get_email_notifications)
from canonical.testing import LaunchpadZopelessLayer


class MockBug:
    """A bug which has only the attributes get_email_notifications() needs."""
    implements(IBug)

    duplicateof = None
    private = False
    security_related = False

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


class TestGetEmailNotificattions(unittest.TestCase):
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
        email_notifications = get_email_notifications(
            notifications_to_send, date_emailed=self.now)
        to_addresses = set()
        sent_notifications = []
        for notifications, messages in email_notifications:
            for message in messages:
                to_addresses.add(message['to'])
            recipients = {}
            for notification in notifications:
                for recipient in notification.recipients:
                    for address in contactEmailAddresses(recipient.person):
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
