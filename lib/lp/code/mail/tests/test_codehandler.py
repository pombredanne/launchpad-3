# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing the CodeHandler."""

__metaclass__ = type

from difflib import unified_diff
from textwrap import dedent

from bzrlib.branch import Branch
from bzrlib.urlutils import join as urljoin
from bzrlib.workingtree import WorkingTree
from storm.store import Store
import transaction
from zope.component import getUtility
from zope.interface import (
    directlyProvidedBy,
    directlyProvides,
    )
from zope.security.management import setSecurityPolicy
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.interaction import (
    get_current_principal,
    setupInteraction,
    )
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessAppServerLayer,
    )
from lp.code.enums import (
    BranchMergeProposalStatus,
    BranchSubscriptionNotificationLevel,
    BranchType,
    BranchVisibilityRule,
    CodeReviewNotificationLevel,
    CodeReviewVote,
    )
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.code.mail.codehandler import (
    AddReviewerEmailCommand,
    CodeEmailCommands,
    CodeHandler,
    CodeReviewEmailCommandExecutionContext,
    InvalidBranchMergeProposalAddress,
    MissingMergeDirective,
    NonLaunchpadTarget,
    UpdateStatusEmailCommand,
    VoteEmailCommand,
    )
from lp.code.model.branchmergeproposaljob import (
    BranchMergeProposalJob,
    BranchMergeProposalJobType,
    CreateMergeProposalJob,
    MergeProposalNeedsReviewEmailJob,
    )
from lp.code.model.diff import PreviewDiff
from lp.code.tests.helpers import make_merge_proposal_without_reviewers
from lp.codehosting.vfs import get_lp_server
from lp.registry.interfaces.person import IPersonSet
from lp.services.job.runner import JobRunner
from lp.services.mail.handlers import mail_handlers
from lp.services.mail.interfaces import (
    EmailProcessingError,
    IWeaklyAuthenticatedPrincipal,
    )
