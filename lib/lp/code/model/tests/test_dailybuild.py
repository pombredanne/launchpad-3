import datetime

import transaction

from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    DatabaseFunctionalLayer,
    )
from lp.buildmaster.enums import BuildStatus
from lp.testing import TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory


class TestRevisionCreationDate(TestCaseWithFactory):
    """Test that RevisionSet.new won't create revisions with future dates."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRevisionCreationDate, self).setUp()


    def runTest(self):

        factory = LaunchpadObjectFactory()

        recipeowner = factory.makePerson()
        archive = factory.makeArchive()
        recipe = factory.makeSourcePackageRecipe(
            build_daily=True, owner=recipeowner)
        sprb = factory.makeSourcePackageRecipeBuild(
            status = BuildStatus.FULLYBUILT,
            requester=recipeowner,
            recipe=recipe,
            duration=datetime.timedelta(minutes=5))
        spr = factory.makeSourcePackageRelease(
            source_package_recipe_build=sprb
            )

        #pb = factory.makePackageBuild()
        bpb = factory.makeBinaryPackageBuild(
            source_package_release=spr, status = BuildStatus.FULLYBUILT)

        bfj = factory.makeSourcePackageRecipeBuildJob(recipe_build = sprb,
                                                       sourcename="fred")

        transaction.commit()

  