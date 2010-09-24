# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature rule editor"""

__metaclass__ = type


from testtools.matchers import (
    Equals,
    )

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities,
    ILaunchpadRoot,
    )
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    BrowserTestCase,
    TestCase,
    TestCaseWithFactory,
    celebrity_logged_in,
    login_person,
    person_logged_in,
    time_counter,
    )

from lp.services.features.browser import FeatureControlView
from lp.services.features.flags import FeatureController
from lp.services.features.model import addFeatureFlagRules


class TestFeatureControlPage(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def getUserBrowserAsTeamMember(self, url, team):
        """Make a TestBrowser authenticated as a team member."""
        # XXX bug=646563: To make a UserBrowser, you must know the password.  This
        # should be separated out into test infrastructure.  -- mbp 20100923
        user = self.factory.makePerson(password='test')
        with person_logged_in(team.teamowner):
            team.addMember(user, reviewer=team.teamowner)
        return self.getUserBrowser(url, user=user, password='test')

    def getFeaturePageBrowserAsAdmin(self):
        root = getUtility(ILaunchpadRoot)
        url = canonical_url(root, view_name='+feature-rules')
        admin_team = getUtility(ILaunchpadCelebrities).admin
        return self.getUserBrowserAsTeamMember(url, admin_team)

    def test_feature_page_default_value(self):
        """No rules in the sampledata gives no content in the page"""
        browser = self.getFeaturePageBrowserAsAdmin()
        textarea = browser.getControl(name="feature_rules")
        # and by default, since there are no rules in the sample data, it's
        # empty
        self.assertThat(textarea.value, Equals(''))

    def test_feature_page_from_database(self):
        addFeatureFlagRules([
            ('default', 'ui.icing', u'3.0', 100),
            ('beta_user', 'ui.icing', u'4.0', 300),
            ])
        browser = self.getFeaturePageBrowserAsAdmin()
        textarea = browser.getControl(name="feature_rules")
        self.assertThat(textarea.value.replace('\r', ''), Equals("""\
ui.icing\tbeta_user\t300\t4.0
ui.icing\tdefault\t100\t3.0\
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
