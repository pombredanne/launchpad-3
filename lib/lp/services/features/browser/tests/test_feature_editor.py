# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature rule editor"""

__metaclass__ = type


from zope.component import getUtility

from canonical.launchpad.interfaces import ILaunchpadRoot
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    BrowserTestCase, TestCase, TestCaseWithFactory, login_person,
    person_logged_in, time_counter)

from lp.services.features.browser import FeatureControlView
from lp.services.features.flags import FeatureController


class TestFeatureControlPage(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_feature_page_anonymous_readonly(self):
        # Anonymous users can see the feature control page, but can't change
        # anything.
        root = getUtility(ILaunchpadRoot)
        url = canonical_url(root,
            view_name='+features')
        browser = self.getUserBrowser(url)
        textarea = browser.getControl(name="feature_rules")
        # and by default, since there are no rules in the sample data, it's
        # empty
        self.assertEquals(textarea.value, '')
