# Copyright 2005, 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.config import config
from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.database import MessageSet
from canonical.launchpad.mail.handlers import (
    CodeHandler, InvalidBranchMergeProposalAddress, mail_handlers)
from canonical.launchpad.testing import TestCaseWithFactory


class TestCodeHandler(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_get(self):
        handler = mail_handlers.get(config.vhost.code.hostname)
        self.assertIsInstance(handler, CodeHandler)

    def test_process(self):
        code_handler = CodeHandler()
        mail = self.factory.makeSignedMessage('<my-id>')
        bmp = self.factory.makeBranchMergeProposal()
        email_addr = bmp.address
        self.assertTrue(code_handler.process(
            mail, email_addr, None), "Succeeded, but didn't return True")
        message = MessageSet().get('<my-id>')

    def test_process_failure(self):
        code_handler = CodeHandler()
        mail = self.factory.makeSignedMessage('<my-id>')
        self.assertFalse(code_handler.process(
            mail, 'foo@bar.com', None),
            "Failed, but didn't return False")

    def test_getBranchMergeProposal(self):
        bmp = self.factory.makeBranchMergeProposal()
        code_handler = CodeHandler()
        bmp2 = code_handler.getBranchMergeProposal(bmp.address)
        self.assertEqual(bmp, bmp2)

    def test_getBranchMergeProposalInvalid(self):
        code_handler = CodeHandler()
        self.assertRaises(InvalidBranchMergeProposalAddress,
                          code_handler.getBranchMergeProposal, '')
        self.assertRaises(InvalidBranchMergeProposalAddress,
                          code_handler.getBranchMergeProposal, 'mp+abc@')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite('canonical.launchpad.mail.handlers'))
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
