# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeProposal mailings"""

from unittest import TestLoader, TestCase

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel,
    TeamSubscriptionPolicy)
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
        bmp = self.factory.makeBranchMergeProposal()
        bmp.registrant.displayname = 'Baz Qux'
        subscriber = self.factory.makePerson()
        subscriber.displayname = 'Baz Quxx'
        bmp.source_branch.subscribe(subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        bmp.source_branch.title = 'foo'
        bmp.target_branch.title = 'bar'
        return bmp, subscriber

    def makeTeam(self, team_member):
        team = self.factory.makePerson(displayname='Qux')
        team.teamowner = team_member
        team.subscriptionpolicy = TeamSubscriptionPolicy.OPEN
        team_member.join(team, team)
        return team

    def test_generateCreationEmail(self):
        """Ensure that the contents of the mail are as expected"""
        bmp, subscriber = self.makeProposalWithSubscriber()
        mailer = BMPMailer.forCreation(bmp)
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

    def test_getReasonPerson(self):
        """Ensure the correct reason is generated for individuals."""
        bmp, subscriber = self.makeProposalWithSubscriber()
        mailer = BMPMailer.forCreation(bmp)
        self.assertEqual('You are subscribed to branch foo.',
            mailer.getReason(subscriber))

    def test_getReasonTeam(self):
        """Ensure the correct reason is generated for teams."""
        bmp, subscriber = self.makeProposalWithSubscriber()
        team_member = self.factory.makePerson(displayname='Foo Bar')
        team = self.makeTeam(team_member)
        bmp.source_branch.subscribe(team,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        mailer = BMPMailer.forCreation(bmp)
        self.assertEqual('Your team Qux is subscribed to branch foo.',
            mailer.getReason(team_member))
        mailer.recipients[subscriber] = mailer.recipients[team_member]
        try:
            mailer.getReason(subscriber)
        except AssertionError, e:
            self.assertEqual(
                'Baz Quxx does not participate in team Qux.', str(e))
        else:
            self.fail('Did not detect bogus team recipient.')

    def test_getRealRecipientsIndirect(self):
        """Ensure getRealRecipients uses indirect memberships."""
        team_member = self.factory.makePerson(displayname='Foo Bar')
        team = self.makeTeam(team_member)
        super_team = self.makeTeam(team)
        recipients = BMPMailer.getRealRecipients(
            {super_team: 42})
        self.assertEqual([(team_member, 42)], recipients.items())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
