# Copyright 2006 Canonical Ltd.  All rights reserved.

import unittest

from zope.component import getUtility

from canonical.launchpad.browser.branch import BranchView
from canonical.launchpad.ftests.harness import login, logout, ANONYMOUS
from canonical.launchpad.helpers import truncate_text
from canonical.launchpad.interfaces import IBranchSet
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadFunctionalLayer


class TestBranchView(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        self.request = LaunchpadTestRequest()

    def tearDown(self):
        logout()

    def testMirrorStatusMessageIsTruncated(self):
        """mirror_status_message is truncated if the text is overly long."""
        branch = getUtility(IBranchSet).get(28)
        branch_view = BranchView(branch, self.request)
        self.assertEqual(
            truncate_text(branch.mirror_status_message,
                          branch_view.MAXIMUM_STATUS_MESSAGE_LENGTH) + ' ...',
            branch_view.mirror_status_message())

    def testMirrorStatusMessage(self):
        """mirror_status_message on the view is the same as on the branch."""
        branch = getUtility(IBranchSet).get(5)
        branch_view = BranchView(branch, self.request)
        self.assertEqual(
            branch.mirror_status_message, branch_view.mirror_status_message())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
