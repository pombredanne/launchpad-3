# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'SourcePackageFormatSelection',
    ]

from storm.locals import Storm, Int, Reference
from zope.interface import implements

from canonical.database.enumcol import DBEnum
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelection, SourcePackageFormat)

class SourcePackageFormatSelection(Storm):
    """See ISourcePackageFormatSelection."""

    implements(ISourcePackageFormatSelection)

    def __init__(self, distroseries, format):
        super(SourcePackageFormatSelection, self).__init__()
        self.distroseries = distroseries
        self.format = format

    __storm_table__ = 'sourcepackageformatselection'

    id = Int(primary=True)

    distroseries_id = Int(name="distroseries")
    distroseries = Reference(distroseries_id, 'DistroSeries.id')

    format = DBEnum(enum=SourcePackageFormat)

