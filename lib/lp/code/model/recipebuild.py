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
    compile,
    EXPR,
    Expr,
    Join,
    Max,
    Select)
from storm import Undef

from zope.interface import implements

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.interfaces.lpstorm import ISlaveStore

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.code.interfaces.recipebuild import IRecipeBuildRecordSet
from lp.code.model.sourcepackagerecipebuild import SourcePackageRecipeBuild
from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
from lp.registry.model.person import Person
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


class RecipeBuildRecord(namedtuple(
    'RecipeBuildRecord',
    """sourcepackagename, recipeowner, archive, recipe,
        most_recent_build_time""")):
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


class RecipeBuildRecordSet:
    """See `IRecipeBuildRecordSet`."""

    implements(IRecipeBuildRecordSet)

    def findCompletedDailyBuilds(self, epoch_days=30):
        """See `IRecipeBuildRecordSet`."""

        store = ISlaveStore(SourcePackageRecipe)
        tables = [
            SourcePackageRecipe,
            Join(Person,
                 Person.id == SourcePackageRecipe.owner_id),
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
            Join(Archive,
                 Archive.id ==
                 SourcePackageRecipe.daily_build_archive_id),
            Join(BuildFarmJob,
                 BuildFarmJob.id ==
                 PackageBuild.build_farm_job_id),
        ]

        where = [BuildFarmJob.status == BuildStatus.FULLYBUILT,
                    SourcePackageRecipe.build_daily]
        if epoch_days is not None:
            epoch = datetime.now(pytz.UTC) - timedelta(days=epoch_days)
            where.append(BuildFarmJob.date_finished >= epoch)

        result_set = store.using(*tables).find(
                (SourcePackageName,
                    Person,
                    SourcePackageRecipe,
                    Archive,
                    Max(BuildFarmJob.date_finished),
                    ),
                *where
            ).group_by(
                SourcePackageName,
                Person,
                SourcePackageRecipe,
                Archive,
            ).order_by(
                SourcePackageName.name,
                Person.name,
                Archive.name,
                )

        def _makeRecipeBuildRecord(values):
            (sourcepackagename, recipeowner, recipe, archive,
                date_finished) = values
            return RecipeBuildRecord(
                sourcepackagename, recipeowner,
                archive, recipe,
                date_finished)

        return RecipeBuildRecordResultSet(
            result_set, _makeRecipeBuildRecord)


# XXX: wallyworld 2010-11-26 bug=675377: storm's Count() implementation is
# broken for distinct with > 1 column
class CountDistinct(Expr):

    __slots__ = ("columns")

    def __init__(self, columns):
        self.columns = columns


@compile.when(CountDistinct)
def compile_countdistinct(compile, countselect, state):
    state.push("context", EXPR)
    col = compile(countselect.columns)
    state.pop()
    return "count(distinct(%s))" % col


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
