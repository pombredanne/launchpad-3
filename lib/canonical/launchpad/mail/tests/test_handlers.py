# Copyright 2005, 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import transaction
import unittest

from bzrlib.merge_directive import MergeDirective2
from zope.component import getUtility
from zope.security.management import setSecurityPolicy
from zope.testing.doctest import DocTestSuite

from canonical.config import config
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, BranchType,
    CodeReviewNotificationLevel, CodeReviewVote, IBranchSet)
from canonical.launchpad.database import MessageSet
from canonical.launchpad.ftests import login_person
from canonical.launchpad.interfaces.mail import EmailProcessingError
from canonical.launchpad.mail.codehandler import (
    AddReviewerEmailCommand, CodeEmailCommands, CodeHandler, InvalidBranchMergeProposalAddress,
    InvalidVoteString, MissingMergeDirective, NonLaunchpadTarget,
    UpdateStatusEmailCommand, VoteEmailCommand)
from canonical.launchpad.mail.commands import BugEmailCommand
from canonical.launchpad.mail.handlers import (
    mail_handlers, MaloneHandler)
from canonical.launchpad.mail.helpers import parse_commands
from canonical.launchpad.testing import TestCase, TestCaseWithFactory
from canonical.launchpad.tests.mail_helpers import pop_notifications
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.testing import LaunchpadFunctionalLayer, LaunchpadZopelessLayer


