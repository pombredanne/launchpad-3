# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Branch-related mailings"""

from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.mail.branch import (
    BranchMailer,
    RecipientReason,
    )
from lp.code.model.branch import Branch
from lp.code.model.gitref import GitRef
from lp.services.config import config
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import ZopelessDatabaseLayer


class TestRecipientReasonMixin:
    """Test the RecipientReason class."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Need to set merge_target.date_last_modified.
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def test_forBranchSubscriber(self):
        """Test values when created from a branch subscription."""
        merge_proposal, subscription = self.makeProposalWithSubscription()
        subscriber = subscription.person
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forBranchSubscriber(
            subscription, merge_proposal.merge_source, subscriber, '',
            merge_proposal)
        self.assertEqual(subscriber, reason.subscriber)
        self.assertEqual(subscriber, reason.recipient)
        self.assertEqual(merge_proposal.merge_source, reason.branch)

    def makeReviewerAndSubscriber(self):
        """Return a tuple of vote_reference, subscriber."""
        merge_proposal, subscription = self.makeProposalWithSubscription()
        subscriber = subscription.person
        login_person(merge_proposal.registrant)
        vote_reference = merge_proposal.nominateReviewer(
            subscriber, subscriber)
        return merge_proposal, vote_reference, subscriber

    def test_forReviewer(self):
        """Test values when created from a branch subscription."""
        merge_proposal, vote_reference, subscriber = (
            self.makeReviewerAndSubscriber())
        pending_review = vote_reference.comment is None
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forReviewer(
            merge_proposal, pending_review, subscriber)
        self.assertEqual(subscriber, reason.subscriber)
        self.assertEqual(subscriber, reason.recipient)
        self.assertEqual(
            vote_reference.branch_merge_proposal.merge_source, reason.branch)

    def test_forReview_individual_pending(self):
        bmp = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson(name='eric')
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forReviewer(bmp, True, reviewer)
        self.assertEqual('Reviewer', reason.mail_header)
        self.assertEqual(
            'You are requested to review the proposed merge of %s into %s.'
            % (bmp.merge_source.identity, bmp.merge_target.identity),
            reason.getReason())

    def test_forReview_individual_in_progress(self):
        bmp = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson(name='eric')
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forReviewer(bmp, False, reviewer)
        self.assertEqual('Reviewer', reason.mail_header)
        self.assertEqual(
            'You are reviewing the proposed merge of %s into %s.'
            % (bmp.merge_source.identity, bmp.merge_target.identity),
            reason.getReason())

    def test_forReview_team_pending(self):
        bmp = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makeTeam(name='vikings')
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forReviewer(bmp, True, reviewer)
        self.assertEqual('Reviewer @vikings', reason.mail_header)
        self.assertEqual(
            'Your team Vikings is requested to review the proposed merge'
            ' of %s into %s.'
            % (bmp.merge_source.identity, bmp.merge_target.identity),
            reason.getReason())

    def test_getReasonPerson(self):
        """Ensure the correct reason is generated for individuals."""
        merge_proposal, subscription = self.makeProposalWithSubscription()
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forBranchSubscriber(
            subscription, merge_proposal.merge_source, subscription.person, '',
            merge_proposal)
        self.assertEqual(
            'You are subscribed to branch %s.'
            % merge_proposal.merge_source.identity, reason.getReason())

    def test_getReasonTeam(self):
        """Ensure the correct reason is generated for teams."""
        team_member = self.factory.makePerson(
            displayname='Foo Bar', email='foo@bar.com')
        team = self.factory.makeTeam(team_member, displayname='Qux')
        bmp, subscription = self.makeProposalWithSubscription(team)
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forBranchSubscriber(
            subscription, bmp.merge_source, team_member, '', bmp)
        self.assertEqual(
            'Your team Qux is subscribed to branch %s.'
            % bmp.merge_source.identity, reason.getReason())


class TestRecipientReasonBzr(TestRecipientReasonMixin, TestCaseWithFactory):
    """Test RecipientReason for Bazaar branches."""

    def makeProposalWithSubscription(self, subscriber=None):
        """Test fixture."""
        if subscriber is None:
            subscriber = self.factory.makePerson()
        source_branch = self.factory.makeProductBranch(title='foo')
        target_branch = self.factory.makeProductBranch(
            product=source_branch.product, title='bar')
        merge_proposal = source_branch.addLandingTarget(
            source_branch.owner, target_branch)
        subscription = merge_proposal.merge_source.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL, subscriber)
        return merge_proposal, subscription

    def test_usesBranchIdentityCache(self):
        """Ensure that the cache is used for branches if provided."""
        branch = self.factory.makeAnyBranch()
        subscription = branch.getSubscription(branch.owner)
        branch_cache = {branch: 'lp://fake'}

        def blowup(self):
            raise AssertionError('boom')
        patched = Branch.identity
        Branch.identity = property(blowup)

        def cleanup():
            Branch.identity = patched
        self.addCleanup(cleanup)
        self.assertRaises(AssertionError, getattr, branch, 'identity')
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forBranchSubscriber(
            subscription, branch, subscription.person, '',
            branch_identity_cache=branch_cache)
        self.assertEqual(
            'You are subscribed to branch lp://fake.',
            reason.getReason())


class TestRecipientReasonGit(TestRecipientReasonMixin, TestCaseWithFactory):
    """Test RecipientReason for Git references."""

    def makeProposalWithSubscription(self, subscriber=None):
        """Test fixture."""
        if subscriber is None:
            subscriber = self.factory.makePerson()
        source_repository = self.factory.makeGitRepository()
        [source_ref] = self.factory.makeGitRefs(repository=source_repository)
        target_repository = self.factory.makeGitRepository(
            target=source_repository.target)
        [target_ref] = self.factory.makeGitRefs(repository=target_repository)
        merge_proposal = source_ref.addLandingTarget(
            source_repository.owner, target_ref)
        subscription = merge_proposal.merge_source.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL, subscriber)
        return merge_proposal, subscription

    def test_usesBranchIdentityCache(self):
        """Ensure that the cache is used for Git references if provided."""
        [ref] = self.factory.makeGitRefs()
        subscription = ref.getSubscription(ref.owner)
        branch_cache = {ref: 'fake:master'}

        def blowup(self):
            raise AssertionError('boom')
        patched = GitRef.identity
        GitRef.identity = property(blowup)

        def cleanup():
            GitRef.identity = patched
        self.addCleanup(cleanup)
        self.assertRaises(AssertionError, getattr, ref, 'identity')
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        reason = RecipientReason.forBranchSubscriber(
            subscription, ref, subscription.person, '',
            branch_identity_cache=branch_cache)
        self.assertEqual(
            'You are subscribed to branch fake:master.',
            reason.getReason())


class TestBranchMailerHeadersMixin:
    """Check the headers are correct."""

    layer = ZopelessDatabaseLayer

    def test_branch_modified(self):
        # Test the email headers for a branch modified email.
        bob = self.factory.makePerson(email='bob@example.com')
        branch = self.makeBranch(owner=bob)
        branch.getSubscription(bob).notification_level = (
            BranchSubscriptionNotificationLevel.FULL)
        switch_dbuser(config.IBranchModifiedMailJobSource.dbuser)
        mailer = BranchMailer.forBranchModified(branch, branch.owner, None)
        mailer.message_id = '<foobar-example-com>'
        ctrl = mailer.generateEmail('bob@example.com', branch.owner)
        self.assertEqual(
            {'X-Launchpad-Branch': branch.unique_name,
             'X-Launchpad-Message-Rationale': 'Subscriber',
             'X-Launchpad-Notification-Type': 'branch-updated',
             'X-Launchpad-Project': self.getBranchProjectName(branch),
             'Message-Id': '<foobar-example-com>'},
            ctrl.headers)

    def test_branch_revision(self):
        # Test the email headers for new revision email.
        bob = self.factory.makePerson(email='bob@example.com')
        branch = self.makeBranch(owner=bob)
        branch.getSubscription(bob).notification_level = (
            BranchSubscriptionNotificationLevel.FULL)
        switch_dbuser(config.IRevisionsAddedJobSource.dbuser)
        mailer = BranchMailer.forRevision(
            branch, 'from@example.com', contents='', diff=None, subject='',
            revno=1)
        mailer.message_id = '<foobar-example-com>'
        ctrl = mailer.generateEmail('bob@example.com', branch.owner)
        self.assertEqual(
            {'X-Launchpad-Branch': branch.unique_name,
             'X-Launchpad-Message-Rationale': 'Subscriber',
             'X-Launchpad-Notification-Type': 'branch-revision',
             'X-Launchpad-Branch-Revision-Number': '1',
             'X-Launchpad-Project': self.getBranchProjectName(branch),
             'Message-Id': '<foobar-example-com>'},
            ctrl.headers)


class TestBranchMailerHeadersBzr(
    TestBranchMailerHeadersMixin, TestCaseWithFactory):
    """Check the headers are correct for Branch email."""

    def makeBranch(self, owner):
        return self.factory.makeProductBranch(owner=owner)

    def getBranchProjectName(self, branch):
        return branch.product.name


class TestBranchMailerHeadersGit(
    TestBranchMailerHeadersMixin, TestCaseWithFactory):
    """Check the headers are correct for GitRef email."""

    def makeBranch(self, owner):
        repository = self.factory.makeGitRepository(owner=owner)
        return self.factory.makeGitRefs(repository=repository)[0]

    def getBranchProjectName(self, branch):
        return branch.target.name


class TestBranchMailerDiffMixin:
    """Check the diff is an attachment."""

    layer = ZopelessDatabaseLayer

    def makeBobMailController(self, diff=None,
                              max_lines=BranchSubscriptionDiffSize.WHOLEDIFF):
        bob = self.factory.makePerson(email='bob@example.com')
        branch = self.makeBranch(owner=bob)
        subscription = branch.getSubscription(bob)
        subscription.max_diff_lines = max_lines
        subscription.notification_level = (
            BranchSubscriptionNotificationLevel.FULL)
        switch_dbuser(config.IRevisionsAddedJobSource.dbuser)
        mailer = BranchMailer.forRevision(
            branch, 'from@example.com', contents='', diff=diff, subject='',
            revno=1)
        return mailer.generateEmail('bob@example.com', branch.owner)

    def test_generateEmail_with_no_diff(self):
        """When there is no diff, no attachment should be included."""
        ctrl = self.makeBobMailController()
        self.assertEqual([], ctrl.attachments)
        self.assertNotIn('larger than your specified limit', ctrl.body)

    def test_generateEmail_with_diff(self):
        """When there is a diff, it should be an attachment, not inline."""
        ctrl = self.makeBobMailController(diff=u'hello \u03A3')
        self.assertEqual(1, len(ctrl.attachments))
        diff = ctrl.attachments[0]
        self.assertEqual('hello \xce\xa3', diff.get_payload(decode=True))
        self.assertEqual('text/x-diff; charset="utf-8"', diff['Content-type'])
        self.assertEqual('inline; filename="revision-diff.txt"',
                         diff['Content-disposition'])
        self.assertNotIn('hello', ctrl.body)
        self.assertNotIn('larger than your specified limit', ctrl.body)

    def test_generateEmail_with_oversize_diff(self):
        """When the diff is oversize, don't attach, add reason."""
        ctrl = self.makeBobMailController(diff='hello\n' * 5000,
            max_lines=BranchSubscriptionDiffSize.FIVEKLINES)
        self.assertEqual([], ctrl.attachments)
        self.assertIn('The size of the diff (5001 lines) is larger than your'
            ' specified limit of 5000 lines', ctrl.body)

    def test_generateEmail_with_subscription_no_diff(self):
        """When subscription forbids diffs, don't add reason."""
        ctrl = self.makeBobMailController(diff='hello\n',
            max_lines=BranchSubscriptionDiffSize.NODIFF)
        self.assertEqual([], ctrl.attachments)
        self.assertNotIn('larger than your specified limit', ctrl.body)


