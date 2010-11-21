# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for recipe build listings."""
from canonical.launchpad.testing.pages import find_tag_by_id, extract_text

__metaclass__ = type


from datetime import (
    datetime,
    timedelta,
    )
from pytz import UTC

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.testing.layers import (
    BaseLayer,
    DatabaseFunctionalLayer,
    )
from lp.buildmaster.enums import BuildStatus
from lp.code.model.recipebuild import RecipeBuildRecord
from lp.soyuz.enums import ArchivePurpose
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    login,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class RecipeBuildsTestMixin:

    def _makeRecipeBuildRecords(
            self, num_recent_records=1, num_records_outside_30_days=0):
        """Create some recipe build records.

        :param num_recent_records: the number of records within the time
         window of 30 days.
        :param num_records_outside_30_days: the number of records to create
         which are older than 30 days.
        """

        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        sourcepackage = self.factory.makeSourcePackage(
            sourcepackagename=sourcepackagename,
            distroseries=distroseries)
        recipeowner = self.factory.makePerson()
        recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True,
            owner=recipeowner,
            name="Recipe_"+sourcepackagename.name,
            distroseries=distroseries)

        records = []
        records_outside_30_days = []
        for x in range(num_recent_records+num_records_outside_30_days):
            # Ensure we have both ppa and primary archives
            if x%2 == 0:
                purpose = ArchivePurpose.PPA
            else:
                purpose = ArchivePurpose.PRIMARY
            archive = self.factory.makeArchive(purpose=purpose)
            sprb = self.factory.makeSourcePackageRecipeBuild(
                requester=recipeowner,
                recipe=recipe,
                archive=archive,
                sourcepackage=sourcepackage,
                distroseries=distroseries)
            spr = self.factory.makeSourcePackageRelease(
                source_package_recipe_build=sprb,
                archive=archive,
                sourcepackagename=sourcepackagename,
                distroseries=distroseries)
            binary_build = self.factory.makeBinaryPackageBuild(
                    source_package_release=spr)
            naked_build = removeSecurityProxy(binary_build)
            naked_build.queueBuild()
            naked_build.status = BuildStatus.FULLYBUILT

            from random import randrange
            offset = randrange(0, 30)
            now = datetime.now(UTC)
            if x >= num_recent_records:
                offset = 31 + offset
            naked_build.date_finished = (
                now - timedelta(days=offset))
            naked_build.date_started = (
                naked_build.date_finished - timedelta(minutes=5))
            rbr = RecipeBuildRecord(
                removeSecurityProxy(sourcepackagename),
                removeSecurityProxy(recipeowner),
                removeSecurityProxy(archive),
                removeSecurityProxy(sprb),
                naked_build.date_finished.replace(tzinfo=None))

            if x < num_recent_records:
                records.append(rbr)
            else:
                records_outside_30_days.append(rbr)
        import transaction
        transaction.commit()
        return records, records_outside_30_days


class TestRecipeBuildView(TestCaseWithFactory, RecipeBuildsTestMixin):

    layer = DatabaseFunctionalLayer

    def test_recipebuildrecords(self):
        records, records_outside_30_days = self._makeRecipeBuildRecords(10, 5)
        login(ANONYMOUS)
        root = getUtility(ILaunchpadRoot)
        view = create_initialized_view(root, "+daily-builds", rootsite='code')
        # It's easier to do it this way than sorted() since __lt__ doesn't
        # work properly on zope proxies.
        self.assertEqual(15, view.dailybuilds.count())
        # By default, all build records will be included in the view.
        records.extend(records_outside_30_days)
        self.assertEqual(set(records), set(view.dailybuilds))


class TestRecipeBuildListing(BrowserTestCase, RecipeBuildsTestMixin):

    layer = DatabaseFunctionalLayer

    def _extract_view_text(self, recipe_build_record):
        naked_recipebuild = removeSecurityProxy(
            recipe_build_record.recipebuild)
        naked_distribution = removeSecurityProxy(
            naked_recipebuild.distribution)
        text = """
            %s
            %s
            %s
            %s
            %s
            %s
            """ % (naked_distribution.displayname,
                  recipe_build_record.sourcepackagename,
                  naked_recipebuild.recipe.name,
                  recipe_build_record.recipeowner.displayname,
                  recipe_build_record.archive.displayname,
                  recipe_build_record.most_recent_build_time.strftime(
                      '%Y-%m-%d %H:%M:%S'))
        return text

    def _test_recipebuild_listing(self, no_login=False):
        [record], records_outside_30_days = (
            self._makeRecipeBuildRecords(1, 5))
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
        root = getUtility(ILaunchpadRoot)
        text = self.getMainText(root, '+daily-builds', rootsite='code')
        expected_text = """
            No recently completed daily builds found.
            """
        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

    def test_recipebuild_listing_anonymous(self):
        self._test_recipebuild_listing(no_login=True)

    def test_recipebuild_listing_with_user(self):
        self._test_recipebuild_listing()

    def test_recipebuild_url(self):
        root_url = BaseLayer.appserver_root_url(facet='code')
        user_browser = self.getUserBrowser("%s/+daily-builds" % root_url)
        self.assertEqual(
            user_browser.url, "%s/+daily-builds" % root_url)

    def test_recentbuild_filter(self):
        login(ANONYMOUS)
        records, records_outside_30_days = self._makeRecipeBuildRecords(3, 2)
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
        records, records_outside_30_days = self._makeRecipeBuildRecords(3, 2)
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
