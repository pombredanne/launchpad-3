# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BranchMergeProposal mailings"""

from unittest import TestLoader
import transaction

from zope.security.proxy import removeSecurityProxy

from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)

from lp.code.model.diff import StaticDiff
from lazr.lifecycle.event import ObjectModifiedEvent
from lp.code.adapters.branch import BranchMergeProposalDelta
from lp.code.enums import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel)
from lp.code.mail.branch import RecipientReason
from lp.code.mail.branchmergeproposal import (
    BMPMailer, send_merge_proposal_modified_notifications)
from lp.code.model.branch import update_trigger_modified_fields
from lp.code.model.codereviewvote import CodeReviewVoteReference
from canonical.launchpad.webapp import canonical_url
from lp.testing import login_person, TestCaseWithFactory
from lp.testing.mail_helpers import pop_notifications


class TestMergeProposalMailing(TestCaseWithFactory):
    """Test that reasonable mailings are generated"""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestMergeProposalMailing, self).setUp('admin@canonical.com')

    def makeProposalWithSubscriber(self, diff_text=None,
                                   initial_comment=None):
        if diff_text is not None:
            review_diff = StaticDiff.acquireFromText(
                self.factory.getUniqueString('revid'),
                self.factory.getUniqueString('revid'),
                diff_text)
            transaction.commit()
        else:
            review_diff = None
        registrant = self.factory.makePerson(
            name='bazqux', displayname='Baz Qux', email='baz.qux@example.com')
        product = self.factory.makeProduct(name='super-product')
        bmp = self.factory.makeBranchMergeProposal(
            registrant=registrant, product=product, review_diff=review_diff,
            initial_comment=initial_comment)
        subscriber = self.factory.makePerson(displayname='Baz Quxx',
            email='baz.quxx@example.com')
        bmp.source_branch.subscribe(subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        bmp.source_branch.owner.name = 'bob'
        bmp.source_branch.name = 'fix-foo-for-bar'
        bmp.target_branch.owner.name = 'mary'
        bmp.target_branch.name = 'bar'
        # Call the function that is normally called through the event system
        # to auto reload the fields updated by the db triggers.
        update_trigger_modified_fields(bmp.source_branch)
        update_trigger_modified_fields(bmp.target_branch)
        return bmp, subscriber

    def test_generateCreationEmail(self):
        """Ensure that the contents of the mail are as expected"""
        bmp, subscriber = self.makeProposalWithSubscriber()
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        assert mailer.message_id is not None, 'Message-id should be set'
        mailer.message_id = '<foobar-example-com>'
        reason = mailer._recipients.getReason(
            subscriber.preferredemail.email)[0]
        bmp.root_message_id = None
        ctrl = mailer.generateEmail('baz.quxx@example.com', subscriber)
        self.assertEqual("""\
Baz Qux has proposed merging lp://dev/~bob/super-product/fix-foo-for-bar into lp://dev/~mary/super-product/bar.


--\x20
%s
%s
""" % (canonical_url(bmp), reason.getReason()), ctrl.body)
        self.assertEqual('[Merge] '
            'lp://dev/~bob/super-product/fix-foo-for-bar into '
            'lp://dev/~mary/super-product/bar', ctrl.subject)
        self.assertEqual(
            {'X-Launchpad-Branch': bmp.source_branch.unique_name,
             'X-Launchpad-Message-Rationale': 'Subscriber',
             'X-Launchpad-Notification-Type': 'code-review',
             'X-Launchpad-Project': bmp.source_branch.product.name,
             'Reply-To': bmp.address,
             'Message-Id': '<foobar-example-com>'},
            ctrl.headers)
        self.assertEqual('Baz Qux <baz.qux@example.com>', ctrl.from_addr)
        self.assertEqual([bmp.address], ctrl.to_addrs)
        mailer.sendAll()

    def test_forCreation_with_bugs(self):
        """If there are related bugs, include 'Related bugs'."""
        bmp, subscriber = self.makeProposalWithSubscriber()
        bug = self.factory.makeBug(title='I am a bug')
        bmp.source_branch.linkBug(bug, bmp.registrant)
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        ctrl = mailer.generateEmail('baz.quxx@example.com', subscriber)
        expected = (
            'Related bugs:\n'
            '  #%d I am a bug\n'
            '  %s\n' % (bug.id, canonical_url(bug))
        )
        self.assertIn(expected, ctrl.body)

    def test_forCreation_without_bugs(self):
        """If there are no related bugs, omit 'Related bugs'."""
        bmp, subscriber = self.makeProposalWithSubscriber()
        bug = self.factory.makeBug()
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        ctrl = mailer.generateEmail('baz.quxx@example.com', subscriber)
        self.assertNotIn('Related bugs:\n', ctrl.body)

    def test_to_addrs_includes_reviewers(self):
        """The addresses for the to header include requested reviewers"""
        request, requester = self.makeReviewRequest()
        bmp = request.merge_proposal
        bmp.source_branch.subscribe(
            bmp.registrant, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        ctrl = mailer.generateEmail(bmp.registrant,
                                    bmp.registrant.preferredemail.email)
        reviewer = request.recipient
        reviewer_id = mailer._format_user_address(reviewer)
        self.assertEqual(set([reviewer_id, bmp.address]),
                         set(ctrl.to_addrs))

    def test_to_addrs_excludes_team_reviewers(self):
        """Addresses for the to header exclude requested team reviewers."""
        bmp, subscriber = self.makeProposalWithSubscriber()
        team = self.factory.makeTeam(email='group@team.com')
        request = CodeReviewVoteReference(
            branch_merge_proposal=bmp, reviewer=team, registrant=subscriber)
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        ctrl = mailer.generateEmail(subscriber,
                                    subscriber.preferredemail.email)
        self.assertEqual([bmp.address], ctrl.to_addrs)

    def test_to_addrs_excludes_people_with_hidden_addresses(self):
        """The to header excludes those with hidden addresses."""
        request, requester = self.makeReviewRequest()
        request.recipient.hide_email_addresses = True
        bmp = request.merge_proposal
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        ctrl = mailer.generateEmail(request.recipient,
                                    request.recipient.preferredemail.email)
        self.assertEqual([bmp.address], ctrl.to_addrs)

    def test_RecordMessageId(self):
        """Ensure that the contents of the mail are as expected"""
        bmp, subscriber = self.makeProposalWithSubscriber()
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        mailer.message_id = '<foobar-example-com>'
        ctrl = mailer.generateEmail('baz.quxx@example.com', subscriber)
        self.assertEqual('<foobar-example-com>', ctrl.headers['Message-Id'])
        self.assertEqual('Baz Qux <baz.qux@example.com>', ctrl.from_addr)
        bmp.root_message_id = None
        pop_notifications()
        mailer.sendAll()
        for notification in pop_notifications():
            self.assertEqual('<foobar-example-com>',
                notification['Message-Id'])
        self.assertEqual('<foobar-example-com>', bmp.root_message_id)
        mailer.message_id = '<bazqux-example-com>'
        mailer.sendAll()
        self.assertEqual('<foobar-example-com>', bmp.root_message_id)

    def test_inReplyTo(self):
        """Ensure that messages are in reply to the root"""
        bmp, subscriber = self.makeProposalWithSubscriber()
        bmp.root_message_id = '<root-message-id>'
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        ctrl = mailer.generateEmail('baz.quxx@example.com', subscriber)
        self.assertEqual('<root-message-id>', ctrl.headers['In-Reply-To'])

    def test_generateEmail_attaches_diff(self):
        """A diff should be attached, with the correct metadata.

        The attached diff should be inline, should have a filename,
        and should be of type text/x-diff (or text/x-patch), with no declared
        encoding.  (The only encoding in a diff is the encoding of the input
        files, which may be inconsistent.)
        """
        bmp, subscriber = self.makeProposalWithSubscriber(
            diff_text="Fake diff")
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        ctrl = mailer.generateEmail('baz.quxx@example.com', subscriber)
        (attachment,) = ctrl.attachments
        self.assertEqual('text/x-diff', attachment['Content-Type'])
        self.assertEqual('inline; filename="review-diff.txt"',
                         attachment['Content-Disposition'])
        self.assertEqual('Fake diff', attachment.get_payload(decode=True))

    def test_generateEmail_attaches_diff_oversize_truncated(self):
        """An oversized diff will be truncated, and the receiver informed."""
        self.pushConfig("diff", max_read_size=25)
        content = "1234567890" * 10
        bmp, subscriber = self.makeProposalWithSubscriber(
            diff_text=content)
        mailer = BMPMailer.forCreation(bmp, bmp.registrant)
        ctrl = mailer.generateEmail('baz.quxx@example.com', subscriber)
        (attachment,) = ctrl.attachments
        self.assertEqual('text/x-diff', attachment['Content-Type'])
        self.assertEqual('inline; filename="review-diff.txt"',
                         attachment['Content-Disposition'])
        self.assertEqual(content[:25], attachment.get_payload(decode=True))
        warning_text = "The attached diff has been truncated due to its size."
        self.assertTrue(warning_text in ctrl.body)

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

    def test_forModificationHasMsgId(self):
        """Ensure the right delta is filled out if there is a change."""
        mailer, subscriber = self.makeMergeProposalMailerModification()
        assert mailer.message_id is not None, 'message_id not set'

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
        ctrl = mailer.generateEmail('baz.quxx@example.com', subscriber)
        self.assertEqual('[Merge] '
            'lp://dev/~bob/super-product/fix-foo-for-bar into '
            'lp://dev/~mary/super-product/bar updated', ctrl.subject)
        url = canonical_url(mailer.merge_proposal)
        reason = mailer._recipients.getReason(
            subscriber.preferredemail.email)[0].getReason()
        self.assertEqual("""\
The proposal to merge lp://dev/~bob/super-product/fix-foo-for-bar into lp://dev/~mary/super-product/bar has been updated.

    Status: Work in progress => Needs review

Commit Message changed to:

new commit message
--\x20
%s
%s
""" % (url, reason), ctrl.body)

    def test_send_merge_proposal_modified_notifications(self):
        """Should send emails when invoked with correct parameters."""
        merge_proposal, subscriber = self.makeProposalWithSubscriber()
        snapshot = BranchMergeProposalDelta.snapshot(merge_proposal)
        merge_proposal.commit_message = 'new message'
        event = ObjectModifiedEvent(merge_proposal, snapshot, None)
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
        event = ObjectModifiedEvent(merge_proposal, snapshot, None)
        pop_notifications()
        send_merge_proposal_modified_notifications(merge_proposal, event)
        emails = pop_notifications()
        self.assertEqual([], emails)

    def assertRecipientsMatches(self, recipients, mailer):
        """Assert that `mailer` will send to the people in `recipients`."""
        persons = zip(*(mailer._recipients.getRecipientPersons()))[1]
        self.assertEqual(set(recipients), set(persons))

    def makeReviewRequest(self):
        merge_proposal, subscriber_ = self.makeProposalWithSubscriber(
            diff_text="Make a diff.", initial_comment="Initial comment")
        candidate = self.factory.makePerson(
            displayname='Candidate', email='candidate@example.com')
        requester = self.factory.makePerson(
            displayname='Requester', email='requester@example.com')
        request = CodeReviewVoteReference(
            branch_merge_proposal=merge_proposal, reviewer=candidate,
            registrant=requester)
        return RecipientReason.forReviewer(request, candidate), requester

    def test_forReviewRequest(self):
        """Test creating a mailer for a review request."""
        request, requester = self.makeReviewRequest()
        mailer = BMPMailer.forReviewRequest(
            request, request.merge_proposal, requester)
        self.assertEqual(
            'Requester <requester@example.com>', mailer.from_address)
        self.assertEqual(
            request.merge_proposal.root_comment,
            mailer.comment)
        self.assertEqual(
            request.merge_proposal.review_diff,
            mailer.review_diff)
        self.assertRecipientsMatches([request.recipient], mailer)

    def test_to_addrs_for_review_request(self):
        request, requester = self.makeReviewRequest()
        mailer = BMPMailer.forReviewRequest(
            request, request.merge_proposal, requester)
        ctrl = mailer.generateEmail(request.recipient.preferredemail.email,
                                    request.recipient)
        recipient_addr = mailer._format_user_address(request.recipient)
        self.assertEqual([recipient_addr], ctrl.to_addrs)

    def test_forReviewRequestMessageId(self):
        """Test creating a mailer for a review request."""
        request, requester = self.makeReviewRequest()
        mailer = BMPMailer.forReviewRequest(
            request, request.merge_proposal, requester)
        assert mailer.message_id is not None, 'message_id not set'


class TestBranchMergeProposalRequestReview(TestCaseWithFactory):
    """Tests for `BranchMergeProposalRequestReviewView`."""

    layer = DatabaseFunctionalLayer

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
