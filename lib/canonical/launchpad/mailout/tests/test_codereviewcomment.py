# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Test CodeReviewComment emailing functionality."""


from unittest import TestLoader

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel,
    CodeReviewVote, EmailAddressStatus)
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailout.codereviewcomment import (
    CodeReviewCommentMailer)
from canonical.launchpad.testing import TestCaseWithFactory


class TestCodeReviewComment(TestCaseWithFactory):
    """Test that comments are generated as expected."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Prepare test fixtures."""
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def makeCommentAndSubscriber(self, notification_level=None,
                                 body=None, as_reply=False, vote=None,
                                 vote_tag=None):
        """Return a comment and a subscriber."""
        sender = self.factory.makePerson(
            displayname='Sender', email='sender@example.com',
            email_address_status=EmailAddressStatus.VALIDATED)
        comment = self.factory.makeCodeReviewComment(
            sender, body=body, vote=vote, vote_tag=vote_tag)
        if as_reply:
            comment = self.factory.makeCodeReviewComment(
                sender, body=body, parent=comment)
        subscriber = self.factory.makePerson(
            displayname='Subscriber', email='subscriber@example.com',
            email_address_status=EmailAddressStatus.VALIDATED)
        if notification_level is None:
            notification_level = CodeReviewNotificationLevel.FULL
        comment.branch_merge_proposal.source_branch.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            notification_level)
        return comment, subscriber

    def makeMailer(self, as_reply=False, vote=None, vote_tag=None, body=None):
        """Return a CodeReviewCommentMailer and the sole subscriber."""
        comment, subscriber = self.makeCommentAndSubscriber(
            body=body, as_reply=as_reply, vote=vote, vote_tag=vote_tag)
        return CodeReviewCommentMailer.forCreation(comment), subscriber

    def test_forCreation(self):
        """Ensure that forCreation produces a mailer with expected values."""
        comment, subscriber = self.makeCommentAndSubscriber()
        mailer = CodeReviewCommentMailer.forCreation(comment)
        self.assertEqual(comment.message.subject,
                         mailer._subject_template)
        self.assertEqual(set([subscriber]),
                         mailer._recipients.getRecipientPersons())
        self.assertEqual(
            comment.branch_merge_proposal, mailer.merge_proposal)
        sender = comment.message.owner
        sender_address = format_address(sender.displayname,
            sender.preferredemail.email)
        self.assertEqual(sender_address, mailer.from_address)
        self.assertEqual(comment, mailer.code_review_comment)

    def test_forCreationStatusSubscriber(self):
        """Ensure that subscriptions with STATUS aren't used."""
        comment, subscriber = self.makeCommentAndSubscriber(
            CodeReviewNotificationLevel.STATUS)
        mailer = CodeReviewCommentMailer.forCreation(comment)
        self.assertEqual(set(),
                         mailer._recipients.getRecipientPersons())

    def test_forCreationStatusNoEmail(self):
        """Ensure that subscriptions with NOEMAIL aren't used."""
        comment, subscriber = self.makeCommentAndSubscriber(
            CodeReviewNotificationLevel.NOEMAIL)
        mailer = CodeReviewCommentMailer.forCreation(comment)
        self.assertEqual(set(),
                         mailer._recipients.getRecipientPersons())

    def test_getReplyAddress(self):
        """Ensure that the reply-to address is reasonable."""
        mailer, subscriber = self.makeMailer()
        merge_proposal = mailer.code_review_comment.branch_merge_proposal
        expected = 'mp+%d@code.launchpad.dev' % merge_proposal.id
        self.assertEqual(expected, mailer._getReplyToAddress())

    def test_generateEmail(self):
        """Ensure mailer's generateEmail method produces expected values."""
        mailer, subscriber = self.makeMailer(as_reply=True)
        headers, subject, body = mailer.generateEmail(subscriber)
        message = mailer.code_review_comment.message
        self.assertEqual(subject, message.subject)
        self.assertEqual(body.splitlines()[:-2],
                         message.text_contents.splitlines())
        source_branch = mailer.merge_proposal.source_branch
        branch_name = source_branch.displayname
        self.assertEqual(body.splitlines()[-2:],
            ['-- ', 'You are subscribed to branch %s.' % branch_name])
        rationale = mailer._recipients.getReason('subscriber@example.com')[1]
        expected = {'X-Launchpad-Branch': source_branch.unique_name,
                    'X-Launchpad-Message-Rationale': rationale,
                    'Message-Id': message.rfc822msgid,
                    'Reply-To': mailer._getReplyToAddress(),
                    'In-Reply-To': message.parent.rfc822msgid}
        for header, value in expected.items():
            self.assertEqual(headers[header], value)
        self.assertEqual(expected, headers)

    def test_appendToFooter(self):
        """If there is an existing footer, we append to it."""
        mailer, subscriber = self.makeMailer(
            body='Hi!\n'
            '-- \n'
            'I am a wacky guy.\n')
        branch_name = mailer.merge_proposal.source_branch.displayname
        body = mailer._getBody(subscriber)
        self.assertEqual(body.splitlines()[1:],
            ['-- ', 'I am a wacky guy.',
             'You are subscribed to branch %s.' % branch_name])

    def test_generateEmailWithVote(self):
        """Ensure that votes are displayed."""
        mailer, subscriber = self.makeMailer(
            vote=CodeReviewVote.APPROVE)
        headers, subject, body = mailer.generateEmail(subscriber)
        self.assertEqual('Vote: Approve', body.splitlines()[0])
        self.assertEqual(body.splitlines()[1:-2],
                         mailer.message.text_contents.splitlines())

    def test_generateEmailWithVoteAndTag(self):
        """Ensure that vote tags are displayed."""
        mailer, subscriber = self.makeMailer(
            vote=CodeReviewVote.APPROVE, vote_tag='DBTAG')
        headers, subject, body = mailer.generateEmail(subscriber)
        self.assertEqual('Vote: Approve DBTAG', body.splitlines()[0])
        self.assertEqual(body.splitlines()[1:-2],
                         mailer.message.text_contents.splitlines())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
