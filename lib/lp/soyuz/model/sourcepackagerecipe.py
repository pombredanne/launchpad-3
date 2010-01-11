# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the `SourcePackageRecipe` content type."""

__metaclass__ = type
__all__ = [
    'SourcePackageBuild',
    'SourcePackageRecipe',
    ]

from storm.locals import Int, Reference, Storm, Unicode

from zope.interface import classProvides, implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from lp.soyuz.interfaces.sourcepackagerecipe import (
    ISourcePackageBuild, ISourcePackageRecipe, ISourcePackageRecipeSource)
from lp.soyuz.model.sourcepackagerecipedata import _SourcePackageRecipeData


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
    sourcepackagename = Reference(sourcepackagename_id, 'SourcePackageName.id')

    name = Unicode(allow_none=True)

    _recipe_data_id = Int(name='recipe_data', allow_none=True)
    _recipe_data = Reference(_recipe_data_id, '_SourcePackageRecipeData.id')

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

    @classmethod
    def new(self, registrant, owner, distroseries, sourcepackagename, name,
            builder_recipe):
        """See `ISourcePackageRecipeSource.new`."""
        store = IMasterStore(SourcePackageRecipe)
        sprecipe = SourcePackageRecipe()
        sprecipe._recipe_data = _SourcePackageRecipeData(builder_recipe)
        sprecipe.registrant = registrant
        sprecipe.owner = owner
        sprecipe.distroseries = distroseries
        sprecipe.sourcepackagename = sourcepackagename
        sprecipe.name = name
        store.add(sprecipe)
        return sprecipe


class SourcePackageBuild:

    implements(ISourcePackageBuild)

    def __init__(self):
        self.build_log = None
        self.build_state = None
        self.build_duration = None
        self.builder = None
        self.date_built = None
        self.date_created = None
        self.date_first_dispatched = None
        self.distroseries = None
        self.manifest = None
        self.recipe = None
        self.requester = None
        self.sourcepackagename = None
