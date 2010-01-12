# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'SourcePackageBuild',
    ]


from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from storm.locals import Int, Reference, Storm, TimeDelta

from zope.interface import classProvides, implements

from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.sourcepackagebuild import (
    ISourcePackageBuild, ISourcePackageBuildSource)


class SourcePackageBuild(Storm):

    __storm_table__ = 'SourcePackageBuild'

    implements(ISourcePackageBuild)
    classProvides(ISourcePackageBuildSource)

    id = Int(primary=True)

    build_duration = TimeDelta(name='build_duration', default=None)

    builder_id = Int(name='builder', allow_none=True)
    builder = Reference(builder_id, 'Builder.id')

    build_log_id = Int(name='build_log', allow_none=True)
    build_log = Reference(build_log_id, 'LibraryFileAlias.id')

    build_state = EnumCol(
        dbName='buildstate', notNull=True, schema=BuildStatus)

    date_created = UtcDateTimeCol(notNull=True)
    date_built = UtcDateTimeCol(notNull=True)
    date_first_dispatched = UtcDateTimeCol(notNull=True)

    distroseries_id = Int(name='distroseries', allow_none=True)
    distroseries = Reference(distroseries_id, 'DistroSeries.id')

    sourcepackagename_id = Int(name='sourcepackagename', allow_none=True)
    sourcepackagename = Reference(sourcepackagename_id, 'SourcePackageName.id')

    recipe_id = Int(name='recipe', allow_none=False)
    recipe = Reference(recipe_id, 'SourcePackageRecipe.id')

    requester_id = Int(name='requester', allow_none=True)
    requester = Reference(requester_id, 'Person.id')

    manifest_id = Int(name='manifest', allow_none=True)
    manifest = Reference(manifest_id, '_SourcePackageRecipeData.id')

    @classmethod
    def new(cls):
        store = IMasterStore(SourcePackageBuild)
        spbuild = cls()
        store.add(spbuild)
        return spbuild
