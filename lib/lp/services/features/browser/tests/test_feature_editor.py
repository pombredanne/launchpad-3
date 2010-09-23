# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature rule editor"""

__metaclass__ = type


from testtools.matchers import (
    Equals,
    )

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

    def getFeaturePageBrowser(self):
        root = getUtility(ILaunchpadRoot)
        url = canonical_url(root,
            view_name='+feature-rules')
        return self.getUserBrowser(url)

    def test_feature_page_default_value(self):
        """No rules in the sampledata gives no content in the page"""
        browser = self.getFeaturePageBrowser()
        textarea = browser.getControl(name="feature_rules")
        # and by default, since there are no rules in the sample data, it's
        # empty
        self.assertThat(textarea.value, Equals(''))

    def test_feature_page_from_database(self):
        model.addFeatureFlagRules([
            ('default', 'ui.icing', u'3.0', 100),
            ('beta_user', 'ui.icing', u'4.0', 300),
            ])
        browser = self.getFeaturePageBrowser()
        textarea = browser.getControl(name="feature_rules")
        self.assertThat(textarea.value, Equals("""\
default\tui.icing\t3.0\t100
beta_user\tui.icing\t4.0\t300
"""))

    def test_feature_page_submit_changes(self):
        # XXX: read/write mode not supported yet
        return
        ## new_value = 'beta_user 10 some_key some value with spaces'
        ## browser = self.getFeaturePageBrowser()
        ## textarea = browser.getControl(name="feature_rules")
        ## textarea.value = new_value
        ## browser.getControl(name="submit").click()
        ## self.assertThat(textarea.value.replace('\t', ' '),
        ##     Equals(new_value))


    # TODO: test that for unauthorized or anonymous users, the page works
    # (including showing the active rules) but the textarea is readonly and
    # there is no submit button.
    #
    # TODO: test that you can submit it and it changes the database.
