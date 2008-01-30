# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewMessage"""

import unittest
from canonical.launchpad.database.branchmergeproposal import (
    BranchMergeProposal
    )
from canonical.launchpad.database.codereviewmessage import (
    CodeReviewMessage
    )
from canonical.launchpad.database.person import Person
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.ftests import login

class TestCodeReviewMessage(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        login('test@canonical.com')
        self.bmp = BranchMergeProposal(source_branchID=5, registrantID=5,
                                       target_branchID=6,
                                       dependent_branchID=None)

    def test_create_root_message(self):
        message = self.bmp.createMessage(
            Person.get(1), 1, 'Message subject', 'Message content')
        self.assertEqual(1, message.vote)
        self.assertEqual(Person.get(1), message.message.owner)
        self.assertEqual(message, self.bmp.conversation)
        self.assertEqual('Message subject', message.message.subject)
        self.assertEqual('Message content', message.message.chunks[0].content)

    def test_create_reply_message(self):
        message = self.bmp.createMessage(
            Person.get(1), 1, 'Message subject', 'Message content')
        reply = self.bmp.createMessage(
            Person.get(1), 1, 'Reply subject', 'Reply content', message)
        self.assertEqual(message, self.bmp.conversation)
        self.assertEqual(message.message.id, reply.message.parent.id)
        self.assertEqual(message.message, reply.message.parent)
        self.assertEqual('Reply subject', reply.message.subject)
        self.assertEqual('Reply content', reply.message.chunks[0].content)

    def test_create_no_parent_message(self):
        message = self.bmp.createMessage(
            Person.get(1), 1, 'Message subject', 'Message content')
        new_message = self.bmp.createMessage(
            Person.get(1), 1, 'New subject', 'New content')
        self.assertEqual(
            self.bmp.conversation.message, new_message.message.parent)

    def test_reply_with_wrong_merge_proposal(self):
        message = self.bmp.createMessage(
            Person.get(1), 1, 'Message subject', 'Message content')
        self.bmp2 = BranchMergeProposal(source_branchID=5, registrantID=5,
                                        target_branchID=6,
                                        dependent_branchID=None)
        self.assertRaises(AssertionError, self.bmp2.createMessage,
                          Person.get(1), 1, 'Reply subject', 'Reply content',
                          message)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
