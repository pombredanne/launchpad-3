# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.browser.bug import BugView
from lp.testing import TestCaseWithFactory


class TestBugView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugView, self).setUp()
        login('test@canonical.com')
        self.bug = self.factory.makeBug()
        self.view = BugView(self.bug, LaunchpadTestRequest())

    def test_regular_attachments_dont_include_invalid_records(self):
        # As reported in bug 542274, rendering the link to bug
        # attchments that do not have a LibraryFileContent record,
        # leads to an OOPS. Ensure that such attachments do not appear
        # in BugViewMixin.regular_attachments and BugViewMixin.patches.
        self.factory.makeBugAttachment(
            bug=self.bug, description="regular attachment", is_patch=False)
        attachment = self.factory.makeBugAttachment(
            bug=self.bug, description="bad regular attachment",
            is_patch=False)
        removeSecurityProxy(attachment.libraryfile).content = None
        self.assertEqual(
            ['regular attachment'],
            [attachment['attachment'].title
             for attachment in self.view.regular_attachments])

    def test_patches_dont_include_invalid_records(self):
        # As reported in bug 542274, rendering the link to bug
        # attchments that do not have a LibraryFileContent record,
        # leads to an OOPS. Ensure that such attachments do not appear
        # in BugViewMixin.regular_attachments and BugViewMixin.patches.
        self.factory.makeBugAttachment(
            bug=self.bug, description="patch", is_patch=True)
        patch = self.factory.makeBugAttachment(
            bug=self.bug, description="bad patch", is_patch=True)
        removeSecurityProxy(patch.libraryfile).content = None
        self.assertEqual(
            ['patch'],
            [attachment['attachment'].title
             for attachment in self.view.patches])
