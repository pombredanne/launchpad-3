# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []


from storm.locals import Int, Reference, Storm, Unicode

from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from lp.soyuz.interfaces.sourcepackagerecipe import ISourcePackageRecipe


class SourcePackageRecipe(Storm):
    __storm_table__ = 'SourcePackageRecipe'
    implements(ISourcePackageRecipe)

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
    recipe_data = Reference(recipe_data_id, 'SourcePackageRecipeData.id')

    @classmethod
    def new(self, registrant, owner, distroseries, sourcepackagename, name,
            recipe):
        store = IMasterStore(SourcePackageRecipe)
        recipe = SourcePackageRecipe()
        recipe.registrant = registrant
        recipe.owner = owner
        recipe.distroseries = distroseries
        recipe.sourcepackagename = sourcepackagename
        recipe.name = name
        store.add(recipe)
        return recipe
