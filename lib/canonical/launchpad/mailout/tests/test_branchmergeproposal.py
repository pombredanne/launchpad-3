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

    def test_generateCreationEmail(self):
        bmp = self.factory.makeBranchMergeProposal()
        bmp.registrant.displayname = 'Baz Qux'
        subscriber = self.factory.makePerson()
        bmp.source_branch.subscribe(subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        bmp.source_branch.title = 'foo'
        bmp.target_branch.title = 'bar'
        mailer = BMPMailer.forCreation(bmp)
        headers, subject, body = mailer.generateEmail(subscriber)
        self.assertEqual("""\
Baz Qux has proposed merging foo into bar.

--
%s

%s
""" % (canonical_url(bmp), mailer.getReason(subscriber)), body)
        self.assertEqual('Merge of foo into bar proposed', subject)

    def makeProposalWithSubscriber(self):
        bmp = self.factory.makeBranchMergeProposal()
        bmp.registrant.displayname = 'Baz Qux'
        subscriber = self.factory.makePerson()
        bmp.source_branch.subscribe(subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        bmp.source_branch.title = 'foo'
        return bmp, subscriber

    def test_getReasonPerson(self):
        bmp, subscriber = self.makeProposalWithSubscriber()
        mailer = BMPMailer.forCreation(bmp)
        self.assertEqual('You are subscribed to branch foo.',
            mailer.getReason(subscriber))

    def test_getReasonTeam(self):
        bmp, subscriber = self.makeProposalWithSubscriber()
        subscriber.displayname = 'Baz Quxx'
        team = self.factory.makePerson(displayname='Qux')
        team_member = self.factory.makePerson(displayname='Foo Bar')
        team.teamowner = team_member
        team.subscriptionpolicy = TeamSubscriptionPolicy.OPEN
        team_member.join(team)
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


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
