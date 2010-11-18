# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for recipe build listings."""

__metaclass__ = type


from datetime import (
    datetime,
    timedelta,
    )
from pytz import UTC

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.testing.layers import DatabaseFunctionalLayer
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
            self, num_records=1, num_records_outside_epoch=0):
        """Create some recipe build records.

        :param num_records: the number of records within the time window of
         30 days which will be displayed in the view.
        :param num_records_outside_epoch: the number of records outside the
         time window which should not be displayed.
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

        result = []
        for x in range(num_records+num_records_outside_epoch):
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
            if x >= num_records:
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

            if x < num_records:
                result.append(rbr)
        import transaction
        transaction.commit()
        return result


class TestRecipeBuildView(TestCaseWithFactory, RecipeBuildsTestMixin):

    layer = DatabaseFunctionalLayer

    def test_recipebuildrecords(self):
        records = self._makeRecipeBuildRecords(10, 5)
        login(ANONYMOUS)
        root = getUtility(ILaunchpadRoot)
        view = create_initialized_view(root, "+daily-builds", rootsite='code')
        # It's easier to do it this way than sorted() since __lt__ doesn't
        # work properly on zope proxies.
        self.assertEqual(10, view.dailybuilds.count())
        self.assertEqual(set(records), set(view.dailybuilds))


class TestRecipeBuildListing(BrowserTestCase, RecipeBuildsTestMixin):

    layer = DatabaseFunctionalLayer

    def _test_recipebuild_listing(self, no_login=False):
        [record] = self._makeRecipeBuildRecords(1, 5)
        naked_recipebuild = removeSecurityProxy(record.recipebuild)
        naked_distribution = removeSecurityProxy(
            naked_recipebuild.distribution)
        root = getUtility(ILaunchpadRoot)
        text = self.getMainText(root, '+daily-builds', no_login)
        expected_text = """
            Recently Completed Daily Recipe Builds
            .*
            Source Package
            Recipe
            Recipe Owner
            Archive
            Most Recent Build Time
            %s
            %s
            %s
            %s
            %s
            %s
            """ % (naked_distribution.displayname,
                  record.sourcepackagename,
                  naked_recipebuild.recipe.name,
                  record.recipeowner.displayname,
                  record.archive.displayname,
                  record.most_recent_build_time.strftime('%Y-%m-%d %H:%M:%S'))

        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

    def test_recipebuild_listing_no_records(self):
        root = getUtility(ILaunchpadRoot)
        text = self.getMainText(root, '+daily-builds')
        expected_text = """
            No recently completed daily builds found.
            """
        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

    def test_recipebuild_listing_anonymous(self):
        self._test_recipebuild_listing(no_login=True)

    def test_recipebuild_listing_with_user(self):
        self._test_recipebuild_listing()
