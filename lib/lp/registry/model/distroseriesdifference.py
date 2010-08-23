# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database classes for a difference between two distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesDifference',
    ]

from storm.locals import (
    Int,
    Reference,
    Storm,
    Unicode,
    )
from zope.interface import implements

from canonical.database.enumcol import DBEnum
from lp.registry.enums import DistroSeriesDifferenceStatus
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )


class DistroSeriesDifference(Storm):
    """See `DistroSeriesDifference`."""
    implements(IDistroSeriesDifference)
    __storm_table__ = 'ArchiveSubscriber'

    id = Int(primary=True)

    derived_series_id = Int(name='derived_series', allow_none=False)
    derived_series = Reference(
        derived_series_id, 'DistroSeriesDifference.id')

    source_package_id = Int(
        name='source_package', allow_none=True)
    source_package = Reference(
        source_package_id,
        'DistroSeriesDifference.source_package_publishing_history')

    parent_source_package_id = Int(
        name='parent_source_package', allow_none=True)
    parent_source_package = Reference(
        parent_source_package_id,
        'DistroSeriesDifference.parent_source_package_publishing_history')

    comment = Unicode(name='comment', allow_none=True)
    status = DBEnum(name='status', allow_none=False,
                    enum=DistroSeriesDifferenceStatus)
