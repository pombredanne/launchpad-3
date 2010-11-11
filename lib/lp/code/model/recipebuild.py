# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'RecipeBuildRecord',
    'RecipeBuildRecordSet',
    ]

from contextlib import contextmanager

from storm.expr import (
    compile,
    EXPR,
    Expr,
    Join,
    Max,
    Select)
from storm import Undef
from storm.store import ResultSet

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
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


@contextmanager
def user_result_set(store, user_result_set):
    """ Allow a user specified ResultSet to be used with a Storm Store."""
    orig_resultset_factory = store._result_set_factory
    store._result_set_factory = user_result_set
    try:
        yield
    finally:
        store._result_set_factory = orig_resultset_factory


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

        with user_result_set(store, RecipeBuildRecordResultSet):
            store._result_set_factory = RecipeBuildRecordResultSet
            result_set = store.using(*tables).find(
                    (SourcePackageName.id,
                        Person.id,
                        SourcePackageRecipeBuild.id,
                        Archive.id,
                        Max(BuildFarmJob.date_finished),
                        ),
                    BuildFarmJob.status == BuildStatus.FULLYBUILT,
                    SourcePackageRecipe.build_daily,
                ).group_by(
                    SourcePackageName.id,
                    Person.id,
                    SourcePackageRecipeBuild.id,
                    Archive.id,
                ).order_by(
                    SourcePackageName.id,
                    Person.id,
                    SourcePackageRecipeBuild.id,
                    Archive.id,
                    )
            return result_set


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


class RecipeBuildRecordResultSet(ResultSet):

    count_columns = (
        SourcePackageName.id,
        Person.id,
        SourcePackageRecipeBuild.id,
        Archive.id,
    )

    def count(self, expr=Undef, distinct=True):
        # We don't support distinct=False for this result set
        select = Select(
            columns=CountDistinct(self.count_columns),
            tables = self._tables,
            where = self._where,
            )
        result = self._store.execute(select)
        return result.get_one()[0]

    def _load_objects(self, result, values):
        values = super(
           RecipeBuildRecordResultSet, self)._load_objects(result, values)
        return self._makeRecipeBuildRecord(*values)

    def _makeRecipeBuildRecord(self, *values):
        recipeowner = self._store.get(Person, values[1])
        recipe_build = self._store.get(SourcePackageRecipeBuild, values[2])
        archive = self._store.get(Archive, values[3])
        sourcepackagename = self._store.get(SourcePackageName, values[0])
        sp_factory = getUtility(ISourcePackageFactory)
        sourcepackage = sp_factory.new(sourcepackagename,
                                       recipe_build.distroseries)
        return RecipeBuildRecord(
            sourcepackage, recipeowner,
            recipe_build.recipe, archive,
            values[4])
