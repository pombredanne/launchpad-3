# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []


from storm.locals import Int, Reference, Unicode

from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol

from lp.soyuz.interfaces.sourcepackagerecipe import ISourcePackageRecipe

class SourcePackageRecipe:
    __storm_table__ = 'SourcePackageRecipe'
    implements(ISourcePackageRecipe)

    id = Int(primary=True)

    date_last_modified = UtcDateTimeCol(notNull=True)

    owner_id = Int(name='owner', allow_none=True)
    owner = Reference(owner_id, 'Person.id')
    registrant_id = Int(name='registrant', allow_none=True)
    registrant = Reference(registrant_id, 'Person.id')

    name = Unicode(allow_none=True)

    recipe_data_id = Int(name='recipe_data', allow_none=True)
    recipe_data = Reference(recipe_data_id, 'SourcePackageRecipeData.id')
