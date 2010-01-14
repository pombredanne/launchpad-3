# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the `SourcePackageRecipe` content type."""

__metaclass__ = type
__all__ = [
    'SourcePackageRecipe',
    ]

from storm.locals import Int, Reference, Store, Storm, Unicode

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.component import IComponentSet
from lp.archiveuploader.permission import check_upload_to_archive
from lp.soyuz.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe, ISourcePackageRecipeSource)
from lp.soyuz.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildSource)
from lp.soyuz.model.sourcepackagerecipedata import _SourcePackageRecipeData


class NonPPABuildRequest(Exception):
    """A build was requested to a non-PPA and this is currently unsupported."""


class SourcePackageRecipe(Storm):
    """See `ISourcePackageRecipe` and `ISourcePackageRecipeSource`."""

    __storm_table__ = 'SourcePackageRecipe'

    implements(ISourcePackageRecipe)
    classProvides(ISourcePackageRecipeSource)

    id = Int(primary=True)

    date_created = UtcDateTimeCol(notNull=True)
    date_last_modified = UtcDateTimeCol(notNull=True)

    owner_id = Int(name='owner', allow_none=True)
    owner = Reference(owner_id, 'Person.id')

    registrant_id = Int(name='registrant', allow_none=True)
    registrant = Reference(registrant_id, 'Person.id')

    distroseries_id = Int(name='distroseries', allow_none=True)
    distroseries = Reference(distroseries_id, 'DistroSeries.id')

    sourcepackagename_id = Int(name='sourcepackagename', allow_none=True)
    sourcepackagename = Reference(
        sourcepackagename_id, 'SourcePackageName.id')

    name = Unicode(allow_none=True)

    @property
    def _recipe_data(self):
        return Store.of(self).find(
            _SourcePackageRecipeData,
            _SourcePackageRecipeData.sourcepackage_recipe == self).one()

    def _get_builder_recipe(self):
        """Accesses of the recipe go to the _SourcePackageRecipeData."""
        return self._recipe_data.getRecipe()

    def _set_builder_recipe(self, value):
        """Setting of the recipe goes to the _SourcePackageRecipeData."""
        self._recipe_data.setRecipe(value)

    builder_recipe = property(_get_builder_recipe, _set_builder_recipe)

    def getReferencedBranches(self):
        """See `ISourcePackageRecipe.getReferencedBranches`."""
        return self._recipe_data.getReferencedBranches()

    @staticmethod
    def new(registrant, owner, distroseries, sourcepackagename, name,
            builder_recipe):
        """See `ISourcePackageRecipeSource.new`."""
        store = IMasterStore(SourcePackageRecipe)
        sprecipe = SourcePackageRecipe()
        _SourcePackageRecipeData(builder_recipe, sprecipe)
        sprecipe.registrant = registrant
        sprecipe.owner = owner
        sprecipe.distroseries = distroseries
        sprecipe.sourcepackagename = sourcepackagename
        sprecipe.name = name
        store.add(sprecipe)
        return sprecipe

    def requestBuild(self, archive, distroseries, requester, pocket):
        if archive.purpose != ArchivePurpose.PPA:
            raise NonPPABuildRequest
        component = getUtility(IComponentSet)["multiverse"]
        reject_reason = check_upload_to_archive(requester, distroseries,
                self.sourcepackagename, archive, component, pocket)
        if reject_reason is not None:
            raise reject_reason
        sourcepackage = distroseries.getSourcePackage(self.sourcepackagename)
        build = getUtility(ISourcePackageRecipeBuildSource).new(sourcepackage,
                self, requester, archive)
        build.createBuildQueueEntry()
        return build