from lp.services.messages.model.message import MessageSet
from lp.services.osutils import override_environ
from lp.testing import (
    login,
    login_person,
    person_logged_in,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.mail_helpers import pop_notifications


class TestGetCodeEmailCommands(TestCase):
    """Test CodeEmailCommands.getCommands."""

    def test_no_message(self):
        # Null in, empty list out.
        self.assertEqual([], CodeEmailCommands.getCommands(None))

    def test_vote_command(self):
        # Check that the vote command is correctly created.
        [command] = CodeEmailCommands.getCommands(" vote approve tag me")
        self.assertIsInstance(command, VoteEmailCommand)
        self.assertEqual('vote', command.name)
        self.assertEqual(['approve', 'tag', 'me'], command.string_args)

    def test_review_as_vote_command(self):
        # Check that the vote command is correctly created.
        [command] = CodeEmailCommands.getCommands(" review approve tag me")
        self.assertIsInstance(command, VoteEmailCommand)
        self.assertEqual('review', command.name)
        self.assertEqual(['approve', 'tag', 'me'], command.string_args)

    def test_status_command(self):
        # Check that the update status command is correctly created.
        [command] = CodeEmailCommands.getCommands(" status approved")
        self.assertIsInstance(command, UpdateStatusEmailCommand)
        self.assertEqual('status', command.name)
        self.assertEqual(['approved'], command.string_args)

    def test_merge_command(self):
        # Merge is an alias for the status command.
        [command] = CodeEmailCommands.getCommands(" merge approved")
        self.assertIsInstance(command, UpdateStatusEmailCommand)
        self.assertEqual('merge', command.name)
        self.assertEqual(['approved'], command.string_args)

    def test_reviewer_command(self):
        # Check that the add review command is correctly created.
        [command] = CodeEmailCommands.getCommands(
            " reviewer test@canonical.com db")
        self.assertIsInstance(command, AddReviewerEmailCommand)
        self.assertEqual('reviewer', command.name)
        self.assertEqual(['test@canonical.com', 'db'], command.string_args)

    def test_ignored_commands(self):
        # Check that other "commands" are not created.
        self.assertEqual([], CodeEmailCommands.getCommands(
            " not-a-command\n spam"))

    def test_vote_commands_come_first(self):
        # Vote commands come before either status or reviewer commands.
        message_body = """
            status approved
            vote approve db
            """
        vote_command, status_command = CodeEmailCommands.getCommands(
            message_body)
        self.assertIsInstance(vote_command, VoteEmailCommand)
        self.assertIsInstance(status_command, UpdateStatusEmailCommand)

        message_body = """
            reviewer foo.bar
            vote reject
            """
        vote_command, reviewer_command = CodeEmailCommands.getCommands(
            message_body)

        self.assertIsInstance(vote_command, VoteEmailCommand)
        self.assertIsInstance(reviewer_command, AddReviewerEmailCommand)


class TestCodeHandler(TestCaseWithFactory):
    """Test the code email hander."""

    layer = ZopelessAppServerLayer

    def setUp(self):
        super(TestCodeHandler, self).setUp(user='test@canonical.com')
        self.code_handler = CodeHandler()
        self._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)

    def tearDown(self):
        setSecurityPolicy(self._old_policy)
        super(TestCodeHandler, self).tearDown()

    def switchDbUser(self, user):
        """Commit the transaction and switch to the new user."""
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(user)

    def test_get(self):
        handler = mail_handlers.get(config.launchpad.code_domain)
        self.assertIsInstance(handler, CodeHandler)

    def test_process(self):
        """Processing an email creates an appropriate CodeReviewComment."""
        mail = self.factory.makeSignedMessage('<my-id>')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.assertTrue(self.code_handler.process(
            mail, email_addr, None), "Succeeded, but didn't return True")
        # if the message has not been created, this raises SQLObjectNotFound
        MessageSet().get('<my-id>')

    def test_process_packagebranch(self):
        """Processing an email related to a package branch works.."""
        mail = self.factory.makeSignedMessage('<my-id>')
        target_branch = self.factory.makePackageBranch()
        bmp = self.factory.makeBranchMergeProposal(
            target_branch=target_branch)
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        self.assertIn(
            '<my-id>', [comment.message.rfc822msgid
                        for comment in bmp.all_comments])

    def test_processBadAddress(self):
        """When a bad address is supplied, it returns False."""
        mail = self.factory.makeSignedMessage('<my-id>')
        self.switchDbUser(config.processmail.dbuser)
        self.assertFalse(self.code_handler.process(mail,
            'foo@code.launchpad.dev', None))

    def test_processNonExistantAddress(self):
        """When a non-existant address is supplied, it returns False."""
        mail = self.factory.makeSignedMessage('<my-id>')
        self.switchDbUser(config.processmail.dbuser)
        self.assertTrue(self.code_handler.process(mail,
            'mp+0@code.launchpad.dev', None))
        notification = pop_notifications()[0]
        self.assertEqual('Submit Request Failure', notification['subject'])
        # The returned message is a multipart message, the first part is
        # the message, and the second is the original message.
        message, original = notification.get_payload()
        self.assertIn(
            "There is no merge proposal at mp+0@code.launchpad.dev\n",
            message.get_payload(decode=True))

    def test_processBadVote(self):
        """process handles bad votes properly."""
        mail = self.factory.makeSignedMessage(body=' vote badvalue')
        # Make sure that the correct user principal is there.
        login(mail['From'])
        bmp = self.factory.makeBranchMergeProposal()
        # Remove the notifications sent about the new proposal.
        pop_notifications()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.assertTrue(self.code_handler.process(
            mail, email_addr, None), "Didn't return True")
        notification = pop_notifications()[0]
        self.assertEqual('Submit Request Failure', notification['subject'])
        # The returned message is a multipart message, the first part is
        # the message, and the second is the original message.
        message, original = notification.get_payload()
        self.assertEqual(dedent("""\
        An error occurred while processing a mail you sent to Launchpad's email
        interface.

        Failing command:
            vote badvalue

        Error message:

        The 'review' command expects any of the following arguments:
        abstain, approve, disapprove, needs-fixing, needs-info, resubmit

        For example:

            review needs-fixing


        -- 
        For more information about using Launchpad by e-mail, see
        https://help.launchpad.net/EmailInterface
        or send an email to help@launchpad.net"""),
                                message.get_payload(decode=True))
        self.assertEqual(mail['From'], notification['To'])

    def test_getReplyAddress(self):
        """getReplyAddress should return From or Reply-to address."""
        mail = self.factory.makeSignedMessage()
        self.switchDbUser(config.processmail.dbuser)
        self.assertEqual(
            mail['From'], self.code_handler._getReplyAddress(mail))
        mail['Reply-to'] = self.factory.getUniqueEmailAddress()
        self.assertEqual(
            mail['Reply-to'], self.code_handler._getReplyAddress(mail))

    def test_process_for_imported_branch(self):
        """Make sure that the database user is able refer to import branches.

        Import branches have different permission checks than other branches.

        Permission to mark a merge proposal as approved checks launchpad.Edit
        of the target branch, or membership of the review team on the target
        branch.  For import branches launchpad.Edit also checks the registrant
        of the code import if there is one, and membership of vcs-imports.  So
        if someone is attempting to review something on an import branch, but
        they don't have launchpad.Edit but are a member of the review team,
        then a check against the code import is done.
        """
        mail = self.factory.makeSignedMessage(body=' merge approved')
        code_import = self.factory.makeCodeImport()
        bmp = self.factory.makeBranchMergeProposal(
            target_branch=code_import.branch)
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        pop_notifications()
        self.code_handler.process(mail, email_addr, None)
        notification = pop_notifications()[0]
        # The returned message is a multipart message, the first part is
        # the message, and the second is the original message.
        message, original = notification.get_payload()
        self.assertTrue(
            "You are not a reviewer for the branch" in
            message.get_payload(decode=True))

    def test_processVote(self):
        """Process respects the vote command."""
        mail = self.factory.makeSignedMessage(body=' vote Abstain EBAILIWICK')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        self.assertEqual(CodeReviewVote.ABSTAIN, bmp.all_comments[0].vote)
        self.assertEqual('ebailiwick', bmp.all_comments[0].vote_tag)

    def test_processVoteColon(self):
        """Process respects the vote: command."""
        mail = self.factory.makeSignedMessage(
            body=' vote: Abstain EBAILIWICK')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        self.assertEqual(CodeReviewVote.ABSTAIN, bmp.all_comments[0].vote)
        self.assertEqual('ebailiwick', bmp.all_comments[0].vote_tag)

    def test_processReview(self):
        """Process respects the review command."""
        mail = self.factory.makeSignedMessage(body=' review Abstain ROAR!')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        self.assertEqual(CodeReviewVote.ABSTAIN, bmp.all_comments[0].vote)
        self.assertEqual('roar!', bmp.all_comments[0].vote_tag)

    def test_processReviewColon(self):
        """Process respects the review: command."""
        mail = self.factory.makeSignedMessage(body=' review: Abstain ROAR!')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        self.assertEqual(CodeReviewVote.ABSTAIN, bmp.all_comments[0].vote)
        self.assertEqual('roar!', bmp.all_comments[0].vote_tag)

    def test_processWithExistingVote(self):
        """Process respects the vote command."""
        mail = self.factory.makeSignedMessage(body=' vote Abstain EBAILIWICK')
        sender = self.factory.makePerson()
        bmp = self.factory.makeBranchMergeProposal(reviewer=sender)
        email_addr = bmp.address
        [vote] = list(bmp.votes)
        self.assertEqual(sender, vote.reviewer)
        self.assertTrue(vote.comment is None)
        self.switchDbUser(config.processmail.dbuser)
        # Login the sender as they are set as the message owner.
        login_person(sender)
        self.code_handler.process(mail, email_addr, None)
        comment = bmp.all_comments[0]
        self.assertEqual(CodeReviewVote.ABSTAIN, comment.vote)
        self.assertEqual('ebailiwick', comment.vote_tag)
        [vote] = list(bmp.votes)
        self.assertEqual(sender, vote.reviewer)
        self.assertEqual(comment, vote.comment)

    def test_processmail_generates_job(self):
        """Processing mail causes an email job to be created."""
        mail = self.factory.makeSignedMessage(
            body=' vote Abstain EBAILIWICK', subject='subject')
        bmp = self.factory.makeBranchMergeProposal()
        # Pop the notifications generated by the new proposal.
        pop_notifications()
        subscriber = self.factory.makePerson()
        bmp.source_branch.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL, subscriber)
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        job = Store.of(bmp).find(
            BranchMergeProposalJob,
            BranchMergeProposalJob.branch_merge_proposal == bmp,
            BranchMergeProposalJob.job_type ==
            BranchMergeProposalJobType.CODE_REVIEW_COMMENT_EMAIL).one()
        self.assertIsNot(None, job)
        # Ensure the DB operations violate no constraints.
        Store.of(bmp).flush()

    def test_getBranchMergeProposal(self):
        """The correct BranchMergeProposal is returned for the address."""
        bmp = self.factory.makeBranchMergeProposal()
        self.switchDbUser(config.processmail.dbuser)
        bmp2 = self.code_handler.getBranchMergeProposal(bmp.address)
        self.assertEqual(bmp, bmp2)

    def test_getBranchMergeProposalInvalid(self):
        """InvalidBranchMergeProposalAddress is raised if appropriate."""
        self.switchDbUser(config.processmail.dbuser)
        self.assertRaises(InvalidBranchMergeProposalAddress,
                          self.code_handler.getBranchMergeProposal, '')
        self.assertRaises(InvalidBranchMergeProposalAddress,
                          self.code_handler.getBranchMergeProposal, 'mp+abc@')

    def test_acquireBranchesForProposal(self):
        """Ensure CodeHandler._acquireBranchesForProposal works."""
        target_branch = self.factory.makeAnyBranch()
        source_branch = self.factory.makeAnyBranch()
        md = self.factory.makeMergeDirective(source_branch, target_branch)
        submitter = self.factory.makePerson()
        self.switchDbUser(config.processmail.dbuser)
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual(mp_source, source_branch)
        self.assertEqual(mp_target, target_branch)
        transaction.commit()

    def test_acquireBranchesForProposalRemoteTarget(self):
        """CodeHandler._acquireBranchesForProposal fails on remote targets."""
        source_branch = self.factory.makeAnyBranch()
        md = self.factory.makeMergeDirective(
            source_branch, target_branch_url='http://example.com')
        submitter = self.factory.makePerson()
        self.switchDbUser(config.create_merge_proposals.dbuser)
        self.assertRaises(
            NonLaunchpadTarget, self.code_handler._acquireBranchesForProposal,
            md, submitter)
        transaction.commit()

    def test_acquireBranchesForProposalRemoteSource(self):
        """CodeHandler._acquireBranchesForProposal allows remote sources.

        If there's no existing remote branch, it creates one, using
        the suffix of the url as a branch name seed.
        """
        target_branch = self.factory.makeProductBranch()
        source_branch_url = 'http://example.com/suffix'
        md = self.factory.makeMergeDirective(
            source_branch_url=source_branch_url, target_branch=target_branch)
        branches = getUtility(IBranchLookup)
        self.assertIs(None, branches.getByUrl(source_branch_url))
        submitter = self.factory.makePerson()
        self.switchDbUser(config.create_merge_proposals.dbuser)
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual(mp_target, target_branch)
        self.assertIsNot(None, mp_source)
        self.assertEqual(mp_source, branches.getByUrl(source_branch_url))
        self.assertEqual(BranchType.REMOTE, mp_source.branch_type)
        self.assertEqual(mp_target.product, mp_source.product)
        self.assertEqual('suffix', mp_source.name)
        transaction.commit()

    def test_acquireBranchesForProposalRemoteSourceDupeName(self):
        """CodeHandler._acquireBranchesForProposal creates names safely.

        When creating a new branch, it uses the suffix of the url as a branch
        name seed.  If there is already a branch with that name, it appends
        a numeric suffix.
        """
        target_branch = self.factory.makeProductBranch()
        source_branch_url = 'http://example.com/suffix'
        md = self.factory.makeMergeDirective(
            source_branch_url=source_branch_url, target_branch=target_branch)
        submitter = self.factory.makePerson()
        self.factory.makeProductBranch(
            product=target_branch.product, name='suffix', owner=submitter)
        self.switchDbUser(config.create_merge_proposals.dbuser)
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual('suffix-1', mp_source.name)
        transaction.commit()

    def test_findMergeDirectiveAndComment(self):
        """findMergeDirectiveAndComment works."""
        md = self.factory.makeMergeDirective()
        message = self.factory.makeSignedMessage(
            body='Hi!\n', attachment_contents=''.join(md.to_lines()),
            force_transfer_encoding=True)
        code_handler = CodeHandler()
        self.switchDbUser(config.processmail.dbuser)
        comment, md2 = code_handler.findMergeDirectiveAndComment(message)
        self.assertEqual('Hi!\n', comment)
        self.assertEqual(md.revision_id, md2.revision_id)
        self.assertEqual(md.target_branch, md2.target_branch)
        transaction.commit()

    def test_findMergeDirectiveAndCommentEmptyBody(self):
        """findMergeDirectiveAndComment handles empty message bodies.

        Empty message bodies are returned verbatim.
        """
        md = self.factory.makeMergeDirective()
        message = self.factory.makeSignedMessage(
            body='', attachment_contents=''.join(md.to_lines()))
        self.switchDbUser(config.processmail.dbuser)
        code_handler = CodeHandler()
        comment, md2 = code_handler.findMergeDirectiveAndComment(message)
        self.assertEqual('', comment)
        transaction.commit()

    def test_findMergeDirectiveAndComment_no_content_type(self):
        """Parts with no content-type are treated as text/plain."""
        md = self.factory.makeMergeDirective()
        message = self.factory.makeSignedMessage(
            body='', attachment_contents=''.join(md.to_lines()))
        body = message.get_payload()[0]
        del body['Content-type']
        body.set_payload('body')
        self.switchDbUser(config.processmail.dbuser)
        code_handler = CodeHandler()
        comment, md2 = code_handler.findMergeDirectiveAndComment(message)
        self.assertEqual('body', comment)

    def test_findMergeDirectiveAndComment_case_insensitive(self):
        """findMergeDirectiveAndComment uses case-insensitive content-type."""
        md = self.factory.makeMergeDirective()
        message = self.factory.makeSignedMessage(
            body='', attachment_contents=''.join(md.to_lines()))
        body = message.get_payload()[0]
        # Unlike dicts, messages append when you assign to a key.  So
        # we must delete the first Content-type before adding another.
        del body['Content-type']
        body['Content-type'] = 'Text/Plain'
        body.set_payload('body')
        self.switchDbUser(config.processmail.dbuser)
        code_handler = CodeHandler()
        comment, md2 = code_handler.findMergeDirectiveAndComment(message)
        self.assertEqual('body', comment)

    def test_findMergeDirectiveAndCommentUnicodeBody(self):
        """findMergeDirectiveAndComment returns unicode comments."""
        md = self.factory.makeMergeDirective()
        message = self.factory.makeSignedMessage(
            body=u'\u1234', attachment_contents=''.join(md.to_lines()))
        self.switchDbUser(config.processmail.dbuser)
        code_handler = CodeHandler()
        comment, md2 = code_handler.findMergeDirectiveAndComment(message)
        self.assertEqual(u'\u1234', comment)
        transaction.commit()

    def test_findMergeDirectiveAndCommentNoMergeDirective(self):
        """findMergeDirectiveAndComment handles missing merge directives.

        MissingMergeDirective is raised when no merge directive is present.
        """
        message = self.factory.makeSignedMessage(body='Hi!\n')
        self.switchDbUser(config.processmail.dbuser)
        code_handler = CodeHandler()
        self.assertRaises(MissingMergeDirective,
            code_handler.findMergeDirectiveAndComment, message)
        transaction.commit()

    def test_processMergeProposal(self):
        """processMergeProposal creates a merge proposal and comment."""
        message, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail())
        # Add some revisions so the proposal is ready.
        self.factory.makeRevisionsForBranch(source, count=1)
        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        pop_notifications()
        bmp = code_handler.processMergeProposal(message)
        self.assertEqual(source, bmp.source_branch)
        self.assertEqual(target, bmp.target_branch)
        self.assertIs(None, bmp.review_diff)
        self.assertEqual('Hi!', bmp.description)
        # No emails are sent.
        messages = pop_notifications()
        self.assertEqual(0, len(messages))
        # Only a job created.
        runner = JobRunner.fromReady(MergeProposalNeedsReviewEmailJob)
        self.assertEqual(1, len(list(runner.jobs)))
        transaction.commit()

    def test_processMergeProposalEmptyMessage(self):
        """processMergeProposal handles empty message bodies.

        Messages with empty bodies produce merge proposals only, not
        comments.
        """
        message, file_alias, source_branch, target_branch = (
            self.factory.makeMergeDirectiveEmail(body=' '))
        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        bmp = code_handler.processMergeProposal(message)
        self.assertEqual(source_branch, bmp.source_branch)
        self.assertEqual(target_branch, bmp.target_branch)
        self.assertIs(None, bmp.description)
        self.assertEqual(0, bmp.all_comments.count())
        transaction.commit()

    def test_processMergeDirectiveEmailNeedsGPG(self):
        """process creates a merge proposal from a merge directive email."""
        message, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail())
        # Ensure the message is stored in the librarian.
        # mail.incoming.handleMail also explicitly does this.
        transaction.commit()
        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        # In order to fake a non-gpg signed email, we say that the current
        # principal direcly provides IWeaklyAuthenticatePrincipal, which is
        # what the surrounding code does.
        cur_principal = get_current_principal()
        directlyProvides(
            cur_principal, directlyProvidedBy(cur_principal),
            IWeaklyAuthenticatedPrincipal)
        code_handler.process(message, 'merge@code.launchpad.net', file_alias)

        notification = pop_notifications()[0]
        self.assertEqual('Submit Request Failure', notification['subject'])
        # The returned message is a multipart message, the first part is
        # the message, and the second is the original message.
        message, original = notification.get_payload()
        self.assertEqual(dedent("""\
        An error occurred while processing a mail you sent to Launchpad's email
        interface.


        Error message:

        All emails to merge@code.launchpad.net must be signed with your OpenPGP
        key.


        -- 
        For more information about using Launchpad by e-mail, see
        https://help.launchpad.net/EmailInterface
        or send an email to help@launchpad.net"""),
                                message.get_payload(decode=True))

    def test_processWithMergeDirectiveEmail(self):
        """process creates a merge proposal from a merge directive email."""
        message, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail())
        # Ensure the message is stored in the librarian.
        # mail.incoming.handleMail also explicitly does this.
        self.switchDbUser(config.processmail.dbuser)
        code_handler = CodeHandler()
        self.assertEqual(0, source.landing_targets.count())
        code_handler.process(message, 'merge@code.launchpad.net', file_alias)
        self.switchDbUser(config.create_merge_proposals.dbuser)
        JobRunner.fromReady(CreateMergeProposalJob).runAll()
        self.assertEqual(target, source.landing_targets[0].target_branch)
        # Ensure the DB operations violate no constraints.
        Store.of(source).flush()

    def test_processWithUnicodeMergeDirectiveEmail(self):
        """process creates a comment from a unicode message body."""
        message, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail(body=u'\u1234'))
        # Ensure the message is stored in the librarian.
        # mail.incoming.handleMail also explicitly does this.
        self.switchDbUser(config.processmail.dbuser)
        code_handler = CodeHandler()
        self.assertEqual(0, source.landing_targets.count())
        code_handler.process(message, 'merge@code.launchpad.net', file_alias)
        self.switchDbUser(config.create_merge_proposals.dbuser)
        JobRunner.fromReady(CreateMergeProposalJob).runAll()
        proposal = source.landing_targets[0]
        self.assertEqual(u'\u1234', proposal.description)
        # Ensure the DB operations violate no constraints.
        Store.of(proposal).flush()

    def test_processMergeProposalReviewerRequested(self):
        # The commands in the merge proposal are parsed.
        eric = self.factory.makePerson(name="eric")
        message, file_alias, source_branch, target_branch = (
            self.factory.makeMergeDirectiveEmail(body=dedent("""\
                This is the comment.

                  reviewer eric
                """)))
        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        pop_notifications()
        bmp = code_handler.processMergeProposal(message)
        pending_reviews = list(bmp.votes)
        self.assertEqual(1, len(pending_reviews))
        self.assertEqual(eric, pending_reviews[0].reviewer)
        # No emails are sent.
        messages = pop_notifications()
        self.assertEqual(0, len(messages))
        # Ensure the DB operations violate no constraints.
        Store.of(bmp).flush()

    def test_reviewer_with_diff(self):
        """Requesting a review with a diff works."""
        diff_text = ''.join(unified_diff('', 'Fake diff'))
        preview_diff = PreviewDiff.create(
            diff_text,
            unicode(self.factory.getUniqueString('revid')),
            unicode(self.factory.getUniqueString('revid')),
            None, None)
        # To record the diff in the librarian.
        transaction.commit()
        bmp = make_merge_proposal_without_reviewers(
            self.factory, preview_diff=preview_diff)
        eric = self.factory.makePerson(name="eric", email="eric@example.com")
        mail = self.factory.makeSignedMessage(body=' reviewer eric')
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        [vote] = bmp.votes
        self.assertEqual(eric, vote.reviewer)

    def test_processMergeProposalDefaultReviewer(self):
        # If no reviewer was requested in the comment body, then the default
        # reviewer of the target branch is used.
        message, file_alias, source_branch, target_branch = (
            self.factory.makeMergeDirectiveEmail(body=dedent("""\
                This is the comment.
                """)))
        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        pop_notifications()
        bmp = code_handler.processMergeProposal(message)
        # If no reviewer is specified, then the default reviewer of the target
        # branch is requested to review.
        pending_reviews = list(bmp.votes)
        self.assertEqual(1, len(pending_reviews))
        self.assertEqual(
            target_branch.code_reviewer,
            pending_reviews[0].reviewer)
        # No emails are sent.
        messages = pop_notifications()
        self.assertEqual(0, len(messages))
        # Ensure the DB operations violate no constraints.
        Store.of(target_branch).flush()

    def test_processMergeProposalExists(self):
        """processMergeProposal raises BranchMergeProposalExists

        If there is already a merge proposal with the same target and source
        branches of the merge directive, an email is sent to the user.
        """
        message, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail())
        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        code_handler.processMergeProposal(message)
        pop_notifications()
        transaction.commit()
        code_handler.processMergeProposal(message)
        [notification] = pop_notifications()
        self.assertEqual(
            notification['Subject'], 'Error Creating Merge Proposal')
        self.assertEqual(
            notification.get_payload(decode=True),
            'The branch %s is already proposed for merging into %s.\n\n'
            % (source.bzr_identity, target.bzr_identity))
        self.assertEqual(notification['to'], message['from'])

    def test_processMissingMergeDirective(self):
        """process sends an email if the original email lacks an attachment.
        """
        message = self.factory.makeSignedMessage(body='A body',
            subject='A subject', attachment_contents='')
        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        code_handler.processMergeProposal(message)
        transaction.commit()
        [notification] = pop_notifications()

        self.assertEqual(
            notification['Subject'], 'Error Creating Merge Proposal')
        self.assertEqual(
            notification.get_payload(),
            'Your email did not contain a merge directive. Please resend '
            'your email with\nthe merge directive attached.\n')
        self.assertEqual(notification['to'],
            message['from'])

    def makeTargetBranch(self):
        """Helper for getNewBranchInfo tests."""
        owner = self.factory.makePerson(name='target-owner')
        product = self.factory.makeProduct(name='target-product')
        return self.factory.makeProductBranch(product=product, owner=owner)

    def test_getNewBranchInfoNoURL(self):
        """If no URL, target namespace is used, with 'merge' basename."""
        submitter = self.factory.makePerson(name='merge-submitter')
        target = self.makeTargetBranch()
        code_handler = CodeHandler()
        namespace, base = code_handler._getNewBranchInfo(
            None, target, submitter)
        self.assertEqual('~merge-submitter/target-product', namespace.name)
        self.assertEqual('merge', base)

    def test_getNewBranchInfoRemoteURL(self):
        """If a URL is provided, its base is used, with target namespace."""
        submitter = self.factory.makePerson(name='merge-submitter')
        target = self.makeTargetBranch()
        code_handler = CodeHandler()
        namespace, base = code_handler._getNewBranchInfo(
                'http://foo/bar', target, submitter)
        self.assertEqual('~merge-submitter/target-product', namespace.name)
        self.assertEqual('bar', base)

    def test_getNewBranchInfoRemoteURLTrailingSlash(self):
        """Trailing slashes are ignored when determining base."""
        submitter = self.factory.makePerson(name='merge-submitter')
        target = self.makeTargetBranch()
        code_handler = CodeHandler()
        namespace, base = code_handler._getNewBranchInfo(
                'http://foo/bar/', target, submitter)
        self.assertEqual('~merge-submitter/target-product', namespace.name)
        self.assertEqual('bar', base)

    def test_getNewBranchInfoLPURL(self):
        """If an LP URL is provided, we attempt to reproduce it exactly."""
        submitter = self.factory.makePerson(name='merge-submitter')
        target = self.makeTargetBranch()
        self.factory.makeProduct('uproduct')
        self.factory.makePerson(name='uuser')
        code_handler = CodeHandler()
        namespace, base = code_handler._getNewBranchInfo(
            config.codehosting.supermirror_root + '~uuser/uproduct/bar',
            target, submitter)
        self.assertEqual('~uuser/uproduct', namespace.name)
        self.assertEqual('bar', base)

    def test_getNewBranchInfoLPURLTrailingSlash(self):
        """Trailing slashes are permitted in LP URLs."""
        submitter = self.factory.makePerson(name='merge-submitter')
        target = self.makeTargetBranch()
        self.factory.makeProduct('uproduct')
        self.factory.makePerson(name='uuser')
        code_handler = CodeHandler()
        namespace, base = code_handler._getNewBranchInfo(
            config.codehosting.supermirror_root + '~uuser/uproduct/bar/',
            target, submitter)
        self.assertEqual('~uuser/uproduct', namespace.name)
        self.assertEqual('bar', base)

    def test_processNonLaunchpadTarget(self):
        """When target branch is unknown to Launchpad, the user is notified.
        """
        directive = self.factory.makeMergeDirective(
            target_branch_url='http://www.example.com')
        message = self.factory.makeSignedMessage(body='body',
            subject='This is gonna fail', attachment_contents=''.join(
                directive.to_lines()))

        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        code_handler.processMergeProposal(message)
        transaction.commit()
        [notification] = pop_notifications()

        self.assertEqual(
            notification['Subject'], 'Error Creating Merge Proposal')
        self.assertEqual(
            notification.get_payload(decode=True),
            'The target branch at %s is not known to Launchpad.  It\'s\n'
            'possible that your submit branch is not set correctly, or that '
            'your submit\nbranch has not yet been pushed to Launchpad.\n\n'
            % ('http://www.example.com'))
        self.assertEqual(notification['to'],
            message['from'])

    def test_processMissingSubject(self):
        """If the subject is missing, the user is warned by email."""
        mail = self.factory.makeSignedMessage(
            body=' review abstain',
            subject='')
        bmp = self.factory.makeBranchMergeProposal()
        pop_notifications()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        [notification] = pop_notifications()

        self.assertEqual(
            notification['Subject'], 'Error Creating Merge Proposal')
        self.assertEqual(
            notification.get_payload(decode=True),
            'Your message did not contain a subject.  Launchpad code '
            'reviews require all\nemails to contain subject lines.  '
            'Please re-send your email including the\nsubject line.\n\n')
        self.assertEqual(notification['to'],
            mail['from'])
        self.assertEqual(0, bmp.all_comments.count())


