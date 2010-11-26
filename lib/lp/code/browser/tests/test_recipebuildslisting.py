# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for recipe build listings."""

__metaclass__ = type


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.testing.layers import (
    BaseLayer,
    DatabaseFunctionalLayer,
    )
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
        records, records_outside_30_days = (
            self.factory.makeRecipeBuildRecords(10, 5))
        login(ANONYMOUS)
        root = getUtility(ILaunchpadRoot)
        view = create_initialized_view(root, "+daily-builds", rootsite='code')
        # It's easier to do it this way than sorted() since __lt__ doesn't
        # work properly on zope proxies.
        self.assertEqual(15, view.dailybuilds.count())
        # By default, all build records will be included in the view.
        records.extend(records_outside_30_days)
        self.assertEqual(set(records), set(view.dailybuilds))


class TestRecipeBuildListing(BrowserTestCase):
    """Browser tests for the Recipe Build Listing page."""
    layer = DatabaseFunctionalLayer

    def _extract_view_text(self, recipe_build_record):
        naked_recipebuild = removeSecurityProxy(
            recipe_build_record.recipebuild)
        naked_distribution = removeSecurityProxy(
            naked_recipebuild.distribution)
        text = '\n'.join(str(item) for item in (
                naked_distribution.displayname,
                recipe_build_record.sourcepackagename.name,
                naked_recipebuild.recipe.name,
                recipe_build_record.recipeowner.displayname,
                recipe_build_record.archive.displayname,
                recipe_build_record.most_recent_build_time.strftime(
                    '%Y-%m-%d %H:%M:%S')))
        return text

    def _test_recipebuild_listing(self, no_login=False):
        # Test the text on a recipe build listing page is as expected.
        [record], records_outside_30_days = (
            self.factory.makeRecipeBuildRecords(1, 5))
        record_text = self._extract_view_text(record)
        root = getUtility(ILaunchpadRoot)
        text = self.getMainText(
            root, '+daily-builds', rootsite='code', no_login=no_login)
        expected_text = """
            Most Recently Completed Daily Recipe Builds
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

    def test_recipebuild_url(self):
        # Check the browser URL is as expected.
        root_url = BaseLayer.appserver_root_url(facet='code')
        user_browser = self.getUserBrowser("%s/+daily-builds" % root_url)
        self.assertEqual(
            user_browser.url, "%s/+daily-builds" % root_url)

    def test_recentbuild_filter(self):
        login(ANONYMOUS)
        records, records_outside_30_days = (
            self.factory.makeRecipeBuildRecords(3, 2))
        records_text = set()
        for record in records:
            record_text = self._extract_view_text(
                record).replace(' ', '').replace('\n', '')
            records_text.add(record_text)

        root_url = BaseLayer.appserver_root_url(facet='code')
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

    def test_all_records_filter(self):
        login(ANONYMOUS)
        records, records_outside_30_days = (
            self.factory.makeRecipeBuildRecords(3, 2))
        records.extend(records_outside_30_days)
        records_text = set()
        for record in records:
            record_text = self._extract_view_text(
                record).replace(' ', '').replace('\n', '')
            records_text.add(record_text)

        root_url = BaseLayer.appserver_root_url(facet='code')
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
