# Copyright 2005, 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.config import config
from canonical.launchpad.interfaces import CodeReviewVote
from canonical.launchpad.database import MessageSet
from canonical.launchpad.mail.commands import BugEmailCommand
from canonical.launchpad.mail.handlers import (
    CodeHandler, InvalidBranchMergeProposalAddress, mail_handlers,
    MaloneHandler, parse_commands)
from canonical.launchpad.testing import TestCase, TestCaseWithFactory
from canonical.testing import LaunchpadFunctionalLayer


class TestParseCommands(TestCase):
    """Test the ParseCommands function."""

    def test_parse_commandsEmpty(self):
        """Empty messages have no commands."""
        self.assertEqual([], parse_commands('', ['command']))

    def test_parse_commandsNoIndent(self):
        """Commands with no indent are not commands."""
        self.assertEqual([], parse_commands('command', ['command']))

    def test_parse_commandsSpaceIndent(self):
        """Commands indented with spaces are recognized"""
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
        # done brooks no arguments.
        self.assertEqual(
            [('command', []), ('command', [])],
            parse_commands(' command\n done commands\n command', ['command']))


class TestCodeHandler(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.code_handler = CodeHandler()

    def test_get(self):
        handler = mail_handlers.get(config.vhost.code.hostname)
        self.assertIsInstance(handler, CodeHandler)

    def test_process(self):
        mail = self.factory.makeSignedMessage('<my-id>')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.assertTrue(self.code_handler.process(
            mail, email_addr, None), "Succeeded, but didn't return True")
        message = MessageSet().get('<my-id>')

    def test_process_failure(self):
        mail = self.factory.makeSignedMessage('<my-id>')
        self.assertFalse(self.code_handler.process(
            mail, 'foo@bar.com', None),
            "Failed, but didn't return False")

    def test_processVote(self):
        mail = self.factory.makeSignedMessage(body=' vote Abstain EBALIWICK')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.code_handler.process(mail, email_addr, None)
        self.assertEqual(CodeReviewVote.ABSTAIN, bmp.all_messages[0].vote)
        self.assertEqual('EBALIWICK', bmp.all_messages[0].vote_tag)

    def test_getVoteNoCommand(self):
        mail = self.factory.makeSignedMessage(body='')
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, None)
        self.assertEqual(vote_tag, None)

    def test_getVoteNoArgs(self):
        mail = self.factory.makeSignedMessage(body=' vote')
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, None)
        self.assertEqual(vote_tag, None)

    def test_getVoteOneArg(self):
        mail = self.factory.makeSignedMessage(body=' vote apPRoVe')
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.APPROVE)
        self.assertEqual(vote_tag, None)

    def test_getVoteDisapprove(self):
        mail = self.factory.makeSignedMessage(body=' vote dIsAppRoVe')
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.DISAPPROVE)

    def test_getVoteThreeArg(self):
        mail = self.factory.makeSignedMessage(body=' vote apPRoVe DB TAG')
        vote, vote_tag = self.code_handler._getVote(mail)
        self.assertEqual(vote, CodeReviewVote.APPROVE)
        self.assertEqual(vote_tag, 'DB TAG')

    def test_getBranchMergeProposal(self):
        bmp = self.factory.makeBranchMergeProposal()
        bmp2 = self.code_handler.getBranchMergeProposal(bmp.address)
        self.assertEqual(bmp, bmp2)

    def test_getBranchMergeProposalInvalid(self):
        self.assertRaises(InvalidBranchMergeProposalAddress,
                          self.code_handler.getBranchMergeProposal, '')
        self.assertRaises(InvalidBranchMergeProposalAddress,
                          self.code_handler.getBranchMergeProposal, 'mp+abc@')


class TestMaloneHandler(TestCaseWithFactory):
    """Test that the Malone/bugs handler works."""

    layer = LaunchpadFunctionalLayer

    def test_getCommandsEmpty(self):
        message = self.factory.makeSignedMessage()
        handler = MaloneHandler()
        self.assertEqual([], handler.getCommands(message))

    def test_getCommandsBug(self):
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