class TestCodeHandlerProcessMergeDirective(TestCaseWithFactory):
    """Test the merge directive processing parts of the code email hander."""

    layer = ZopelessAppServerLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, user='test@canonical.com')
        self.code_handler = CodeHandler()
        self._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)

    def tearDown(self):
        setSecurityPolicy(self._old_policy)
        TestCaseWithFactory.tearDown(self)

    def switchDbUser(self, user):
        """Commit the transactionand switch to the new user."""
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(user)

    def _createTargetSourceAndBundle(self, format=None):
        """Create a merge directive with a bundle and associated branches.

        The target branch is created in the specified format, or the default
        format if the format is None.

        :return: A tuple containing the db_branch relating to the target
            branch, a bzr_branch of the source branch, and the merge directive
            containing the revisions in the source branch that aren't in the
            target branch.
        """
        db_target_branch, target_tree = self.create_branch_and_tree(
            tree_location='.', format=format)
        target_tree.branch.set_public_branch(db_target_branch.bzr_identity)
        # XXX: AaronBentley 2010-08-06 bug=614404: a bzr username is
        # required to generate the revision-id.
        with override_environ(BZR_EMAIL='me@example.com'):
            target_tree.commit('rev1')
            # Make sure that the created branch has been mirrored.
            removeSecurityProxy(db_target_branch).branchChanged(
                '', 'rev1', None, None, None)
            sprout_bzrdir = target_tree.bzrdir.sprout('source')
            source_tree = sprout_bzrdir.open_workingtree()
            source_tree.commit('rev2')
        message = self.factory.makeBundleMergeDirectiveEmail(
            source_tree.branch, db_target_branch)
        return db_target_branch, source_tree.branch, message

    def _openBazaarBranchAsClient(self, db_branch):
        """Open the Bazaar branch relating to db_branch as if a client was.

        The client has write access to the branch.
        """
        lp_server = get_lp_server(db_branch.owner.id)
        lp_server.start_server()
        self.addCleanup(lp_server.stop_server)
        branch_url = urljoin(lp_server.get_url(), db_branch.unique_name)
        return Branch.open(branch_url)

    def _processMergeDirective(self, message):
        """Process the merge directive email."""
        self.switchDbUser(config.create_merge_proposals.dbuser)
        code_handler = CodeHandler()
        # Do the authentication dance as we do in the processing script.
        authutil = getUtility(IPlacelessAuthUtility)
        email_addr = message['from']
        principal = authutil.getPrincipalByLogin(email_addr)
        if principal is None:
            raise AssertionError('No principal found for %s' % email_addr)
        setupInteraction(principal, email_addr)
        return code_handler.processMergeProposal(message)

    def test_nonstackable_target(self):
        # If the target branch is in a non-stackable format, then the source
        # branch that is created is an empty hosted branch.  The new branch
        # will not have a mirror requested as there are no revisions, and
        # there is no branch created in the hosted area.

        # XXX Tim Penhey 2010-07-27 bug 610292
        # We should fail here and return an oops email to the user.
        self.useBzrBranches()
        branch, source, message = self._createTargetSourceAndBundle(
            format="pack-0.92")
        bmp = self._processMergeDirective(message)
        self.assertEqual(BranchType.HOSTED, bmp.source_branch.branch_type)
        self.assertIs(None, bmp.source_branch.next_mirror_time)

    def test_stackable_unmirrored_target(self):
        # If the target branch is in a stackable format but has not been
        # mirrored, the source branch that is created is an empty hosted
        # branch.  The new branch will not have a mirror requested as there
        # are no revisions, and there is no branch created in the hosted area.
        self.useBzrBranches()
        branch, source, message = self._createTargetSourceAndBundle(
            format="1.9")
        # Mark the target branch as "unmirrored", at least as far as the db is
        # concerned.
        branch.last_mirrored = None
        branch.last_mirrored_id = None
        bmp = self._processMergeDirective(message)
        self.assertEqual(BranchType.REMOTE, bmp.source_branch.branch_type)

    def test_stackable_target(self):
        # If the target branch is in a stackable format, then the source
        # branch that is created is a hosted branch stacked on the target
        # branch. The source branch will have the revisions from the bundle,
        # and a mirror will have been triggered.
        self.useBzrBranches()
        branch, source, message = self._createTargetSourceAndBundle(
            format="1.9")
        bmp = self._processMergeDirective(message)
        source_bzr_branch = self._openBazaarBranchAsClient(bmp.source_branch)
        self.assertEqual(BranchType.HOSTED, bmp.source_branch.branch_type)
        self.assertTrue(bmp.source_branch.pending_writes)
        self.assertEqual(
            source.last_revision(), source_bzr_branch.last_revision())

    def test_branch_stacked(self):
        # When a branch is created for a merge directive, it is created
        # stacked on the target branch.
        self.useBzrBranches()
        branch, source, message = self._createTargetSourceAndBundle(
            format="1.9")
        bmp = self._processMergeDirective(message)
        # The source branch is stacked on the target.
        source_bzr_branch = self._openBazaarBranchAsClient(bmp.source_branch)
        self.assertEqual(
            '/' + bmp.target_branch.unique_name,
            source_bzr_branch.get_stacked_on_url())
        # Make sure that the source branch doesn't have all the revisions.
        source_branch_revisions = (
            source_bzr_branch.bzrdir.open_repository().all_revision_ids())
        # The only revision is the tip revision, as the other revisions are
        # from the target branch.
        tip_revision = source_bzr_branch.last_revision()
        self.assertEqual([tip_revision], source_branch_revisions)

    def test_source_not_newer(self):
        # The source branch is created correctly when the source is not newer
        # than the target, instead of raising DivergedBranches.
        self.useBzrBranches()
        branch, source, message = self._createTargetSourceAndBundle(
            format="1.9")
        target_tree = WorkingTree.open('.')
        # XXX: AaronBentley 2010-08-06 bug=614404: a bzr username is
        # required to generate the revision-id.
        with override_environ(BZR_EMAIL='me@example.com'):
            target_tree.commit('rev2b')
        bmp = self._processMergeDirective(message)
        lp_branch = self._openBazaarBranchAsClient(bmp.source_branch)
        self.assertEqual(source.last_revision(), lp_branch.last_revision())

    def _createPreexistingSourceAndMessage(self, target_format,
                                           source_format, set_stacked=False):
        """Create the source and target branches and the merge directive."""
        db_target_branch, target_tree = self.create_branch_and_tree(
            'target', format=target_format)
        target_tree.branch.set_public_branch(db_target_branch.bzr_identity)
        # XXX: AaronBentley 2010-08-06 bug=614404: a bzr username is
        # required to generate the revision-id.
        with override_environ(BZR_EMAIL='me@example.com'):
            revid = target_tree.commit('rev1')
            removeSecurityProxy(db_target_branch).branchChanged(
                '', revid, None, None, None)

            db_source_branch, source_tree = self.create_branch_and_tree(
                'lpsource', db_target_branch.product, format=source_format)
            # The branch is not scheduled to be mirrorred.
            self.assertIs(db_source_branch.next_mirror_time, None)
            source_tree.pull(target_tree.branch)
            source_tree.commit('rev2', rev_id='rev2')
            # bundle_tree is effectively behaving like a local copy of
            # db_source_branch, and is used to create the merge directive.
            sprout_bzrdir = source_tree.bzrdir.sprout('source')
            bundle_tree = sprout_bzrdir.open_workingtree()
            bundle_tree.commit('rev3', rev_id='rev3')
        bundle_tree.branch.set_public_branch(db_source_branch.bzr_identity)
        message = self.factory.makeBundleMergeDirectiveEmail(
            bundle_tree.branch, db_target_branch,
            sender=db_source_branch.owner)
        # Tell the source branch that it is stacked on the target.
        if set_stacked:
            stacked_url = '/' + db_target_branch.unique_name
            branch = self._openBazaarBranchAsClient(db_source_branch)
            branch.set_stacked_on_url(stacked_url)
        return db_source_branch, message

    def test_existing_stacked_branch(self):
        # A bundle can update an existing branch if they are both stackable,
        # and the source branch is stacked.
        self.useBzrBranches()
        lp_source, message = self._createPreexistingSourceAndMessage(
            target_format="1.9", source_format="1.9", set_stacked=True)
        bmp = self._processMergeDirective(message)
        # The branch merge proposal should use the existing db branch.
        self.assertEqual(lp_source, bmp.source_branch)
        bzr_branch = self._openBazaarBranchAsClient(bmp.source_branch)
        # The branch has been updated.
        self.assertEqual('rev3', bzr_branch.last_revision())

    def test_existing_unstacked_branch(self):
        # Even if the source and target are stackable, if the source is not
        # stacked, we don't support stacking something that wasn't stacked
        # before (yet).
        self.useBzrBranches()
        lp_source, message = self._createPreexistingSourceAndMessage(
            target_format="1.9", source_format="1.9")
        bmp = self._processMergeDirective(message)
        # The branch merge proposal should use the existing db branch.
        self.assertEqual(lp_source, bmp.source_branch)
        bzr_branch = self._openBazaarBranchAsClient(bmp.source_branch)
        # The hosted copy of the branch has not been updated.
        self.assertEqual('rev2', bzr_branch.last_revision())

    def test_existing_branch_nonstackable_target(self):
        # If the target branch is not stackable, then we don't pull any
        # revisions.
        self.useBzrBranches()
        lp_source, message = self._createPreexistingSourceAndMessage(
            target_format="pack-0.92", source_format="1.9")
        bmp = self._processMergeDirective(message)
        # The branch merge proposal should use the existing db branch.
        self.assertEqual(lp_source, bmp.source_branch)
        # Now the branch is not scheduled to be mirrorred.
        self.assertIs(None, lp_source.next_mirror_time)
        hosted = self._openBazaarBranchAsClient(bmp.source_branch)
        # The hosted copy has not been updated.
        self.assertEqual('rev2', hosted.last_revision())

    def test_existing_branch_nonstackable_source(self):
        # If the source branch is not stackable, then we don't pull any
        # revisions.
        self.useBzrBranches()
        lp_source, message = self._createPreexistingSourceAndMessage(
            target_format="1.9", source_format="pack-0.92")
        bmp = self._processMergeDirective(message)
        # The branch merge proposal should use the existing db branch.
        self.assertEqual(lp_source, bmp.source_branch)
        # Now the branch is not scheduled to be mirrorred.
        self.assertIs(None, lp_source.next_mirror_time)
        hosted = self._openBazaarBranchAsClient(bmp.source_branch)
        # The hosted copy has not been updated.
        self.assertEqual('rev2', hosted.last_revision())

    def test_forbidden_target(self):
        """Specifying a branch in a forbidden target generates email."""
        self.useBzrBranches()
        branch, source, message = self._createTargetSourceAndBundle(
            format="pack-0.92")
        branch.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        result = self._processMergeDirective(message)
        self.assertIs(None, result)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'Error Creating Merge Proposal', notifications[0]['subject'])
        body = notifications[0].get_payload(decode=True)
        sender = getUtility(IPersonSet).getByEmail(message['from'])
        expected = (
            'Launchpad cannot create the branch requested by'
            ' your merge directive:\n'
            'You cannot create branches in "~%s/%s"\n' %
            (sender.name, branch.product.name))
        self.assertEqual(expected, body)