class TestBranchMailerDiffBzr(TestBranchMailerDiffMixin, TestCaseWithFactory):
    """Check the diff is an attachment for Branch email."""

    def makeBranch(self, owner):
        return self.factory.makeProductBranch(owner=owner)


class TestBranchMailerDiffGit(TestBranchMailerDiffMixin, TestCaseWithFactory):
    """Check the diff is an attachment for GitRef email."""

    def makeBranch(self, owner):
        repository = self.factory.makeGitRepository(owner=owner)
        return self.factory.makeGitRefs(repository=repository)[0]


class TestBranchMailerSubjectMixin:
    """The subject for a BranchMailer is returned verbatim."""

    layer = ZopelessDatabaseLayer

    def test_subject(self):
        # No string interpolation should occur on the subject.
        branch = self.makeBranch()
        # Subscribe the owner to get revision email.
        branch.getSubscription(branch.owner).notification_level = (
            BranchSubscriptionNotificationLevel.FULL)
        switch_dbuser(config.IRevisionsAddedJobSource.dbuser)
        mailer = BranchMailer.forRevision(
            branch, 'test@example.com', 'content', 'diff', 'Testing %j foo',
            revno=1)
        owner = branch.owner
        self.assertEqual(
            'Testing %j foo',
            mailer._getSubject(owner.preferredemail.email, owner))


class TestBranchMailerSubjectBzr(
    TestBranchMailerSubjectMixin, TestCaseWithFactory):
    """The subject for a BranchMailer is returned verbatim for Branch."""

    def makeBranch(self):
        return self.factory.makeAnyBranch()


class TestBranchMailerSubjectGit(
    TestBranchMailerSubjectMixin, TestCaseWithFactory):
    """The subject for a BranchMailer is returned verbatim for GitRef."""

    def makeBranch(self):
        return self.factory.makeGitRefs()[0]
