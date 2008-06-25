# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewComment"""

import unittest

from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import CodeReviewVote
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import LaunchpadFunctionalLayer

class TestCodeReviewComment(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'foo.bar@canonical.com')
        self.bmp = self.factory.makeBranchMergeProposal()
        self.submitter = self.factory.makePerson(password='password')
        self.reviewer = self.factory.makePerson(password='password')
        self.bmp2 = self.factory.makeBranchMergeProposal()

    def test_createRootComment(self):
        comment = self.bmp.createComment(
            self.submitter, 'Message subject', 'Message content')
        self.assertEqual(None, comment.vote)
        self.assertEqual(None, comment.vote_tag)
        self.assertEqual(self.submitter, comment.message.owner)
        self.assertEqual(comment, self.bmp.root_comment)
        self.assertEqual('Message subject', comment.message.subject)
        self.assertEqual('Message content', comment.message.chunks[0].content)

    def test_createReplyComment(self):
        comment = self.bmp.createComment(
            self.submitter, 'Message subject', 'Message content')
        reply = self.bmp.createComment(
            self.reviewer, 'Reply subject', 'Reply content',
            CodeReviewVote.ABSTAIN, 'My tag', comment)
        self.assertEqual(comment, self.bmp.root_comment)
        self.assertEqual(comment.message.id, reply.message.parent.id)
        self.assertEqual(comment.message, reply.message.parent)
        self.assertEqual('Reply subject', reply.message.subject)
        self.assertEqual('Reply content', reply.message.chunks[0].content)
        self.assertEqual(CodeReviewVote.ABSTAIN, reply.vote)
        self.assertEqual('My tag', reply.vote_tag)

    def test_createNoParentComment(self):
        comment = self.bmp.createComment(
            self.submitter, 'Message subject', 'Message content')
        new_comment = self.bmp.createComment(
            self.reviewer, 'New subject', 'New content',
            CodeReviewVote.ABSTAIN)
        self.assertEqual(
            self.bmp.root_comment.message, new_comment.message.parent)

    def test_replyWithWrongMergeProposal(self):
        comment = self.bmp.createComment(
            self.submitter, 'Message subject', 'Message content')
        self.assertRaises(AssertionError, self.bmp2.createComment,
                          self.reviewer, 'Reply subject', 'Reply content',
                          CodeReviewVote.ABSTAIN, 'My tag', comment)

    def test_createCommentFromMessage(self):
        """Creating a CodeReviewComment from a message works."""
        message = self.factory.makeMessage(owner=self.submitter)
        comment = self.bmp.createCommentFromMessage(message, None, None)
        self.assertEqual(message, comment.message)

    def test_createCommentFromMessageNotifies(self):
        """Creating a CodeReviewComment should trigger a notification."""
        message = self.factory.makeMessage()
        self.assertNotifies(
            SQLObjectCreatedEvent, self.bmp.createCommentFromMessage, message,
            None, None)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
