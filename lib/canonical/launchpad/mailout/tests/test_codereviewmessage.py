# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test CodeReviewMessage emailing functionality."""

from unittest import TestLoader

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel,
    EmailAddressStatus)
from canonical.launchpad.mailout.codereviewmessage import (
    CodeReviewMessageMailer)
from canonical.launchpad.testing import TestCaseWithFactory


class TestCodeReviewMessage(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Prepare test fixtures."""
        TestCaseWithFactory.setUp(self, 'foo.bar@canonical.com')

    def makeMessageAndSubscriber(self, notification_level=None):
        """Return a message and a subscriber."""
        sender = self.factory.makePerson(
            displayname='Foo Bar', email='foo.bar@example.com',
            email_address_status=EmailAddressStatus.VALIDATED)
        code_message = self.factory.makeCodeReviewMessage(sender)
        subscriber = self.factory.makePerson(
            displayname='Baz Qux', email='baz.qux@example.com',
            email_address_status=EmailAddressStatus.VALIDATED)
        if notification_level is None:
            notification_level = CodeReviewNotificationLevel.FULL
        code_message.branch_merge_proposal.source_branch.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            notification_level)
        return code_message, subscriber

    def makeMailer(self):
        """Return a CodeReviewMessageMailer and the sole subscriber."""
        code_message, subscriber = self.makeMessageAndSubscriber()
        return CodeReviewMessageMailer.forCreation(code_message), subscriber

    def test_forCreation(self):
        """Ensure that forCreation produces a mailer with expected values."""
        code_message, subscriber = self.makeMessageAndSubscriber()
        mailer = CodeReviewMessageMailer.forCreation(code_message)
        self.assertEqual(code_message.message.subject,
                         mailer._subject_template)
        self.assertEqual(set([subscriber]),
                         mailer._recipients.getRecipientPersons())
        self.assertEqual(
            code_message.branch_merge_proposal, mailer.merge_proposal)
        self.assertEqual('Foo Bar <foo.bar@example.com>', mailer.from_address)
        self.assertEqual(code_message, mailer.code_review_message)

    def test_forCreationStatusSubscriber(self):
        """Ensure that subscriptions with STATUS aren't used."""
        code_message, subscriber = self.makeMessageAndSubscriber(
            CodeReviewNotificationLevel.STATUS)
        mailer = CodeReviewMessageMailer.forCreation(code_message)
        self.assertEqual(set(),
                         mailer._recipients.getRecipientPersons())

    def test_forCreationStatusNoEmail(self):
        """Ensure that subscriptions with NOEMAIL aren't used."""
        code_message, subscriber = self.makeMessageAndSubscriber(
            CodeReviewNotificationLevel.NOEMAIL)
        mailer = CodeReviewMessageMailer.forCreation(code_message)
        self.assertEqual(set(),
                         mailer._recipients.getRecipientPersons())

    def test_getReplyAddress(self):
        mailer, subscriber = self.makeMailer()
        merge_proposal = mailer.code_review_message.branch_merge_proposal
        expected = 'mp+%d@code.launchpad.dev' % merge_proposal.id
        self.assertEqual(expected, mailer._getReplyToAddress())

    def test_generateEmail(self):
        """Ensure mailer's generateEmail method prduces expected values."""
        mailer, subscriber = self.makeMailer()
        headers, subject, body = mailer.generateEmail(subscriber)
        message = mailer.code_review_message.message
        self.assertEqual(subject, message.subject)
        self.assertEqual(body.splitlines()[:-2],
                         message.text_contents.splitlines())
        source_branch = mailer.merge_proposal.source_branch
        branch_name = source_branch.displayname
        self.assertEqual(body.splitlines()[-2:],
            ['--', 'You are subscribed to branch %s.' % branch_name])
        rationale = mailer._recipients.getReason('baz.qux@example.com')[1]
        expected = {'X-Launchpad-Branch': source_branch.unique_name,
                    'X-Launchpad-Message-Rationale': rationale,
                    'Message-Id': message.rfc822msgid,
                    'Reply-To': mailer._getReplyToAddress()}
        for header, value in expected.items():
            self.assertEqual(headers[header], value)
        self.assertEqual(expected, headers)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
