# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature rule editor"""

__metaclass__ = type


from testtools.matchers import Equals
from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.features.browser.edit import FeatureControlView
from lp.services.features.rulesource import StormFeatureRuleSource
from lp.testing.matchers import Contains

from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    )


class FauxForm:
    """The simplest fake form, used for testing."""
    context = None


class TestFeatureControlPage(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def getUserBrowserAsTeamMember(self, teams):
        """Make a TestBrowser authenticated as a team member.

        :param teams: List of teams to add the new user to.
        """
        # XXX MartinPool 2010-09-23 bug=646563: To make a UserBrowser, you
        # must know the password; we can't get the password for an existing
        # user so we have to make a new one.
        user = self.factory.makePerson(password='test')
        for team in teams:
            with person_logged_in(team.teamowner):
                team.addMember(user, reviewer=team.teamowner)
        return self.getUserBrowser(url=None, user=user, password='test')

    def getUserBrowserAsAdmin(self):
        """Make a new TestBrowser logged in as an admin user."""
        url = self.getFeatureRulesViewURL()
        admin_team = getUtility(ILaunchpadCelebrities).admin
        return self.getUserBrowserAsTeamMember([admin_team])

    def getFeatureRulesViewURL(self):
        root = getUtility(ILaunchpadRoot)
        return canonical_url(root, view_name='+feature-rules')

    def getFeatureRulesEditURL(self):
        root = getUtility(ILaunchpadRoot)
        return canonical_url(root, view_name='+feature-rules')

    def test_feature_page_default_value(self):
        """No rules in the sampledata gives no content in the page"""
        browser = self.getUserBrowserAsAdmin()
        browser.open(self.getFeatureRulesViewURL())
        textarea = browser.getControl(name="field.feature_rules")
        # and by default, since there are no rules in the sample data, it's
        # empty
        self.assertThat(textarea.value, Equals(''))

    def test_feature_page_from_database(self):
        StormFeatureRuleSource().setAllRules([
            ('ui.icing', 'default', 100, u'3.0'),
            ('ui.icing', 'beta_user', 300, u'4.0'),
            ])
        browser = self.getUserBrowserAsAdmin()
        browser.open(self.getFeatureRulesViewURL())
        textarea = browser.getControl(name="field.feature_rules")
        self.assertThat(
            textarea.value.replace('\r', ''),
            Equals(
                "ui.icing\tbeta_user\t300\t4.0\n"
                "ui.icing\tdefault\t100\t3.0\n"))

    def test_feature_rules_anonymous_unauthorized(self):
        browser = self.getUserBrowser()
        self.assertRaises(Unauthorized,
            browser.open,
            self.getFeatureRulesViewURL())

    def test_feature_rules_plebian_unauthorized(self):
        """Logged in, but not a member of any interesting teams."""
        browser = self.getUserBrowserAsTeamMember([])
        self.assertRaises(Unauthorized,
            browser.open,
            self.getFeatureRulesViewURL())

    def test_feature_page_submit_changes(self):
        """Submitted changes show up in the db."""
        browser = self.getUserBrowserAsAdmin()
        browser.open(self.getFeatureRulesEditURL())
        new_value = 'beta_user some_key 10 some value with spaces'
        textarea = browser.getControl(name="field.feature_rules")
        textarea.value = new_value
        browser.getControl(name="field.actions.change").click()
        self.assertThat(
            list(StormFeatureRuleSource().getAllRulesAsTuples()),
            Equals([
                ('beta_user', 'some_key', 10, 'some value with spaces'),
                ]))

    def test_change_message(self):
        """Submitting shows a message that the changes have been applied."""
        browser = self.getUserBrowserAsAdmin()
        browser.open(self.getFeatureRulesEditURL())
        textarea = browser.getControl(name="field.feature_rules")
        textarea.value = 'beta_user some_key 10 some value with spaces'
        browser.getControl(name="field.actions.change").click()
        self.assertThat(
            browser.contents,
            Contains('Your changes have been applied'))

    def test_change_diff(self):
        """Submitting shows a diff of the changes."""
        browser = self.getUserBrowserAsAdmin()
        browser.open(self.getFeatureRulesEditURL())
        browser.getControl(name="field.feature_rules"
            ).value = 'beta_user some_key 10 some value with spaces'
        browser.getControl(name="field.actions.change").click()
        browser.getControl(name="field.feature_rules"
            ).value = 'beta_user some_key 10 another value with spaces'
        browser.getControl(name="field.actions.change").click()
        # The diff is formatted nicely using CSS.
        self.assertThat(
            browser.contents,
            Contains('<td class="diff-added text">'))
        # Removed rules are displayed as being removed.
        self.assertThat(
            browser.contents.replace('\t', ' '),
            Contains('-beta_user some_key 10 some value with spaces'))
        # Added rules are displayed as being added.
        self.assertThat(
            browser.contents.replace('\t', ' '),
            Contains('+beta_user some_key 10 another value with spaces'))

    def test_feature_page_submit_change_to_empty(self):
        """Correctly handle submitting an empty value."""
        # Zope has the quirk of conflating empty with absent; make sure we
        # handle it properly.
        browser = self.getUserBrowserAsAdmin()
        browser.open(self.getFeatureRulesEditURL())
        new_value = ''
        textarea = browser.getControl(name="field.feature_rules")
        textarea.value = new_value
        browser.getControl(name="field.actions.change").click()
        self.assertThat(
            list(StormFeatureRuleSource().getAllRulesAsTuples()),
            Equals([]))

    def test_feature_page_submit_change_when_unauthorized(self):
        """Correctly handling attempted value changes when not authorized."""
        # When a change is submitted but the user is unauthorized, an
        # exception is raised.

        view = FeatureControlView(None, None)
        self.assertRaises(
            Unauthorized,
            view.change_action.success_handler, FauxForm(), None, None)
