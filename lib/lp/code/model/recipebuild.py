# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'RecipeBuildRecord',
    'RecipeBuildRecordSet',
    ]

from collections import namedtuple
from datetime import (
    datetime,
    timedelta,
    )

import pytz
from storm.expr import (
    Desc,
    Join,
    Max,
    Select,
    )
from storm import Undef

from zope.interface import implements

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.interfaces.lpstorm import ISlaveStore
from canonical.launchpad.webapp.publisher import canonical_url

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.code.interfaces.recipebuild import IRecipeBuildRecordSet
from lp.code.model.sourcepackagerecipebuild import SourcePackageRecipeBuild
from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
from lp.services.database.stormexpr import CountDistinct
from lp.registry.model.person import Person
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


class RecipeBuildRecord(namedtuple(
    'RecipeBuildRecord',
    """sourcepackagename, recipeowner, archive, recipe,
        most_recent_build_time""")):

    def __new__(cls, sourcepackagename, recipeowner, archive, recipe,
                most_recent_build_time):
        # Ensure that a valid (not None) recipe is used. This may change in
        # future if we support build records with no recipe.
        assert recipe is not None, "RecipeBuildRecord requires a recipe."
        self = super(RecipeBuildRecord, cls).__new__(
            cls, sourcepackagename, recipeowner, archive, recipe,
            most_recent_build_time)
        return self

    # We need to implement our own equality check since __eq__ is broken on
    # SourcePackageRecipe. It's broken there because __eq__ is broken,
    # or not supported, on storm's ReferenceSet implementation.
    def __eq__(self, other):
        return (self.sourcepackagename == other.sourcepackagename
            and self.recipeowner == other.recipeowner
            and self.recipe.name == other.recipe.name
            and self.archive == other.archive
            and self.most_recent_build_time == other.most_recent_build_time)

    def __hash__(self):
        return (
            hash(self.sourcepackagename.name) ^
            hash(self.recipeowner.name) ^
            hash(self.recipe.name) ^
            hash(self.archive.name) ^
            hash(self.most_recent_build_time))

    @property
    def distro_source_package(self):
        return self.archive.distribution.getSourcePackage(
            self.sourcepackagename)

    @property
    def recipe_name(self):
        return self.recipe.name

    @property
    def recipe_url(self):
        return canonical_url(self.recipe, rootsite='code')


class RecipeBuildRecordSet:
    """See `IRecipeBuildRecordSet`."""

    implements(IRecipeBuildRecordSet)

    def findCompletedDailyBuilds(self, epoch_days=30):
        """See `IRecipeBuildRecordSet`."""

        store = ISlaveStore(SourcePackageRecipe)
        tables = [
            SourcePackageRecipe,
            Join(SourcePackageRecipeBuild,
                 SourcePackageRecipeBuild.recipe_id ==
                 SourcePackageRecipe.id),
            Join(SourcePackageRelease,
                 SourcePackageRecipeBuild.id ==
                 SourcePackageRelease.source_package_recipe_build_id),
            Join(SourcePackageName,
                 SourcePackageRelease.sourcepackagename ==
                 SourcePackageName.id),
            Join(BinaryPackageBuild,
                 BinaryPackageBuild.source_package_release_id ==
                    SourcePackageRelease.id),
            Join(PackageBuild,
                 PackageBuild.id ==
                 BinaryPackageBuild.package_build_id),
            Join(BuildFarmJob,
                 BuildFarmJob.id ==
                 PackageBuild.build_farm_job_id),
        ]

        where = [BuildFarmJob.status == BuildStatus.FULLYBUILT,
                    SourcePackageRecipe.build_daily]
        if epoch_days is not None:
            epoch = datetime.now(pytz.UTC) - timedelta(days=epoch_days)
            where.append(BuildFarmJob.date_finished >= epoch)

        # We include SourcePackageName directly in the query instead of just
        # selecting its id and fetching the objects later. This is because
        # SourcePackageName only has an id and and a name and we use the name
        # for the order by so there's no benefit in introducing another query
        # for eager fetching later. If SourcePackageName gets new attributes,
        # this can be re-evaluated.
        result_set = store.using(*tables).find(
                (SourcePackageRecipe.id,
                    SourcePackageName,
                    Max(BuildFarmJob.date_finished),
                    ),
                *where
            ).group_by(
                SourcePackageRecipe.id,
                SourcePackageName,
            ).order_by(
                SourcePackageName.name,
                Desc(Max(BuildFarmJob.date_finished)),
            )

        def _makeRecipeBuildRecord(values):
            (recipe_id, sourcepackagename, date_finished) = values
            recipe = store.get(SourcePackageRecipe, recipe_id)
            return RecipeBuildRecord(
                sourcepackagename, recipe.owner,
                recipe.daily_build_archive, recipe,
                date_finished)

        to_recipes_ids = lambda rows: [row[0] for row in rows]

        def eager_load_recipes(recipe_ids):
            if not recipe_ids:
                return []
            return list(store.find(
                SourcePackageRecipe,
                SourcePackageRecipe.id.is_in(recipe_ids)))

        def eager_load_owners(recipes):
            owner_ids = set(recipe.owner_id for recipe in recipes)
            owner_ids.discard(None)
            if not owner_ids:
                return
            list(store.find(Person, Person.id.is_in(owner_ids)))

        def eager_load_archives(recipes):
            archive_ids = set(
            recipe.daily_build_archive_id for recipe in recipes)
            archive_ids.discard(None)
            if not archive_ids:
                return
            list(store.find(Archive, Archive.id.is_in(archive_ids)))

        def _prefetchRecipeBuildData(rows):
            recipe_ids = set(to_recipes_ids(rows))
            recipe_ids.discard(None)
            recipes = eager_load_recipes(recipe_ids)
            eager_load_owners(recipes)
            eager_load_archives(recipes)

        return RecipeBuildRecordResultSet(
            result_set, _makeRecipeBuildRecord,
            pre_iter_hook=_prefetchRecipeBuildData)


class RecipeBuildRecordResultSet(DecoratedResultSet):
    """A ResultSet which can count() queries with group by."""

    def count(self, expr=Undef, distinct=True):
        """This count() knows how to handle result sets with group by."""

        # We don't support distinct=False for this result set
        select = Select(
            columns=CountDistinct(self.result_set._group_by),
            tables = self.result_set._tables,
            where = self.result_set._where,
            )
        result = self.result_set._store.execute(select)
        return result.get_one()[0]
