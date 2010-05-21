# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401,W1001

"""Implementation of the `SourcePackageRecipe` content type."""

__metaclass__ = type
__all__ = [
    'SourcePackageRecipe',
    ]

import datetime

from bzrlib.plugins.builder import RecipeParser
from lazr.delegates import delegates

from pytz import utc
from storm.locals import (
    And, Bool, Desc, Int, Not, Reference, ReferenceSet, Select, Store, Storm,
    Unicode)

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore, IStore

from lp.code.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe, ISourcePackageRecipeSource,
    ISourcePackageRecipeData)
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildSource)
from lp.code.model.branch import Branch
from lp.code.model.sourcepackagerecipebuild import SourcePackageRecipeBuild
from lp.code.model.sourcepackagerecipedata import SourcePackageRecipeData
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distroseries import DistroSeries
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.component import IComponentSet


class NonPPABuildRequest(Exception):
    """A build was requested to a non-PPA and this is currently
    unsupported."""


class _SourcePackageRecipeDistroSeries(Storm):
    """Link table for many-to-many relationship."""

    __storm_table__ = "SourcePackageRecipeDistroSeries"
    id = Int(primary=True)
    sourcepackagerecipe_id = Int(name='sourcepackagerecipe', allow_none=False)
    sourcepackage_recipe = Reference(
        sourcepackagerecipe_id, 'SourcePackageRecipe.id')
    distroseries_id = Int(name='distroseries', allow_none=False)
    distroseries = Reference(distroseries_id, 'DistroSeries.id')


class SourcePackageRecipe(Storm):
    """See `ISourcePackageRecipe` and `ISourcePackageRecipeSource`."""

    __storm_table__ = 'SourcePackageRecipe'

    implements(ISourcePackageRecipe)

    classProvides(ISourcePackageRecipeSource)

    delegates(ISourcePackageRecipeData, context='_recipe_data')

    id = Int(primary=True)

    daily_build_archive_id = Int(name='daily_build_archive', allow_none=True)
    daily_build_archive = Reference(daily_build_archive_id, 'Archive.id')

    date_created = UtcDateTimeCol(notNull=True)
    date_last_modified = UtcDateTimeCol(notNull=True)

    owner_id = Int(name='owner', allow_none=True)
    owner = Reference(owner_id, 'Person.id')

    registrant_id = Int(name='registrant', allow_none=True)
    registrant = Reference(registrant_id, 'Person.id')

    distroseries = ReferenceSet(
        id, _SourcePackageRecipeDistroSeries.sourcepackagerecipe_id,
        _SourcePackageRecipeDistroSeries.distroseries_id, DistroSeries.id)

    build_daily = Bool()

    sourcepackagename_id = Int(name='sourcepackagename', allow_none=True)
    sourcepackagename = Reference(
        sourcepackagename_id, 'SourcePackageName.id')

    @property
    def _sourcepackagename_text(self):
        return self.sourcepackagename.name

    name = Unicode(allow_none=True)
    description = Unicode(allow_none=False)

    @property
    def _recipe_data(self):
        return Store.of(self).find(
            SourcePackageRecipeData,
            SourcePackageRecipeData.sourcepackage_recipe == self).one()

    def _get_builder_recipe(self):
        """Accesses of the recipe go to the SourcePackageRecipeData."""
        return self._recipe_data.getRecipe()

    def _set_builder_recipe(self, value):
        """Setting of the recipe goes to the SourcePackageRecipeData."""
        self._recipe_data.setRecipe(value)

    builder_recipe = property(_get_builder_recipe, _set_builder_recipe)

    @property
    def base_branch(self):
        return self._recipe_data.base_branch

    def setRecipeText(self, recipe_text):
        self.builder_recipe = RecipeParser(recipe_text).parse()

    @property
    def recipe_text(self):
        return str(self.builder_recipe)

    @staticmethod
    def new(registrant, owner, sourcepackagename, name,
            builder_recipe, description, distroseries=None,
            daily_build_archive=None, build_daily=False):
        """See `ISourcePackageRecipeSource.new`."""
        store = IMasterStore(SourcePackageRecipe)
        sprecipe = SourcePackageRecipe()
        SourcePackageRecipeData(builder_recipe, sprecipe)
        sprecipe.registrant = registrant
        sprecipe.owner = owner
        sprecipe.sourcepackagename = sourcepackagename
        sprecipe.name = name
        if distroseries is not None:
            for distroseries_item in distroseries:
                sprecipe.distroseries.add(distroseries_item)
        sprecipe.description = description
        sprecipe.daily_build_archive = daily_build_archive
        sprecipe.build_daily = build_daily
        store.add(sprecipe)
        return sprecipe

    @classmethod
    def findStaleDailyBuilds(cls):
        store = IStore(cls)
        # Distroseries which have been built since the base branch was
        # modified.
        up_to_date_distroseries = Select(
            SourcePackageRecipeBuild.distroseries_id,
            And(
                SourcePackageRecipeData.sourcepackage_recipe_id ==
                SourcePackageRecipeBuild.recipe_id,
                SourcePackageRecipeData.base_branch_id == Branch.id,
                Branch.date_last_modified <
                SourcePackageRecipeBuild.datebuilt))
        return store.find(
            _SourcePackageRecipeDistroSeries, cls.build_daily == True,
            _SourcePackageRecipeDistroSeries.sourcepackagerecipe_id == cls.id,
            Not(_SourcePackageRecipeDistroSeries.distroseries_id.is_in(
                up_to_date_distroseries)))

    @classmethod
    def requestDailyBuilds(cls):
        candidates = cls.findStaleDailyBuilds()
        builds = []
        for candidate in candidates:
            recipe = candidate.sourcepackage_recipe
            builds.append(
                recipe.requestBuild(recipe.daily_build_archive, recipe.owner,
                candidate.distroseries, PackagePublishingPocket.RELEASE))
        return builds

    def destroySelf(self):
        store = Store.of(self)
        self.distroseries.clear()
        self._recipe_data.instructions.find().remove()
        def destroyBuilds(pending):
            builds = self.getBuilds(pending=pending)
            for build in builds:
                build.destroySelf()
        destroyBuilds(pending=True)
        destroyBuilds(pending=False)
        store.remove(self._recipe_data)
        store.remove(self)

    def requestBuild(self, archive, requester, distroseries, pocket):
        """See `ISourcePackageRecipe`."""
        if archive.purpose != ArchivePurpose.PPA:
            raise NonPPABuildRequest
        component = getUtility(IComponentSet)["multiverse"]
        reject_reason = archive.checkUpload(
            requester, self.distroseries, self.sourcepackagename,
            component, pocket)
        if reject_reason is not None:
            raise reject_reason

        sourcepackage = distroseries.getSourcePackage(
            self.sourcepackagename)
        build = getUtility(ISourcePackageRecipeBuildSource).new(sourcepackage,
            self, requester, archive)
        build.queueBuild()
        return build

    def getBuilds(self, pending=False):
        """See `ISourcePackageRecipe`."""
        if pending:
            clauses = [SourcePackageRecipeBuild.datebuilt == None]
        else:
            clauses = [SourcePackageRecipeBuild.datebuilt != None]
        result = Store.of(self).find(
            SourcePackageRecipeBuild, SourcePackageRecipeBuild.recipe==self,
            *clauses)
        result.order_by(Desc(SourcePackageRecipeBuild.datebuilt))
        return result
