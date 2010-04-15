# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401

"""Implementation of the `SourcePackageRecipe` content type."""

__metaclass__ = type
__all__ = [
    'SourcePackageRecipe',
    ]

from lazr.delegates import delegates

from storm.locals import (
    Bool, Desc, Int, Reference, ReferenceSet, Store, Storm, Unicode)

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from lp.archiveuploader.permission import check_upload_to_archive
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
    distroseries_id = Int(name='distroseries', allow_none=False)


class SourcePackageRecipe(Storm):
    """See `ISourcePackageRecipe` and `ISourcePackageRecipeSource`."""

    __storm_table__ = 'SourcePackageRecipe'

    implements(ISourcePackageRecipe)

    classProvides(ISourcePackageRecipeSource)

    delegates(ISourcePackageRecipeData, context='_recipe_data')

    id = Int(primary=True)

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

    @staticmethod
    def new(registrant, owner, distroseries, sourcepackagename, name,
            builder_recipe, description):
        """See `ISourcePackageRecipeSource.new`."""
        store = IMasterStore(SourcePackageRecipe)
        sprecipe = SourcePackageRecipe()
        SourcePackageRecipeData(builder_recipe, sprecipe)
        sprecipe.registrant = registrant
        sprecipe.owner = owner
        sprecipe.sourcepackagename = sourcepackagename
        sprecipe.name = name
        for distroseries_item in distroseries:
            sprecipe.distroseries.add(distroseries_item)
        sprecipe.description = description
        store.add(sprecipe)
        return sprecipe

    def destroySelf(self):
        store = Store.of(self)
        self.distroseries.clear()
        for instruction in self._recipe_data.instructions:
            store.remove(instruction)
        self.getBuilds(pending=True).remove()
        self.getBuilds(pending=False).remove()
        store.remove(self._recipe_data)
        store.remove(self)

    def requestBuild(self, archive, requester, distroseries, pocket):
        """See `ISourcePackageRecipe`."""
        if archive.purpose != ArchivePurpose.PPA:
            raise NonPPABuildRequest
        component = getUtility(IComponentSet)["multiverse"]
        reject_reason = check_upload_to_archive(
            requester, distroseries, self.sourcepackagename,
            archive, component, pocket)
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
