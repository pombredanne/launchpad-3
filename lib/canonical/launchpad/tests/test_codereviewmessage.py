# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewMessage"""

import unittest
from canonical.launchpad.database.branchmergeproposal import (
    BranchMergeProposal
    )
from canonical.launchpad.database.codereviewmessage import (
    CodeReviewMessage
    )
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
            None, 1, 'Message subject', 'Message content')
        self.assertEqual(1, message.vote)
        self.assertEqual(None, message.message.owner)
        self.assertEqual(message, self.bmp.conversation)
        self.assertEqual('Message subject', message.message.subject)
        self.assertEqual('Message content', message.message.chunks[0].content)

    def test_create_reply_message(self):
        message = self.bmp.createMessage(
            None, 1, 'Message subject', 'Message content')
        reply = self.bmp.createMessage(
            None, 1, 'Reply subject', 'Reply content', message)
        self.assertEqual(message, self.bmp.conversation)
        self.assertEqual(message.message.id, reply.message.parent.id)
        self.assertEqual(message.message, reply.message.parent)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
