# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewMessage"""

import unittest

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import CodeReviewVote
from canonical.launchpad.testing import TestCaseWithFactory

class TestCodeReviewMessage(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'foo.bar@canonical.com')
        self.bmp = self.factory.makeBranchMergeProposal()
        self.submitter = self.factory.makePerson(password='password')
        self.reviewer = self.factory.makePerson(password='password')
        self.bmp2 = self.factory.makeBranchMergeProposal()

    def test_createRootMessage(self):
        message = self.bmp.createMessage(
            self.submitter, 'Message subject', 'Message content')
        self.assertEqual(None, message.vote)
        self.assertEqual(self.submitter, message.message.owner)
        self.assertEqual(message, self.bmp.root_message)
        self.assertEqual('Message subject', message.message.subject)
        self.assertEqual('Message content', message.message.chunks[0].content)

    def test_createReplyMessage(self):
        message = self.bmp.createMessage(
            self.submitter, 'Message subject', 'Message content')
        reply = self.bmp.createMessage(
            self.reviewer, 'Reply subject', 'Reply content',
            CodeReviewVote.ABSTAIN, message)
        self.assertEqual(message, self.bmp.root_message)
        self.assertEqual(message.message.id, reply.message.parent.id)
        self.assertEqual(message.message, reply.message.parent)
        self.assertEqual('Reply subject', reply.message.subject)
        self.assertEqual('Reply content', reply.message.chunks[0].content)
        self.assertEqual(CodeReviewVote.ABSTAIN, reply.vote)

    def test_createNoParentMessage(self):
        message = self.bmp.createMessage(
            self.submitter, 'Message subject', 'Message content')
        new_message = self.bmp.createMessage(
            self.reviewer, 'New subject', 'New content',
            CodeReviewVote.ABSTAIN)
        self.assertEqual(
            self.bmp.root_message.message, new_message.message.parent)

    def test_replyWithWrongMergeProposal(self):
        message = self.bmp.createMessage(
            self.submitter, 'Message subject', 'Message content')
        self.assertRaises(AssertionError, self.bmp2.createMessage,
                          self.reviewer, 'Reply subject', 'Reply content',
                          CodeReviewVote.ABSTAIN, message)

    def test_createNotifies(self):
        """Creating a CodeReviewMessage should trigger a notification."""
        result, event = self.assertNotifies(SQLObjectCreatedEvent,
            self.bmp.createMessage, self.submitter, 'Message subject',
            'Message content')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
