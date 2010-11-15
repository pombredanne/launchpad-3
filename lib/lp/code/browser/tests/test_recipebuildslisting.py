# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for recipe build listings."""

__metaclass__ = type

import collections
import datetime

from zope.component._api import getUtility

from canonical.launchpad.interfaces.launchpad import IBazaarApplication
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.buildmaster.enums import BuildStatus
from lp.code.interfaces.recipebuild import IRecipeBuildRecordSet
from lp.code.model.recipebuild import RecipeBuildRecord
from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.enums import ArchivePurpose
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    login,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import (
    create_initialized_view
    )


class RecipeBuildsTestMixin:

    def _makeRecipeBuildRecords(self, nr_records):
        recipeowner = self.factory.makePerson()
        result = []
        with person_logged_in(recipeowner):
            for x in range(0, nr_records):
                sourcepackagename = self.factory.makeSourcePackageName()
                distroseries = self.factory.makeDistroRelease()
                sourcepackage = self.factory.makeSourcePackage(
                    sourcepackagename=sourcepackagename,
                    distroseries=distroseries)
                recipe = self.factory.makeSourcePackageRecipe(
                    build_daily=True,
                    owner=recipeowner,
                    name=sourcepackagename.name,
                    distroseries=distroseries)
                # Ensure we have both ppa and primary archives
                if x%2 == 0:
                    purpose = ArchivePurpose.PPA
                else:
                    purpose = ArchivePurpose.PRIMARY
                archive = self.factory.makeArchive(purpose=purpose)
                sprb = self.factory.makeSourcePackageRecipeBuild(
                    status = BuildStatus.FULLYBUILT,
                    requester=recipeowner,
                    recipe=recipe,
                    archive=archive,
                    sourcepackage=sourcepackage,
                    distroseries=distroseries,
                    duration=datetime.timedelta(minutes=5))
                spr = self.factory.makeSourcePackageRelease(
                    source_package_recipe_build=sprb,
                    archive=archive,
                    sourcepackagename=sourcepackagename,
                    distroseries=distroseries)
                self.factory.makeBinaryPackageBuild(
                        source_package_release=spr,
                        status = BuildStatus.FULLYBUILT)
                bfj = self.factory.makeSourcePackageRecipeBuildJob(
                        recipe_build = sprb)

#                RecipeBuildRec = collections.namedtuple(
#                    'lp_code_model_recipebuild_RecipeBuildRec',
#                    'sourcepackage, recipeowner, recipe, archive, most_recent_build_time')
#
#                rbr = RecipeBuildRec(
#                    sourcepackage, recipeowner,
#                    recipe, archive,
#                    bfj.job.date_finished)
                
                rbr = RecipeBuildRecord(
                    sourcepackage, recipeowner,
                    recipe, archive,
                    bfj.job.date_finished)

                result.append(rbr)
        return result


class TestRecipeBuildView(TestCaseWithFactory, RecipeBuildsTestMixin):

    layer = DatabaseFunctionalLayer

    def test_recipebuildrecords(self):
        records = self._makeRecipeBuildRecords(5)
        login(ANONYMOUS)
        root = getUtility(IBazaarApplication)
        view = create_initialized_view(
            root, "+daily-builds", rootsite='code')
        self.assertEqual(set(records), set(view.dailybuilds))


class TestRecipeBuildListing(BrowserTestCase, RecipeBuildsTestMixin):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        #self.user = self.factory.makePerson()
        self.user = getUtility(IPersonSet).getByName("name12")

    def test_recipebuild_listing(self):
        self._makeRecipeBuildRecords(15)
        root = getUtility(IBazaarApplication)
        text = self.getMainText(root, '+daily-builds')
        self.assertTextMatchesExpressionIgnoreWhitespace("""
                Completed Daily Recipe Builds
                .*
                Source Package
                Recipe
                Recipe Owner
                Archive
                Most Recent Build Time
                .*
                generic-string.*
                generic-string.*
                Person-name.*
                """, text)

    def test_recipebuild_listing_anonymous(self):
        self._makeRecipeBuildRecords(15)
        root = getUtility(IBazaarApplication)
        text = self.getMainText(root, '+daily-builds', no_login=True)
        self.assertTextMatchesExpressionIgnoreWhitespace("""
                Completed Daily Recipe Builds
                .*
                Source Package
                Recipe
                Recipe Owner
                Archive
                Most Recent Build Time
                .*
                generic-string.*
                generic-string.*
                Person-name.*
                """, text)
