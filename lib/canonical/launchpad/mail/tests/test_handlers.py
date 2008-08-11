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
from canonical.launchpad.mail.commands import BugEmailCommand
from canonical.launchpad.mail.handlers import (
    CodeHandler, InvalidBranchMergeProposalAddress, InvalidVoteString,
    mail_handlers, MaloneHandler, NonLaunchpadTarget, parse_commands)
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
            ' supported: abstain, approve, disapprove.',
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
        self.assertEqual('EBAILIWICK', bmp.all_comments[0].vote_tag)

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
        self.assertEqual('EBAILIWICK', comment.vote_tag)
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
        expected_body = ('Vote: Abstain EBAILIWICK\n'
                         ' vote Abstain EBAILIWICK\n'
                         '-- \n'
                         '%s\n'
                         'You are subscribed to branch %s.' %
                         (canonical_url(bmp), bmp.source_branch.unique_name))
        self.assertEqual(expected_body, notification.get_payload(decode=True))

    def test_getVoteNoCommand(self):
        """getVote returns None, None when no command is supplied."""
        mail = self.factory.makeSignedMessage(body='')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, None)
        self.assertEqual(vote_tag, None)

    def test_getVoteNoArgs(self):
        """getVote returns None, None when no arguments are supplied."""
        mail = self.factory.makeSignedMessage(body=' vote')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, None)
        self.assertEqual(vote_tag, None)

    def test_getVoteOneArg(self):
        """getVote returns vote, None when only a vote is supplied."""
        mail = self.factory.makeSignedMessage(body=' vote apPRoVe')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.APPROVE)
        self.assertEqual(vote_tag, None)

    def test_getVoteDisapprove(self):
        """getVote returns disapprove when it is specified."""
        mail = self.factory.makeSignedMessage(body=' vote dIsAppRoVe')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.DISAPPROVE)

    def test_getVoteBadValue(self):
        """getVote returns vote, None when only a vote is supplied."""
        mail = self.factory.makeSignedMessage(body=' vote badvalue')
        self.switchDbUser(config.processmail.dbuser)
        self.assertRaises(InvalidVoteString, self.code_handler._getVote, mail)

    def test_getVoteThreeArg(self):
        """getVote returns vote, vote_tag when both are supplied."""
        mail = self.factory.makeSignedMessage(body=' vote apPRoVe DB TAG')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.APPROVE)
        self.assertEqual(vote_tag, 'DB TAG')

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

    def test_getVoteApproveAlias(self):
        """Test the approve alias of +1."""
        mail = self.factory.makeSignedMessage(body=' vote +1')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.APPROVE)

    def test_getVoteAbstainAlias(self):
        """Test the abstain alias of 0."""
        mail = self.factory.makeSignedMessage(body=' vote 0')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.ABSTAIN)

    def test_getVoteAbstainAliasPlus(self):
        """Test the abstain alias of +0."""
        mail = self.factory.makeSignedMessage(body=' vote +0')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.ABSTAIN)

    def test_getVoteAbstainAliasMinus(self):
        """Test the abstain alias of -0."""
        mail = self.factory.makeSignedMessage(body=' vote -0')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.ABSTAIN)

    def test_getVoteDisapproveAlias(self):
        """Test the disapprove alias of -1."""
        mail = self.factory.makeSignedMessage(body=' vote -1')
        self.switchDbUser(config.processmail.dbuser)
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.DISAPPROVE)

    @staticmethod
    def make_merge_directive(source_branch=None, target_branch=None,
        source_branch_url=None, target_branch_url=None):
        if source_branch_url is None:
            source_branch_url = (config.codehosting.supermirror_root +
                                 source_branch.unique_name)
        if target_branch_url is None:
            target_branch_url = (config.codehosting.supermirror_root +
                                 target_branch.unique_name)
        return MergeDirective2(None, None, None, None, target_branch_url,
                               source_branch=source_branch_url)


    def test_acquireBranchesForProposal(self):
        target_branch = self.factory.makeBranch()
        source_branch = self.factory.makeBranch()
        md = self.make_merge_directive(source_branch, target_branch)
        submitter = self.factory.makePerson()
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual(mp_source, source_branch)
        self.assertEqual(mp_target, target_branch)

    def test_acquireBranchesForProposalRemoteTarget(self):
        source_branch = self.factory.makeBranch()
        md = self.make_merge_directive(source_branch,
                                       target_branch_url='http://example.com')
        submitter = self.factory.makePerson()
        self.assertRaises(NonLaunchpadTarget,
                          self.code_handler._acquireBranchesForProposal, md,
                          submitter)

    def test_acquireBranchesForProposalRemoteSource(self):
        target_branch = self.factory.makeBranch()
        source_branch_url = 'http://example.com/suffix'
        md = self.make_merge_directive(source_branch_url=source_branch_url,
                                       target_branch=target_branch)
        branches = getUtility(IBranchSet)
        self.assertEqual(None, branches.getByUrl(source_branch_url))
        submitter = self.factory.makePerson()
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual(mp_target, target_branch)
        self.assertFalse(mp_source is None)
        self.assertEqual(mp_source, branches.getByUrl(source_branch_url))
        self.assertEqual(BranchType.REMOTE, mp_source.branch_type)
        self.assertEqual(mp_target.product, mp_source.product)
        self.assertEqual('suffix', mp_source.name)

    def test_acquireBranchesForProposalRemoteSourceDupeName(self):
        target_branch = self.factory.makeBranch()
        source_branch_url = 'http://example.com/suffix'
        md = self.make_merge_directive(source_branch_url=source_branch_url,
                                       target_branch=target_branch)
        branches = getUtility(IBranchSet)
        submitter = self.factory.makePerson()
        duplicate_branch = self.factory.makeBranch(
            product=target_branch.product, name='suffix', owner=submitter)
        mp_source, mp_target = self.code_handler._acquireBranchesForProposal(
            md, submitter)
        self.assertEqual('suffix-1', mp_source.name)


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
