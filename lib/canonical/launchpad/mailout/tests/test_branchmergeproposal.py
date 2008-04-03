# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeProposal mailings"""

from unittest import TestLoader, TestCase

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel,
    EmailAddressStatus, IBranchMergeProposal)
from canonical.launchpad.mailout.branchmergeproposal import BMPMailer
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
        """Ensure an assertion is raised if no change has been made."""
        merge_proposal, person = self.makeProposalWithSubscriber()
        old_merge_proposal = BranchMergeProposalDelta.snapshot(merge_proposal)
        self.assertRaises(AssertionError, BMPMailer.forModification,
            old_merge_proposal, merge_proposal, merge_proposal.registrant)

    def makeMergeProposalMailerModification(self):
        merge_proposal, person = self.makeProposalWithSubscriber()
        old_merge_proposal = BranchMergeProposalDelta.snapshot(merge_proposal)
        merge_proposal.commit_message = 'new commit message'
        return BMPMailer.forModification(
            old_merge_proposal, merge_proposal, merge_proposal.registrant)

    def test_forModificationWithModificationDelta(self):
        """Ensure the right delta is filled out if there is a change."""
        mailer = self.makeMergeProposalMailerModification()
        self.assertEqual({'old': None, 'new': 'new commit message'},
            mailer.delta.commit_message)

    def test_forModificationWithModificationDeltaLines(self):
        """Ensure the right delta is filled out if there is a change."""
        mailer = self.makeMergeProposalMailerModification()
        self.assertEqual(
            ['    Commit Message: (not set) => new commit message'],
            mailer.deltaLines())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
