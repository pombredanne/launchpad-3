# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'RecipeBuildRecord',
    'RecipeBuildRecordSet',
    ]

import collections

from storm.expr import (
    compile,
    EXPR,
    Expr,
    Join,
    Max,
    Select)
from storm import Undef

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    SLAVE_FLAVOR,
    )

from lp.code.interfaces.recipebuild import (
    IRecipeBuildRecord,
    IRecipeBuildRecordSet,
    )
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.code.model.sourcepackagerecipebuild import SourcePackageRecipeBuild
from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
from lp.registry.interfaces.sourcepackage import ISourcePackageFactory
from lp.registry.model.person import Person
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


class RecipeBuildRecord():
    """See `IRecipeBuildRecord`."""

    implements(IRecipeBuildRecord)

    def __init__(
            self, sourcepackage, recipeowner, recipe, archive,
            most_recent_build_time):
        self.sourcepackage = sourcepackage
        self.archive = archive
        self.recipeowner = recipeowner
        self.recipe = recipe
        self.most_recent_build_time = most_recent_build_time

    def __eq__(self, other):
        return (self.sourcepackage == other.sourcepackage and
                self.archive == other.archive and
                self.recipe == other.recipe and
                self.recipeowner == other.recipeowner and
                self.most_recent_build_time == other.most_recent_build_time)

    def __hash__(self):
        return (hash(self.recipe) ^ hash(self.sourcepackage)
                ^ hash(self.archive))

    def __repr__(self):
        return ("<Recipe Build for %r, sp=%r, a=%r>"
            % (self.recipe, self.sourcepackage, self.archive))


class RecipeBuildRecordSet:
    """See `IRecipeBuildRecordSet`."""

    implements(IRecipeBuildRecordSet)

    def findCompletedDailyBuilds(self):
        """See `IRecipeBuildRecordSet`."""

        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
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
                 PackageBuild.archive_id),
            Join(BuildFarmJob,
                 BuildFarmJob.id ==
                 PackageBuild.build_farm_job_id),
        ]

        def _makeRecipeBuildRecord(values):
            (sourcepackagename, recipeowner, recipe_build, archive,
                date_finished) = values
            sp_factory = getUtility(ISourcePackageFactory)
            sourcepackage = sp_factory.new(sourcepackagename,
                                           recipe_build.distroseries)

#            RecipeBuildRec = collections.namedtuple(
#                'lp_code_model_recipebuild_RecipeBuildRec',
#                'sourcepackage, recipeowner, recipe, archive, most_recent_build_time')
#
#            return RecipeBuildRec(
#                sourcepackage, recipeowner,
#                recipe_build.recipe, archive,
#                date_finished)

            return RecipeBuildRecord(
                sourcepackage, recipeowner,
                recipe_build.recipe, archive,
                date_finished)
        
        result_set = store.using(*tables).find(
                (SourcePackageName,
                    Person,
                    SourcePackageRecipeBuild,
                    Archive,
                    Max(BuildFarmJob.date_finished),
                    ),
                BuildFarmJob.status == BuildStatus.FULLYBUILT,
                SourcePackageRecipe.build_daily,
            ).group_by(
                SourcePackageName,
                Person,
                SourcePackageRecipeBuild,
                Archive,
            ).order_by(
                SourcePackageName.name,
                Person.name,
                Archive.name,
                )
        return RecipeBuildRecordResultSet(
            result_set, _makeRecipeBuildRecord)

# XXX: wallyworld Nov 2010
# storm's Count() implementation is broken for distinct
# see bug 675377
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

    count_columns = (
        SourcePackageName.id,
        Person.id,
        SourcePackageRecipeBuild.id,
        Archive.id,
    )

    def count(self, expr=Undef, distinct=True):
        """This count() knows how to handle result sets with group by."""

        # We don't support distinct=False for this result set
        select = Select(
            columns=CountDistinct(self.count_columns),
            tables = self.result_set._tables,
            where = self.result_set._where,
            )
        result = self.result_set._store.execute(select)
        return result.get_one()[0]
