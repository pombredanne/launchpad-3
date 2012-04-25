# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lazr.restful.interfaces import IJSONRequestCache
from zope.security.proxy import removeSecurityProxy

from lp.bugs.browser.bug import BugView
from lp.registry.enums import InformationType
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    login,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer


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

    def test_information_type(self):
        self.bug.transitionToInformationType(
            InformationType.USERDATA, self.bug.owner)
        self.assertEqual(
            self.bug.information_type.title, self.view.information_type)
        
    def test_userdata_shown_as_private(self):
        # When the display_userdata_as_private feature flag is enabled, the
        # information_type is shown as 'Private'.
        self.bug.transitionToInformationType(
            InformationType.USERDATA, self.bug.owner)
        feature_flag = {
            'disclosure.display_userdata_as_private.enabled': 'on'}
        with FeatureFixture(feature_flag):
            view = BugView(self.bug, LaunchpadTestRequest())
            self.assertEqual('Private', view.information_type)

    def test_proprietary_hidden(self):
        # When the proprietary_information_type.disabled feature flag is
        # enabled, it isn't in the JSON request cache.
        feature_flag = {
            'disclosure.proprietary_information_type.disabled': 'on'}
        with FeatureFixture(feature_flag):
            view = BugView(self.bug, LaunchpadTestRequest())
            view.initialize()
            cache = IJSONRequestCache(view.request)
            expected = [
                InformationType.PUBLIC, InformationType.UNEMBARGOEDSECURITY,
                InformationType.EMBARGOEDSECURITY, InformationType.USERDATA]
            self.assertContentEqual(expected, [
                type['value']
                for type in cache.objects['information_types']])
