# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for recipe build listings."""

__metaclass__ = type


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    login,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestRecipeBuildView(TestCaseWithFactory):
    """Tests for `CompletedDailyBuildsView`."""

    layer = DatabaseFunctionalLayer

    def test_recipebuildrecords(self):
        # Check that the view is created from the url and loads the expected
        # records.
        records = self.factory.makeRecipeBuildRecords(10, 5)
        login(ANONYMOUS)
        root = getUtility(ILaunchpadRoot)
        view = create_initialized_view(root, "+daily-builds", rootsite='code')
        # It's easier to do it this way than sorted() since __lt__ doesn't
        # work properly on zope proxies.
        self.assertEqual(10, view.dailybuilds.count())
        self.assertEqual(set(records), set(view.dailybuilds))


class TestRecipeBuildListing(BrowserTestCase):
    """Browser tests for the Recipe Build Listing page."""
    layer = DatabaseFunctionalLayer

    def _test_recipebuild_listing(self, no_login=False):
        # Test the content of the listing when there is data.
        [record] = self.factory.makeRecipeBuildRecords(1, 5)
        naked_recipebuild = removeSecurityProxy(record.recipebuild)
        naked_distribution = removeSecurityProxy(
            naked_recipebuild.distribution)
        root = getUtility(ILaunchpadRoot)
        text = self.getMainText(
            root, '+daily-builds', rootsite='code', no_login=no_login)
        expected_text = '\n'.join(str(item) for item in (
                """Most Recently Completed Daily Recipe Builds
                Source Package
                Recipe
                Recipe Owner
                Archive
                Most Recent Build Time""",
                naked_distribution.displayname,
                record.sourcepackagename.name,
                naked_recipebuild.recipe.name,
                record.recipeowner.displayname,
                record.archive.displayname,
                record.most_recent_build_time.strftime('%Y-%m-%d %H:%M:%S')))
        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

    def test_recipebuild_listing_no_records(self):
        # Test the expected text when there is no data.
        root = getUtility(ILaunchpadRoot)
        text = self.getMainText(root, '+daily-builds', rootsite='code')
        expected_text = "No recently completed daily builds found."
        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

    def test_recipebuild_listing_anonymous(self):
        # Ensure we can see the listing when we are not logged in.
        self._test_recipebuild_listing(no_login=True)

    def test_recipebuild_listing_with_user(self):
        # Ensure we can see the listing when we are logged in.
        self._test_recipebuild_listing()

    def test_recipebuild_url(self):
        # Check the browser URL is as expected.
        root_url = self.layer.appserver_root_url(facet='code')
        user_browser = self.getUserBrowser("%s/+daily-builds" % root_url)
        self.assertEqual(
            user_browser.url, "%s/+daily-builds" % root_url)
