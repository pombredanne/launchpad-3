# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

""" Unit-tests for the Answer Tracker Mail Notifications. """

__metaclass__ = type

from unittest import TestCase

from zope.interface import implements

from lp.answers.notification import (
    QuestionAddedNotification,
    QuestionModifiedDefaultNotification,
    )
from lp.registry.interfaces.person import IPerson


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
        self.owner = FakeUser()


class StubQuestionMessage:
    """Question message with only a subject attribute."""

    def __init__(self, subject='Message subject'):
        self.subject = subject


class FakeUser:
    """A fake user."""
    implements(IPerson)


class FakeEvent:
    """A fake event."""
    user = FakeUser()


class QuestionModifiedDefaultNotificationTestCase(TestCase):
    """Test cases for mail notifications about modified questions."""

    def setUp(self):
        """Create a notification with a fake question."""
        self.notification = TestQuestionModifiedNotification(
            StubQuestion(), FakeEvent())

    def test_buildBody_with_separator(self):
        # A body with a separator is preserved.
        formatted_body = self.notification.buildBody(
            "body\n-- ", "rationale")
        self.assertEqual(
            "body\n-- \nrationale", formatted_body)

    def test_buildBody_without_separator(self):
        # A separator will added to body if one is not present.
        formatted_body = self.notification.buildBody(
            "body -- mdash", "rationale")
        self.assertEqual(
            "body -- mdash\n-- \nrationale", formatted_body)

    def test_getSubject_no_new_message(self):
        """getSubject() when there is no message added to the question."""
        self.assertEquals(
            '[Question #1]: Question title', self.notification.getSubject())

    def test_getSubject_new_message(self):
        """Test getSubject() when there is a new message."""
        self.notification.new_message = StubQuestionMessage()
        self.assertEquals(
            '[Question #1]: Message subject',
            self.notification.getSubject())

    def test_getSubject_new_message_with_reply_prefix(self):
        """getSubject() when there is a new message with a reply prefix."""
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

    def test_user_is_event_user(self):
        """The notification user is always the event user."""
        question = StubQuestion()
        event = FakeEvent()
        notification = TestQuestionModifiedNotification(question, event)
        self.assertEqual(event.user, notification.user)
        self.assertNotEqual(question.owner, notification.user)


class TestQuestionAddedNotification(QuestionAddedNotification):
    """A subclass that does not send emails."""

    def shouldNotify(self):
        return False


class QuestionCreatedTestCase(TestCase):
    """Test cases for mail notifications about created questions."""

    def test_user_is_question_owner(self):
        """The notification user is always the question owner."""
        question = StubQuestion()
        event = FakeEvent()
        notification = TestQuestionAddedNotification(question, event)
        self.assertEqual(question.owner, notification.user)
        self.assertNotEqual(event.user, notification.user)
