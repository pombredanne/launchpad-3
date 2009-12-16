# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []

from storm.locals import Int, Reference, Storm, Unicode

from zope.interface import classImplements, implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from lp.soyuz.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe, ISourcePackageRecipeSource)
from lp.soyuz.model.sourcepackagerecipedata import _SourcePackageRecipeData


class SourcePackageRecipe(Storm):
    __storm_table__ = 'SourcePackageRecipe'
    implements(ISourcePackageRecipe)
    classImplements(ISourcePackageRecipeSource)

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

    recipe_data_id = Int(name='recipe_data', allow_none=True)
    recipe_data = Reference(recipe_data_id, '_SourcePackageRecipeData.id')

    def getReferencedBranches(self):
        return self.recipe_data.referenced_branches

    @classmethod
    def new(self, registrant, owner, distroseries, sourcepackagename, name,
            recipe):
        store = IMasterStore(SourcePackageRecipe)
        sprecipe = SourcePackageRecipe()
        sprecipe.recipe_data = _SourcePackageRecipeData(recipe)
        sprecipe.registrant = registrant
        sprecipe.owner = owner
        sprecipe.distroseries = distroseries
        sprecipe.sourcepackagename = sourcepackagename
        sprecipe.name = name
        store.add(sprecipe)
        return sprecipe