class TestParseCommands(TestCase):
    """Test the ParseCommands function."""

    def test_parse_commandsEmpty(self):
        """Empty messages have no commands."""
        self.assertEqual([], parse_commands('', ['command']))

    def test_parse_commandsNoIndent(self):
        """Commands with no indent are not commands."""
        self.assertEqual([], parse_commands('command', ['command']))

    def test_parse_commandsSpaceIndent(self):
        """Commands indented with spaces are recognized."""
        self.assertEqual(
            [('command', [])], parse_commands(' command', ['command']))

    def test_parse_commands_args(self):
        """Commands indented with spaces are recognized."""
        self.assertEqual(
            [('command', ['arg1', 'arg2'])],
            parse_commands(' command arg1 arg2', ['command']))

    def test_parse_commands_args_quoted(self):
        """Commands indented with spaces are recognized."""
        self.assertEqual(
            [('command', ['"arg1', 'arg2"'])],
            parse_commands(' command "arg1 arg2"', ['command']))

    def test_parse_commandsTabIndent(self):
        """Commands indented with tabs are recognized.

        (Tabs?  What are we, make?)
        """
        self.assertEqual(
            [('command', [])], parse_commands('\tcommand', ['command']))

    def test_parse_commandsDone(self):
        """The 'done' pseudo-command halts processing."""
        self.assertEqual(
            [('command', []), ('command', [])],
            parse_commands(' command\n command', ['command']))
        self.assertEqual(
            [('command', [])],
            parse_commands(' command\n done\n command', ['command']))
        # done takes no arguments.
        self.assertEqual(
            [('command', []), ('command', [])],
            parse_commands(' command\n done commands\n command', ['command']))


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

    def test_status_command(self):
        # Check that the update status command is correctly created.
        [command] = CodeEmailCommands.getCommands(" status approved")
        self.assertIsInstance(command, UpdateStatusEmailCommand)
        self.assertEqual('status', command.name)
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

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, user='test@canonical.com')
        self.code_handler = CodeHandler()
        self._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)

    def tearDown(self):
        setSecurityPolicy(self._old_policy)

    def switchDbUser(self, user):
        """Commit the transactionand switch to the new user."""
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
        message = MessageSet().get('<my-id>')

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
        self.assertFalse(self.code_handler.process(mail,
            'mp+0@code.launchpad.dev', None))

    def test_processFailure(self):
        """When process fails, it returns False."""
        code_handler = CodeHandler()
        # Induce unexpected failure
        def raise_value_error(*args, **kwargs):
            raise ValueError('Bad value')
        code_handler._getVote = raise_value_error
        mail = self.factory.makeSignedMessage('<my-id>')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.assertRaises(ValueError, code_handler.process, mail,
            email_addr, None)

    def test_processBadVote(self):
        """process handles bad votes properly."""
        mail = self.factory.makeSignedMessage(body=' vote badvalue')
        bmp = self.factory.makeBranchMergeProposal()
        # Remove the notifications sent about the new proposal.
        pop_notifications()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.assertTrue(self.code_handler.process(
            mail, email_addr, None), "Didn't return True")
        notification = pop_notifications()[0]
        self.assertEqual('Unsupported vote', notification['subject'])
        self.assertEqual(
            'Your comment was not accepted because the string "badvalue" is'
            ' not a supported voting value.  The following values are'
            ' supported: abstain, approve, disapprove, needs_fixing, '
            'resubmit.',
            notification.get_payload(decode=True))
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

    def test_processVote(self):
        """Process respects the vote command."""
        mail = self.factory.makeSignedMessage(body=' vote Abstain EBAILIWICK')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        self.assertEqual(CodeReviewVote.ABSTAIN, bmp.all_comments[0].vote)
        self.assertEqual('ebailiwick', bmp.all_comments[0].vote_tag)

    def test_processWithExistingVote(self):
        """Process respects the vote command."""
        mail = self.factory.makeSignedMessage(body=' vote Abstain EBAILIWICK')
        bmp = self.factory.makeBranchMergeProposal()
        sender = self.factory.makePerson()
        bmp.nominateReviewer(sender, bmp.registrant)
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

    def test_processSendsMail(self):
        """Processing mail causes mail to be sent."""
        mail = self.factory.makeSignedMessage(
            body=' vote Abstain EBAILIWICK', subject='subject')
        bmp = self.factory.makeBranchMergeProposal()
        # Pop the notifications generated by the new proposal.
        pop_notifications()
        subscriber = self.factory.makePerson()
        bmp.source_branch.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        email_addr = bmp.address
        self.switchDbUser(config.processmail.dbuser)
        self.code_handler.process(mail, email_addr, None)
        notification = pop_notifications()[0]
        self.assertEqual('subject', notification['Subject'])
        expected_body = ('Vote: Abstain ebailiwick\n'
                         ' vote Abstain EBAILIWICK\n'
                         '-- \n'
                         '%s\n'
                         'You are subscribed to branch %s.' %
                         (canonical_url(bmp), bmp.source_branch.bzr_identity))
        self.assertEqual(expected_body, notification.get_payload(decode=True))

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

    def makeMergeDirective(self, source_branch=None, target_branch=None,
        source_branch_url=None, target_branch_url=None):
        if source_branch_url is None:
            if source_branch is None:
                source_branch = self.factory.makeBranch()
            source_branch_url = (
                config.codehosting.supermirror_root +
                source_branch.unique_name)
        if target_branch_url is None:
            if target_branch is None:
                target_branch = self.factory.makeBranch()
            target_branch_url = (
                config.codehosting.supermirror_root +
                target_branch.unique_name)
        return MergeDirective2(
            'revid', 'sha', 0, 0, target_branch_url,
            source_branch=source_branch_url, base_revision_id='base-revid')

    def test_acquireBranchesForProposal(self):
        """Ensure CodeHandler._acquireBranchesForProposal works."""
        target_branch = self.factory.makeBranch()
        source_branch = self.factory.makeBranch()
        md = self.makeMergeDirective(source_branch, target_branch)
        submitter = self.factory.makePerson()
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual(mp_source, source_branch)
        self.assertEqual(mp_target, target_branch)

    def test_acquireBranchesForProposalRemoteTarget(self):
        """CodeHandler._acquireBranchesForProposal fails on remote targets."""
        source_branch = self.factory.makeBranch()
        md = self.makeMergeDirective(
            source_branch, target_branch_url='http://example.com')
        submitter = self.factory.makePerson()
        self.assertRaises(
            NonLaunchpadTarget, self.code_handler._acquireBranchesForProposal,
            md, submitter)

    def test_acquireBranchesForProposalRemoteSource(self):
        """CodeHandler._acquireBranchesForProposal allows remote sources.

        If there's no existing remote branch, it creates one, using
        the suffix of the url as a branch name seed.
        """
        target_branch = self.factory.makeBranch()
        source_branch_url = 'http://example.com/suffix'
        md = self.makeMergeDirective(
            source_branch_url=source_branch_url, target_branch=target_branch)
        branches = getUtility(IBranchSet)
        self.assertIs(None, branches.getByUrl(source_branch_url))
        submitter = self.factory.makePerson()
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual(mp_target, target_branch)
        self.assertIsNot(None, mp_source)
        self.assertEqual(mp_source, branches.getByUrl(source_branch_url))
        self.assertEqual(BranchType.REMOTE, mp_source.branch_type)
        self.assertEqual(mp_target.product, mp_source.product)
        self.assertEqual('suffix', mp_source.name)

    def test_acquireBranchesForProposalRemoteSourceDupeName(self):
        """CodeHandler._acquireBranchesForProposal creates names safely.

        When creating a new branch, it uses the suffix of the url as a branch
        name seed.  If there is already a branch with that name, it appends
        a numeric suffix.
        """
        target_branch = self.factory.makeBranch()
        source_branch_url = 'http://example.com/suffix'
        md = self.makeMergeDirective(
            source_branch_url=source_branch_url, target_branch=target_branch)
        branches = getUtility(IBranchSet)
        submitter = self.factory.makePerson()
        duplicate_branch = self.factory.makeBranch(
            product=target_branch.product, name='suffix', owner=submitter)
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual('suffix-1', mp_source.name)

    def test_findMergeDirectiveAndComment(self):
        """findMergeDirectiveAndComment works."""
        md = self.makeMergeDirective()
        message = self.factory.makeSignedMessage(
            body='Hi!\n', attachment_contents=''.join(md.to_lines()),
            force_transfer_encoding=True)
        code_handler = CodeHandler()
        comment, md2 = code_handler.findMergeDirectiveAndComment(message)
        self.assertEqual('Hi!\n', comment)
        self.assertEqual(md.revision_id, md2.revision_id)
        self.assertEqual(md.target_branch, md2.target_branch)

    def test_findMergeDirectiveAndCommentEmptyBody(self):
        """findMergeDirectiveAndComment handles empty message bodies.

        Empty message bodies are returned verbatim.
        """
        md = self.makeMergeDirective()
        message = self.factory.makeSignedMessage(
            body='', attachment_contents=''.join(md.to_lines()))
        code_handler = CodeHandler()
        comment, md2 = code_handler.findMergeDirectiveAndComment(message)
        self.assertEqual('', comment)

    def test_findMergeDirectiveAndCommentNoMergeDirective(self):
        """findMergeDirectiveAndComment handles missing merge directives.

        MissingMergeDirective is raised when no merge directive is present.
        """
        md = self.makeMergeDirective()
        message = self.factory.makeSignedMessage(body='Hi!\n')
        code_handler = CodeHandler()
        self.assertRaises(MissingMergeDirective,
            code_handler.findMergeDirectiveAndComment, message)

    def makeMergeDirectiveEmail(self, body='Hi!\n'):
        """Create an email with a merge directive attached.

        :param body: The message body to use for the email.
        :return: message, source_branch, target_branch
        """
        target_branch = self.factory.makeBranch()
        source_branch = self.factory.makeBranch(product=target_branch.product)
        md = self.makeMergeDirective(source_branch, target_branch)
        message = self.factory.makeSignedMessage(body=body,
            subject='My subject', attachment_contents=''.join(md.to_lines()))
        return message, source_branch, target_branch

    def test_processMergeProposal(self):
        """processMergeProposal creates a merge proposal and comment."""
        message, source_branch, target_branch = self.makeMergeDirectiveEmail()
        code_handler = CodeHandler()
        bmp, comment = code_handler.processMergeProposal(message)
        self.assertEqual(source_branch, bmp.source_branch)
        self.assertEqual(target_branch, bmp.target_branch)
        self.assertEqual('Hi!\n', comment.message.text_contents)
        self.assertEqual('My subject', comment.message.subject)

    def test_processMergeProposalEmptyMessage(self):
        """processMergeProposal handles empty message bodies.

        Messages with empty bodies produce merge proposals only, not
        comments.
        """
        message, source_branch, target_branch = (
            self.makeMergeDirectiveEmail(body=' '))
        code_handler = CodeHandler()
        bmp, comment = code_handler.processMergeProposal(message)
        self.assertEqual(source_branch, bmp.source_branch)
        self.assertEqual(target_branch, bmp.target_branch)
        self.assertIs(None, comment)
        self.assertEqual(0, bmp.all_comments.count())

    def test_processWithMergeDirectiveEmail(self):
        """process creates a merge proposal from a merge directive email."""
        message, source, target = self.makeMergeDirectiveEmail()
        code_handler = CodeHandler()
        self.assertEqual(0, source.landing_targets.count())
        code_handler.process(message, 'merge@code.launchpad.net', None)
        self.assertEqual(target, source.landing_targets[0].target_branch)


    def test_getVoteNoCommand(self):
        """getVote returns None, None when no command is supplied."""
        # XXX: change this to check commands from body
        mail = self.factory.makeSignedMessage(body='')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, None)
        self.assertEqual(vote_tag, None)



class TestVoteEmailCommand(TestCase):
    """Test the vote and tag processing of the VoteEmailCommand."""

    # We don't need no stinking layer.

    def setUp(self):
        class FakeExecutionContext:
            vote = None
            vote_tag = None
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
            self.assertIs(None, self.context.vote_tag)
        else:
            self.assertEqual(expected_tag, self.context.vote_tag)

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


class TestMaloneHandler(TestCaseWithFactory):
    """Test that the Malone/bugs handler works."""

    layer = LaunchpadFunctionalLayer

    def test_getCommandsEmpty(self):
        """getCommands returns an empty list for messages with no command."""
        message = self.factory.makeSignedMessage()
        handler = MaloneHandler()
        self.assertEqual([], handler.getCommands(message))

    def test_getCommandsBug(self):
        """getCommands returns a reasonable list if commands are specified."""
        message = self.factory.makeSignedMessage(body=' bug foo')
        handler = MaloneHandler()
        commands = handler.getCommands(message)
        self.assertEqual(1, len(commands))
        self.assertTrue(isinstance(commands[0], BugEmailCommand))
        self.assertEqual('bug', commands[0].name)
        self.assertEqual(['foo'], commands[0].string_args)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite('canonical.launchpad.mail.handlers'))
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
