# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401,W1001

"""Implementation of the `SourcePackageRecipe` content type."""

__metaclass__ = type
__all__ = [
    'SourcePackageRecipe',
    ]

from bzrlib.plugins.builder.recipe import RecipeParser
from lazr.delegates import delegates

from storm.locals import (
    Bool, Desc, Int, Reference, ReferenceSet, Store, Storm,
    Unicode)

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.config import config
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore, IStore

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.errors import BuildAlreadyPending, TooManyBuilds
from lp.code.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe, ISourcePackageRecipeSource,
    ISourcePackageRecipeData)
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildSource)
from lp.code.model.sourcepackagerecipebuild import SourcePackageRecipeBuild
from lp.code.model.sourcepackagerecipedata import SourcePackageRecipeData
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

    def __str__(self):
        return '%s/%s' % (self.owner.name, self.name)

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

    is_stale = Bool()

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
    def new(registrant, owner, name, builder_recipe, description,
            distroseries=None, daily_build_archive=None, build_daily=False):
        """See `ISourcePackageRecipeSource.new`."""
        store = IMasterStore(SourcePackageRecipe)
        sprecipe = SourcePackageRecipe()
        SourcePackageRecipeData(builder_recipe, sprecipe)
        sprecipe.registrant = registrant
        sprecipe.owner = owner
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
        return store.find(cls, cls.is_stale == True, cls.build_daily == True)

    @staticmethod
    def exists(owner, name):
        """See `ISourcePackageRecipeSource.new`."""
        store = IMasterStore(SourcePackageRecipe)
        recipe = store.find(
            SourcePackageRecipe,
            SourcePackageRecipe.owner == owner,
            SourcePackageRecipe.name == name).one()
        if recipe:
            return True
        else:
            return False

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

    def isOverQuota(self, requester, distroseries):
        """See `ISourcePackageRecipe`."""
        return SourcePackageRecipeBuild.getRecentBuilds(
            requester, self, distroseries).count() >= 5

    def requestBuild(self, archive, requester, distroseries, pocket,
                     manual=False):
        """See `ISourcePackageRecipe`."""
        if not config.build_from_branch.enabled:
            raise ValueError('Source package recipe builds disabled.')
        if archive.purpose != ArchivePurpose.PPA:
            raise NonPPABuildRequest
        component = getUtility(IComponentSet)["multiverse"]
        reject_reason = archive.checkUpload(
            requester, self.distroseries, None, component, pocket)
        if reject_reason is not None:
            raise reject_reason
        if self.isOverQuota(requester, distroseries):
            raise TooManyBuilds(self, distroseries)
        pending = IStore(self).find(SourcePackageRecipeBuild,
            SourcePackageRecipeBuild.recipe_id == self.id,
            SourcePackageRecipeBuild.distroseries_id == distroseries.id,
            SourcePackageRecipeBuild.archive_id == archive.id,
            SourcePackageRecipeBuild.buildstate == BuildStatus.NEEDSBUILD)
        if pending.any() is not None:
            raise BuildAlreadyPending(self, distroseries)

        build = getUtility(ISourcePackageRecipeBuildSource).new(distroseries,
            self, requester, archive)
        build.queueBuild(build)
        if manual:
            build.buildqueue_record.manualScore(1000)
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

    def getLastBuild(self):
        """See `ISourcePackageRecipeBuild`."""
        store = Store.of(self)
        result = store.find(
            SourcePackageRecipeBuild, SourcePackageRecipeBuild.recipe == self)
        result.order_by(Desc(SourcePackageRecipeBuild.datebuilt))
        return result.first()

    def getMedianBuildDuration(self):
        """Return the median duration of builds of this recipe."""
        store = IStore(self)
        result = store.find(
            SourcePackageRecipeBuild.buildduration,
            SourcePackageRecipeBuild.recipe==self.id,
            SourcePackageRecipeBuild.buildduration != None)
        result.order_by(Desc(SourcePackageRecipeBuild.buildduration))
        count = result.count()
        if count == 0:
            return None
        return result[count/2]
