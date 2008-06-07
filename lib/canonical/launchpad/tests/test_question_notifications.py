# Copyright 2007 Canonical Ltd.  All rights reserved.

""" Unit-tests for the Answer Tracker Mail Notifications. """

__metaclass__ = type

from unittest import TestCase, TestLoader

from canonical.launchpad.mailnotification import (
    QuestionModifiedDefaultNotification)


class TestQuestionModifiedNotification(QuestionModifiedDefaultNotification):
    """Subclass that do not send emails and with simpler initialization.

    Since notifications are handlers that accomplish their action on
    initialization, override the relevant method to make them easier to test.
    """

    def initialize(self):
        """Leave the fixture to initialize the notification properly."""
        self.new_message = None

    def shouldNotify(self):
        """Do not send emails!"""
        return False


class StubQuestion:
    """Question with a only an id and title attributes."""

    def __init__(self, id=1, title="Question title"):
        self.id = id
        self.title = title


class StubQuestionMessage:
    """Question message with only a subject attribute."""

    def __init__(self, subject='Message subject'):
        self.subject = subject


class QuestionModifiedDefaultNotificationTestCase(TestCase):
    """Test cases for mail notifications about modified questions."""

    def setUp(self):
        """Create a notification with a fake question."""
        self.notification = TestQuestionModifiedNotification(
            StubQuestion(), object())

    def test_getSubject_no_new_message(self):
        """Test getSubject() when there is no message added to the question."""
        self.assertEquals(
            '[Question #1]: Question title', self.notification.getSubject())

    def test_getSubject_new_message(self):
        """Test getSubject() when there is a new message."""
        self.notification.new_message = StubQuestionMessage()
        self.assertEquals(
            '[Question #1]: Message subject',
            self.notification.getSubject())

    def test_getSubject_new_message_with_reply_prefix(self):
        """Test getSubject() when there is a new message with a reply prefix."""
        self.notification.new_message = StubQuestionMessage(
            'RE: Message subject')
        self.assertEquals('RE: [Question #1]: Message subject',
            self.notification.getSubject())

        self.notification.new_message.subject = 'Re: Message subject'
        self.assertEquals('Re: [Question #1]: Message subject',
            self.notification.getSubject())

        self.notification.new_message.subject = 're: Message subject'
        self.assertEquals('re: [Question #1]: Message subject',
            self.notification.getSubject())

    def test_getSubject_with_existing_prefix(self):
        """Test getSubject() when there is already a [Question #xx] prefix."""
        self.notification.new_message = StubQuestionMessage(
            '[Question #1]: Question title')
        self.assertEquals('[Question #1]: Question title',
            self.notification.getSubject())

        self.notification.new_message.subject = (
            'Re: [Question #1]: Message subject')
        self.assertEquals(
            'Re: [Question #1]: Message subject',
            self.notification.getSubject())

    def test_getSubject_old_prefix(self):
        """Test that getSubject() with an old [Support #dd] prefix."""
        self.notification.new_message = StubQuestionMessage(
            'Re: [Support #1]: Message subject')
        self.assertEquals(
            'Re: [Question #1]: Message subject',
            self.notification.getSubject())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)


