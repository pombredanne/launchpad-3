# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'SourcePackageFormatSelection',
    'SourcePackageFormatSelectionSet',
    ]

from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from zope.interface import implementer

from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.soyuz.enums import SourcePackageFormat
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelection,
    ISourcePackageFormatSelectionSet,
    )


@implementer(ISourcePackageFormatSelection)
class SourcePackageFormatSelection(Storm):
    """See ISourcePackageFormatSelection."""

    __storm_table__ = 'sourcepackageformatselection'

    id = Int(primary=True)

    distroseries_id = Int(name="distroseries")
    distroseries = Reference(distroseries_id, 'DistroSeries.id')

    format = DBEnum(enum=SourcePackageFormat)


@implementer(ISourcePackageFormatSelectionSet)
class SourcePackageFormatSelectionSet:
    """See ISourcePackageFormatSelectionSet."""

    def getBySeriesAndFormat(self, distroseries, format):
        """See `ISourcePackageFormatSelection`."""
        return IStore(SourcePackageFormatSelection).find(
            SourcePackageFormatSelection, distroseries=distroseries,
            format=format).one()

    def add(self, distroseries, format):
        """See `ISourcePackageFormatSelection`."""
        spfs = SourcePackageFormatSelection()
        spfs.distroseries = distroseries
        spfs.format = format
        return IMasterStore(SourcePackageFormatSelection).add(spfs)