class TestVoteEmailCommand(TestCase):
    """Test the vote and tag processing of the VoteEmailCommand."""

    # We don't need no stinking layer.

    def setUp(self):
        super(TestVoteEmailCommand, self).setUp()

        class FakeExecutionContext:
            vote = None
            vote_tags = None
        self.context = FakeExecutionContext()

    def test_getVoteNoArgs(self):
        """getVote returns None, None when no arguments are supplied."""
        command = VoteEmailCommand('vote', [])
        self.assertRaises(EmailProcessingError, command.execute, self.context)

    def assertVoteAndTag(self, expected_vote, expected_tag, command):
        """Execute the command and check the resulting vote and tag."""
        command.execute(self.context)
        self.assertEqual(expected_vote, self.context.vote)
        if expected_tag is None:
            self.assertIs(None, self.context.vote_tags)
        else:
            self.assertEqual(expected_tag, self.context.vote_tags)

    def test_getVoteOneArg(self):
        """getVote returns vote, None when only a vote is supplied."""
        command = VoteEmailCommand('vote', ['apPRoVe'])
        self.assertVoteAndTag(CodeReviewVote.APPROVE, None, command)

    def test_getVoteDisapprove(self):
        """getVote returns disapprove when it is specified."""
        command = VoteEmailCommand('vote', ['dIsAppRoVe'])
        self.assertVoteAndTag(CodeReviewVote.DISAPPROVE, None, command)

    def test_getVoteBadValue(self):
        """getVote returns vote, None when only a vote is supplied."""
        command = VoteEmailCommand('vote', ['badvalue'])
        self.assertRaises(EmailProcessingError, command.execute, self.context)

    def test_getVoteThreeArg(self):
        """getVote returns vote, vote_tag when both are supplied."""
        command = VoteEmailCommand('vote', ['apPRoVe', 'DB', 'TAG'])
        self.assertVoteAndTag(CodeReviewVote.APPROVE, 'DB TAG', command)

    def test_getVoteApproveAlias(self):
        """Test the approve alias of +1."""
        command = VoteEmailCommand('vote', ['+1'])
        self.assertVoteAndTag(CodeReviewVote.APPROVE, None, command)

    def test_getVoteAbstainAlias(self):
        """Test the abstain alias of 0."""
        command = VoteEmailCommand('vote', ['0'])
        self.assertVoteAndTag(CodeReviewVote.ABSTAIN, None, command)
        command = VoteEmailCommand('vote', ['+0'])
        self.assertVoteAndTag(CodeReviewVote.ABSTAIN, None, command)
        command = VoteEmailCommand('vote', ['-0'])
        self.assertVoteAndTag(CodeReviewVote.ABSTAIN, None, command)

    def test_getVoteDisapproveAlias(self):
        """Test the disapprove alias of -1."""
        command = VoteEmailCommand('vote', ['-1'])
        self.assertVoteAndTag(CodeReviewVote.DISAPPROVE, None, command)

    def test_getVoteNeedsFixingAlias(self):
        """Test the needs_fixing aliases of needsfixing and needs-fixing."""
        command = VoteEmailCommand('vote', ['needs_fixing'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_FIXING, None, command)
        command = VoteEmailCommand('vote', ['needsfixing'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_FIXING, None, command)
        command = VoteEmailCommand('vote', ['needs-fixing'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_FIXING, None, command)

    def test_getVoteNeedsInfoAlias(self):
        """Test the needs_info review type and its aliases."""
        command = VoteEmailCommand('vote', ['needs_info'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_INFO, None, command)
        command = VoteEmailCommand('vote', ['needsinfo'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_INFO, None, command)
        command = VoteEmailCommand('vote', ['needs-info'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_INFO, None, command)
        command = VoteEmailCommand('vote', ['needs_information'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_INFO, None, command)
        command = VoteEmailCommand('vote', ['needsinformation'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_INFO, None, command)
        command = VoteEmailCommand('vote', ['needs-information'])
        self.assertVoteAndTag(CodeReviewVote.NEEDS_INFO, None, command)


class TestUpdateStatusEmailCommand(TestCaseWithFactory):
    """Test the UpdateStatusEmailCommand."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestUpdateStatusEmailCommand, self).setUp(
            user='test@canonical.com')
        self._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)
        self.merge_proposal = self.factory.makeBranchMergeProposal()
        # Default the user to be the target branch owner, so they are
        # authorised to update the status.
        self.context = CodeReviewEmailCommandExecutionContext(
            self.merge_proposal, self.merge_proposal.target_branch.owner)
        self.jrandom = self.factory.makePerson()
        transaction.commit()
        self.layer.switchDbUser(config.processmail.dbuser)

    def tearDown(self):
        setSecurityPolicy(self._old_policy)
        super(TestUpdateStatusEmailCommand, self).tearDown()

    def test_numberOfArguments(self):
        # The command needs one and only one arg.
        command = UpdateStatusEmailCommand('status', [])
        error = self.assertRaises(
            EmailProcessingError, command.execute, self.context)
        self.assertEqual(
            "The 'status' argument expects 1 argument(s). It got 0.\n",
            str(error))
        command = UpdateStatusEmailCommand('status', ['approve', 'spam'])
        error = self.assertRaises(
            EmailProcessingError, command.execute, self.context)
        self.assertEqual(
            "The 'status' argument expects 1 argument(s). It got 2.\n",
            str(error))

    def test_status_approved(self):
        # Test that approve sets the status of the merge proposal.
        self.assertNotEqual(
            BranchMergeProposalStatus.CODE_APPROVED,
            self.merge_proposal.queue_status)
        command = UpdateStatusEmailCommand('status', ['approved'])
        command.execute(self.context)
        self.assertEqual(
            BranchMergeProposalStatus.CODE_APPROVED,
            self.merge_proposal.queue_status)
        # The vote is also set if it wasn't before.
        self.assertEqual(CodeReviewVote.APPROVE, self.context.vote)
        # Commit the transaction to check database permissions.
        transaction.commit()

    def test_status_approved_doesnt_override_vote(self):
        # Test that approve sets the status of the merge proposal.
        self.context.vote = CodeReviewVote.NEEDS_FIXING
        command = UpdateStatusEmailCommand('status', ['approved'])
        command.execute(self.context)
        self.assertEqual(
            BranchMergeProposalStatus.CODE_APPROVED,
            self.merge_proposal.queue_status)
        self.assertEqual(CodeReviewVote.NEEDS_FIXING, self.context.vote)

    def test_status_rejected(self):
        # Test that rejected sets the status of the merge proposal.
        self.assertNotEqual(
            BranchMergeProposalStatus.REJECTED,
            self.merge_proposal.queue_status)
        command = UpdateStatusEmailCommand('status', ['rejected'])
        command.execute(self.context)
        self.assertEqual(
            BranchMergeProposalStatus.REJECTED,
            self.merge_proposal.queue_status)
        # The vote is also set if it wasn't before.
        self.assertEqual(CodeReviewVote.DISAPPROVE, self.context.vote)
        # Commit the transaction to check database permissions.
        transaction.commit()

    def test_status_rejected_doesnt_override_vote(self):
        # Test that approve sets the status of the merge proposal.
        self.context.vote = CodeReviewVote.NEEDS_FIXING
        command = UpdateStatusEmailCommand('status', ['rejected'])
        command.execute(self.context)
        self.assertEqual(
            BranchMergeProposalStatus.REJECTED,
            self.merge_proposal.queue_status)
        self.assertEqual(CodeReviewVote.NEEDS_FIXING, self.context.vote)

    def test_unknown_status(self):
        # Unknown status values will cause an email response to the user.
        command = UpdateStatusEmailCommand('status', ['bob'])
        error = self.assertRaises(
            EmailProcessingError, command.execute, self.context)
        self.assertEqual(
            "The 'status' command expects any of the following arguments:\n"
            "approved, rejected\n\n"
            "For example:\n\n"
            "    status approved\n",
            str(error))

    def test_not_a_reviewer(self):
        # If the user is not a reviewer, they cannot update the status.
        self.context.user = self.jrandom
        command = UpdateStatusEmailCommand('status', ['approve'])
        with person_logged_in(self.context.user):
            error = self.assertRaises(
                EmailProcessingError, command.execute, self.context)
        target = self.merge_proposal.target_branch.bzr_identity
        self.assertEqual(
            "You are not a reviewer for the branch %s.\n" % target,
            str(error))

    def test_registrant_not_a_reviewer(self):
        # If the registrant is not a reviewer, they cannot update the status.
        self.context.user = self.context.merge_proposal.registrant
        command = UpdateStatusEmailCommand('status', ['approve'])
        with person_logged_in(self.context.user):
            error = self.assertRaises(
                EmailProcessingError, command.execute, self.context)
        target = self.merge_proposal.target_branch.bzr_identity
        self.assertEqual(
            "You are not a reviewer for the branch %s.\n" % target,
            str(error))


class TestAddReviewerEmailCommand(TestCaseWithFactory):
    """Test the AddReviewerEmailCommand."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestAddReviewerEmailCommand, self).setUp(
            user='test@canonical.com')
        self._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)
        self.merge_proposal = (
            make_merge_proposal_without_reviewers(self.factory))
        # Default the user to be the target branch owner, so they are
        # authorised to update the status.
        self.context = CodeReviewEmailCommandExecutionContext(
            self.merge_proposal, self.merge_proposal.target_branch.owner)
        self.reviewer = self.factory.makePerson()
        transaction.commit()
        self.layer.switchDbUser(config.processmail.dbuser)

    def tearDown(self):
        setSecurityPolicy(self._old_policy)
        super(TestAddReviewerEmailCommand, self).tearDown()

    def test_numberOfArguments(self):
        # The command needs at least one arg.
        command = AddReviewerEmailCommand('reviewer', [])
        error = self.assertRaises(
            EmailProcessingError, command.execute, self.context)
        self.assertEqual(
            "The 'reviewer' argument expects one or more argument(s). "
            "It got 0.\n",
            str(error))

    def test_add_reviewer(self):
        # The simple case is to add a reviewer with no tags.
        command = AddReviewerEmailCommand('reviewer', [self.reviewer.name])
        command.execute(self.context)
        [vote_ref] = list(self.context.merge_proposal.votes)
        self.assertEqual(self.reviewer, vote_ref.reviewer)
        self.assertEqual(self.context.user, vote_ref.registrant)
        self.assertIs(None, vote_ref.review_type)
        self.assertIs(None, vote_ref.comment)

    def test_add_reviewer_with_tags(self):
        # The simple case is to add a reviewer with no tags.
        command = AddReviewerEmailCommand(
            'reviewer', [self.reviewer.name, 'DB', 'Foo'])
        command.execute(self.context)
        [vote_ref] = list(self.context.merge_proposal.votes)
        self.assertEqual(self.reviewer, vote_ref.reviewer)
        self.assertEqual(self.context.user, vote_ref.registrant)
        self.assertEqual('db foo', vote_ref.review_type)
        self.assertIs(None, vote_ref.comment)

    def test_unknown_reviewer(self):
        # An unknown user raises.
        command = AddReviewerEmailCommand('reviewer', ['unknown@example.com'])
        error = self.assertRaises(
            EmailProcessingError, command.execute, self.context)
        self.assertEqual(
            "There's no such person with the specified name or email: "
            "unknown@example.com\n",
            str(error))
