# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for recipe build listings."""

__metaclass__ = type


from zope.component import getUtility

from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    login,
    TestCaseWithFactory,
    )
from lp.testing.matchers import BrowsesWithQueryLimit
from lp.testing.views import create_initialized_view


class TestRecipeBuildView(TestCaseWithFactory):
    """Tests for `CompletedDailyBuildsView`."""

    layer = DatabaseFunctionalLayer

    def test_recipebuildrecords(self):
        all_records, recent_records = (
            self.factory.makeRecipeBuildRecords(10, 5))
        login(ANONYMOUS)
        root = getUtility(ILaunchpadRoot)
        view = create_initialized_view(root, "+daily-builds", rootsite='code')
        # It's easier to do it this way than sorted() since __lt__ doesn't
        # work properly on zope proxies.
        self.assertEqual(15, view.dailybuilds.count())
        # By default, all build records will be included in the view.
        self.assertEqual(set(all_records), set(view.dailybuilds))


class TestRecipeBuildListing(BrowserTestCase):
    """Browser tests for the Recipe Build Listing page."""
    layer = DatabaseFunctionalLayer

    def _extract_view_text(self, recipe_build_record):
        text = '\n'.join(str(item) for item in (
                recipe_build_record.sourcepackagename.name,
                recipe_build_record.recipe.name,
                recipe_build_record.recipeowner.displayname,
                recipe_build_record.archive.displayname,
                recipe_build_record.most_recent_build_time.strftime(
                    '%Y-%m-%d %H:%M:%S')))
        return text

    def _test_recipebuild_listing(self, no_login=False):
        # Test the text on a recipe build listing page is as expected.
        all_records, [recent_record] = (
            self.factory.makeRecipeBuildRecords(1, 5))
        record_text = self._extract_view_text(recent_record)
        root = getUtility(ILaunchpadRoot)
        text = self.getMainText(
            root, '+daily-builds', rootsite='code', no_login=no_login)
        expected_text = """
            Packages Built Daily With Recipes
            .*
            Source Package
            Recipe
            Recipe Owner
            Archive
            Most Recent Build Time
            """ + record_text
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

    def test_recipebuild_listing_querycount(self):
        # The query count on the recipe build listing page is small enough.
        # There's a base query count of approx 30, but if the page template
        # is not set up right, the query count can increases linearly with the
        # number of records.
        self.factory.makeRecipeBuildRecords(5, 0)
        root = getUtility(ILaunchpadRoot)
        browser_query_limit = BrowsesWithQueryLimit(
            35, self.user, view_name='+daily-builds', rootsite='code')
        self.assertThat(root, browser_query_limit)

    def test_recipebuild_url(self):
        # Check the browser URL is as expected.
        root_url = self.layer.appserver_root_url(facet='code')
        user_browser = self.getUserBrowser("%s/+daily-builds" % root_url)
        self.assertEqual(
            user_browser.url, "%s/+daily-builds" % root_url)

    def test_recentbuild_filter(self):
        login(ANONYMOUS)
        all_records, recent_records = (
            self.factory.makeRecipeBuildRecords(3, 2))
        records_text = set()
        for record in recent_records:
            record_text = self._extract_view_text(
                record).replace(' ', '').replace('\n', '')
            records_text.add(record_text)

        root_url = self.layer.appserver_root_url(facet='code')
        browser = self.getUserBrowser("%s/+daily-builds" % root_url)
        status_control = browser.getControl(
            name='field.when_completed_filter')

        status_control.value = ['WITHIN_30_DAYS']
        browser.getControl('Filter').click()
        table = find_tag_by_id(browser.contents, 'daily-build-listing')

        view_records_text = set()
        for row in table.tbody.fetch('tr'):
            text = extract_text(row)
            view_records_text.add(text.replace(' ', '').replace('\n', ''))
        self.assertEquals(records_text, view_records_text)

    def test_recentbuild_filter_with_no_records(self):
        # This test ensures that the filter control works properly when the
        # filtered record set contains no records. We should be able to
        # select All again and have the page re-display all records."

        login(ANONYMOUS)
        # Create records all outside the filter time window.
        all_records, recent_records = (
            self.factory.makeRecipeBuildRecords(0, 2))
        records_text = set()
        for record in all_records:
            record_text = self._extract_view_text(
                record).replace(' ', '').replace('\n', '')
            records_text.add(record_text)

        def check_build_records(table):
            view_records_text = set()
            for row in table.tbody.fetch('tr'):
                text = extract_text(row)
                view_records_text.add(text.replace(' ', '').replace('\n', ''))
            self.assertEquals(records_text, view_records_text)

        # Initial rendering has all records.
        root_url = self.layer.appserver_root_url(facet='code')
        browser = self.getUserBrowser("%s/+daily-builds" % root_url)
        table = find_tag_by_id(browser.contents, 'daily-build-listing')
        check_build_records(table)

        # There are no filtered records.
        status_control = browser.getControl(
            name='field.when_completed_filter')
        status_control.value = ['WITHIN_30_DAYS']
        browser.getControl('Filter').click()
        table = find_tag_by_id(browser.contents, 'daily-build-listing')
        self.assertIs(None, table)

        # We can click All and see the record again.
        status_control = browser.getControl(
            name='field.when_completed_filter')
        status_control.value = ['ALL']
        browser.getControl('Filter').click()
        table = find_tag_by_id(browser.contents, 'daily-build-listing')
        check_build_records(table)

    def test_all_records_filter(self):
        login(ANONYMOUS)
        all_records, recent_records = (
            self.factory.makeRecipeBuildRecords(3, 2))
        records_text = set()
        for record in all_records:
            record_text = self._extract_view_text(
                record).replace(' ', '').replace('\n', '')
            records_text.add(record_text)

        root_url = self.layer.appserver_root_url(facet='code')
        browser = self.getUserBrowser("%s/+daily-builds" % root_url)
        status_control = browser.getControl(
            name='field.when_completed_filter')

        status_control.value = ['ALL']
        browser.getControl('Filter').click()
        table = find_tag_by_id(browser.contents, 'daily-build-listing')

        view_records_text = set()
        for row in table.tbody.fetch('tr'):
            text = extract_text(row)
            view_records_text.add(text.replace(' ', '').replace('\n', ''))
        self.assertEquals(records_text, view_records_text)

    def test_one_recipe_redirects_to_recipe_page(self):
        # Ensure that if the product or person has only one recipe, they are
        # redirected right to the recipe page.
        recipe = self.factory.makeSourcePackageRecipe()
        root_url = self.layer.appserver_root_url(facet='code')
        recipes_url = '%s/~%s/+recipes' % (root_url, recipe.owner.name)
        expected_url = canonical_url(recipe)
        browser = self.getUserBrowser(recipes_url)
        self.assertEquals(expected_url, browser.url)
