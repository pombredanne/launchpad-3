# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeProposal mailings"""

from unittest import TestLoader, TestCase

from zope.security.proxy import removeSecurityProxy

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.database import CodeReviewVoteReference
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.ftests import login, login_person
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel)
from canonical.launchpad.mailout.branchmergeproposal import (
    BMPMailer, send_merge_proposal_modified_notifications, RecipientReason)
from canonical.launchpad.tests.mail_helpers import pop_notifications
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory)


class TestMergeProposalMailing(TestCase):
    """Test that reasonable mailings are generated"""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def makeProposalWithSubscriber(self):
        registrant = self.factory.makePerson(
            displayname='Baz Qux', email='baz.qux@example.com')
        bmp = self.factory.makeBranchMergeProposal(registrant=registrant)
        subscriber = self.factory.makePerson(displayname='Baz Quxx',
            email='baz.quxx@example.com')
        bmp.source_branch.subscribe(subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        bmp.source_branch.title = 'foo'
        bmp.target_branch.title = 'bar'
        return bmp, subscriber

    def test_generateCreationEmail(self):
        """Ensure that the contents of the mail are as expected"""
        bmp, subscriber = self.makeProposalWithSubscriber()
        bmp.whiteboard = "I think this would be good."
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        reason = mailer._recipients.getReason(
            subscriber.preferredemail.email)[0]
        headers, subject, body = mailer.generateEmail(subscriber)
        self.assertEqual("""\
Baz Qux has proposed merging foo into bar.

Whiteboard:
I think this would be good.

--\x20
%s
%s
""" % (canonical_url(bmp), reason.getReason()), body)
        self.assertEqual('Proposed merge of foo into bar', subject)
        self.assertEqual(
            {'X-Launchpad-Branch': bmp.source_branch.unique_name,
             'X-Launchpad-Message-Rationale': 'Subscriber',
             'X-Launchpad-Project': bmp.source_branch.product.name,
             'Reply-To': bmp.address},
            headers)
        self.assertEqual('Baz Qux <baz.qux@example.com>', mailer.from_address)
        mailer.sendAll()

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
        reason = mailer._recipients.getReason(
            subscriber.preferredemail.email)[0].getReason()
        self.assertEqual("""\
The proposal to merge foo into bar has been updated.

    Status: Work in progress => Needs review

Commit Message changed to:

new commit message
--\x20
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
        self.assertEqual(3, len(emails),
                         'There should be three emails sent out.  One to the '
                         'explicit subscriber above, and one each to the '
                         'source branch owner and the target branch owner '
                         'who were implicitly subscribed to their branches.')

    def test_send_merge_proposal_modified_notifications_no_delta(self):
        """Should not send emails if no delta."""
        merge_proposal, subscriber = self.makeProposalWithSubscriber()
        snapshot = BranchMergeProposalDelta.snapshot(merge_proposal)
        event = SQLObjectModifiedEvent(merge_proposal, snapshot, None)
        pop_notifications()
        send_merge_proposal_modified_notifications(merge_proposal, event)
        emails = pop_notifications()
        self.assertEqual([], emails)

    def assertRecipientsMatches(self, recipients, mailer):
        """Assert that `mailer` will send to the people in `recipients`."""
        persons = zip(*(mailer._recipients.getRecipientPersons()))[1]
        self.assertEqual(set(recipients), set(persons))

    def test_forReviewRequest(self):
        """Test creating a mailer for a review request."""
        merge_proposal, subscriber_ = self.makeProposalWithSubscriber()
        candidate = self.factory.makePerson(
            displayname='Candidate', email='candidate@example.com')
        requester = self.factory.makePerson(
            displayname='Requester', email='requester@example.com')
        request = CodeReviewVoteReference(
            branch_merge_proposal=merge_proposal, reviewer=candidate,
            registrant=requester)
        request = RecipientReason.forReviewer(request, candidate)
        mailer = BMPMailer.forReviewRequest(
            request, merge_proposal, requester)
        self.assertEqual(
            'Requester <requester@example.com>', mailer.from_address)
        self.assertRecipientsMatches([candidate], mailer)


class TestRecipientReason(TestCaseWithFactory):
    """Test the RecipientReason class."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Need to set target_branch.date_last_modified.
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def makeProposalWithSubscription(self, subscriber=None):
        """Test fixture."""
        if subscriber is None:
            subscriber = self.factory.makePerson()
        source_branch = self.factory.makeBranch(title='foo')
        target_branch = self.factory.makeBranch(product=source_branch.product,
                title='bar')
        merge_proposal = source_branch.addLandingTarget(
            subscriber, target_branch)
        subscription = merge_proposal.source_branch.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        return merge_proposal, subscription

    def test_forBranchSubscriber(self):
        """Test values when created from a branch subscription."""
        merge_proposal, subscription = self.makeProposalWithSubscription()
        subscriber = subscription.person
        reason = RecipientReason.forBranchSubscriber(
            subscription, subscriber, merge_proposal, '')
        self.assertEqual(subscriber, reason.subscriber)
        self.assertEqual(subscriber, reason.recipient)
        self.assertEqual(merge_proposal.source_branch, reason.branch)

    def makeReviewerAndSubscriber(self):
        merge_proposal, subscription = self.makeProposalWithSubscription()
        subscriber = subscription.person
        login(merge_proposal.registrant.preferredemail.email)
        vote_reference = merge_proposal.nominateReviewer(
            subscriber, subscriber)
        return vote_reference, subscriber

    def test_forReviewer(self):
        """Test values when created from a branch subscription."""
        vote_reference, subscriber = self.makeReviewerAndSubscriber()
        reason = RecipientReason.forReviewer(vote_reference, subscriber)
        self.assertEqual(subscriber, reason.subscriber)
        self.assertEqual(subscriber, reason.recipient)
        self.assertEqual(
            vote_reference.branch_merge_proposal.source_branch, reason.branch)

    def test_getReasonReviewer(self):
        vote_reference, subscriber = self.makeReviewerAndSubscriber()
        reason = RecipientReason.forReviewer(vote_reference, subscriber)
        self.assertEqual(
            'You are requested to review the proposed merge of foo into bar.',
            reason.getReason())

    def test_getReasonPerson(self):
        """Ensure the correct reason is generated for individuals."""
        merge_proposal, subscription = self.makeProposalWithSubscription()
        reason = RecipientReason.forBranchSubscriber(
            subscription, subscription.person, merge_proposal, '')
        self.assertEqual('You are subscribed to branch foo.',
            reason.getReason())

    def test_getReasonTeam(self):
        """Ensure the correct reason is generated for teams."""
        team_member = self.factory.makePerson(
            displayname='Foo Bar', email='foo@bar.com')
        team = self.factory.makeTeam(team_member, displayname='Qux')
        bmp, subscription = self.makeProposalWithSubscription(team)
        reason = RecipientReason.forBranchSubscriber(
            subscription, team_member, bmp, '')
        self.assertEqual('Your team Qux is subscribed to branch foo.',
            reason.getReason())


class TestBranchMergeProposalRequestReview(TestCaseWithFactory):
    """Tests for `BranchMergeProposalRequestReviewView`."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.owner = self.factory.makePerson()
        login_person(self.owner)
        self.bmp = self.factory.makeBranchMergeProposal(registrant=self.owner)

    def makePersonWithHiddenEmail(self):
        """Make an arbitrary person with hidden email addresses."""
        person = self.factory.makePerson()
        login_person(person)
        person.hide_email_addresses = True
        login_person(self.owner)
        return person

    def test_requestReviewWithPrivateEmail(self):
        # We can request a review, even when one of the parties involved has a
        # private email address.
        candidate = self.makePersonWithHiddenEmail()
        # Request a review and prepare the mailer.
        vote_reference = self.bmp.nominateReviewer(
            candidate, self.owner, None)
        reason = RecipientReason.forReviewer(vote_reference, candidate)
        mailer = BMPMailer.forReviewRequest(reason, self.bmp, self.owner)
        # Send the mail.
        pop_notifications()
        mailer.sendAll()
        mails = pop_notifications()
        self.assertEqual(1, len(mails))
        candidate = removeSecurityProxy(candidate)
        expected_email = '%s <%s>' % (
            candidate.displayname, candidate.preferredemail.email)
        self.assertEqual(expected_email, mails[0]['To'])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
