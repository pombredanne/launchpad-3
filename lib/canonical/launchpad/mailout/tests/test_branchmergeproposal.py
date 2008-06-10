# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeProposal mailings"""

from unittest import TestLoader, TestCase

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel,
    EmailAddressStatus)
from canonical.launchpad.mailout.branchmergeproposal import (
    BMPMailer, send_merge_proposal_modified_notifications)
from canonical.launchpad.tests.mail_helpers import pop_notifications
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.testing import LaunchpadObjectFactory


class TestMergeProposalMailing(TestCase):
    """Test that reasonable mailings are generated"""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def makeProposalWithSubscriber(self):
        registrant = self.factory.makePerson(
            displayname='Baz Qux', email='baz.qux@example.com',
            email_address_status=EmailAddressStatus.VALIDATED)
        bmp = self.factory.makeBranchMergeProposal(registrant=registrant)
        subscriber = self.factory.makePerson(displayname='Baz Quxx',
            email='baz.quxx@example.com',
            email_address_status=EmailAddressStatus.VALIDATED)
        bmp.source_branch.subscribe(subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        bmp.source_branch.title = 'foo'
        bmp.target_branch.title = 'bar'
        return bmp, subscriber

    def test_generateCreationEmail(self):
        """Ensure that the contents of the mail are as expected"""
        bmp, subscriber = self.makeProposalWithSubscriber()
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        headers, subject, body = mailer.generateEmail(subscriber)
        self.assertEqual("""\
Baz Qux has proposed merging foo into bar.

--
%s
%s
""" % (canonical_url(bmp), mailer.getReason(subscriber)), body)
        self.assertEqual('Merge of foo into bar proposed', subject)
        self.assertEqual(
            {'X-Launchpad-Branch': bmp.source_branch.unique_name,
             'X-Launchpad-Message-Rationale': 'Subscriber'},
            headers)
        self.assertEqual('Baz Qux <baz.qux@example.com>', mailer.from_address)
        mailer.sendAll()

    def test_getReasonPerson(self):
        """Ensure the correct reason is generated for individuals."""
        bmp, subscriber = self.makeProposalWithSubscriber()
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        self.assertEqual('You are subscribed to branch foo.',
            mailer.getReason(subscriber))

    def test_getReasonTeam(self):
        """Ensure the correct reason is generated for teams."""
        bmp, subscriber = self.makeProposalWithSubscriber()
        team_member = self.factory.makePerson(
            displayname='Foo Bar', email='foo@bar.com', password='password')
        team = self.factory.makeTeam(team_member, displayname='Qux')
        bmp.source_branch.subscribe(team,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        self.assertEqual('Your team Qux is subscribed to branch foo.',
            mailer.getReason(team_member))
        mailer._recipients._emailToPerson[
            subscriber.preferredemail.email] = team
        try:
            mailer.getReason(subscriber)
        except AssertionError, e:
            self.assertEqual(
                'Baz Quxx does not participate in team Qux.', str(e))
        else:
            self.fail('Did not detect bogus team recipient.')

    def test_forModificationNoModification(self):
        """Ensure None is returned if no change has been made."""
        merge_proposal, person = self.makeProposalWithSubscriber()
        old_merge_proposal = BranchMergeProposalDelta.snapshot(merge_proposal)
        self.assertEqual(None, BMPMailer.forModification(
            old_merge_proposal, merge_proposal, merge_proposal.registrant))

    def makeMergeProposalMailerModification(self):
        """Fixture method providing a mailer for a modified merge proposal"""
        merge_proposal, subscriber = self.makeProposalWithSubscriber()
        old_merge_proposal = BranchMergeProposalDelta.snapshot(merge_proposal)
        merge_proposal.requestReview()
        merge_proposal.commit_message = 'new commit message'
        mailer = BMPMailer.forModification(
            old_merge_proposal, merge_proposal, merge_proposal.registrant)
        return mailer, subscriber

    def test_forModificationWithModificationDelta(self):
        """Ensure the right delta is filled out if there is a change."""
        mailer, subscriber = self.makeMergeProposalMailerModification()
        self.assertEqual('new commit message',
            mailer.delta.commit_message)

    def test_forModificationWithModificationTextDelta(self):
        """Ensure the right delta is filled out if there is a change."""
        mailer, subscriber = self.makeMergeProposalMailerModification()
        self.assertEqual(
            '    Status: Work in progress => Needs review\n\n'
            'Commit Message changed to:\n\nnew commit message',
            mailer.textDelta())

    def test_generateEmail(self):
        """Ensure that contents of modification mails are right."""
        mailer, subscriber = self.makeMergeProposalMailerModification()
        headers, subject, body = mailer.generateEmail(subscriber)
        self.assertEqual('Proposed merge of foo into bar updated', subject)
        url = canonical_url(mailer.merge_proposal)
        reason = mailer.getReason(subscriber)
        self.assertEqual("""\
The proposal to merge foo into bar has been updated.

    Status: Work in progress => Needs review

Commit Message changed to:

new commit message
--
%s
%s
""" % (url, reason), body)

    def test_send_merge_proposal_modified_notifications(self):
        """Should send emails when invoked with correct parameters."""
        merge_proposal, subscriber = self.makeProposalWithSubscriber()
        snapshot = BranchMergeProposalDelta.snapshot(merge_proposal)
        merge_proposal.commit_message = 'new message'
        event = SQLObjectModifiedEvent(merge_proposal, snapshot, None)
        pop_notifications()
        send_merge_proposal_modified_notifications(merge_proposal, event)
        emails = pop_notifications()
        self.assertEqual(1, len(emails))

    def test_send_merge_proposal_modified_notifications_no_delta(self):
        """Should not send emails if no delta."""
        merge_proposal, subscriber = self.makeProposalWithSubscriber()
        snapshot = BranchMergeProposalDelta.snapshot(merge_proposal)
        event = SQLObjectModifiedEvent(merge_proposal, snapshot, None)
        pop_notifications()
        send_merge_proposal_modified_notifications(merge_proposal, event)
        emails = pop_notifications()
        self.assertEqual([], emails)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
