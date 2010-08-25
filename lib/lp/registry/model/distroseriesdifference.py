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
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.exceptions import NotADerivedSeriesError
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    IDistroSeriesDifferenceSource,
    )


class DistroSeriesDifference(Storm):
    """See `DistroSeriesDifference`."""
    implements(IDistroSeriesDifference)
    classProvides(IDistroSeriesDifferenceSource)
    __storm_table__ = 'DistroSeriesDifference'

    id = Int(primary=True)

    derived_series_id = Int(name='derived_series', allow_none=False)
    derived_series = Reference(
        derived_series_id, 'DistroSeries.id')

    source_package_name_id = Int(
        name='source_package_name', allow_none=False)
    source_package_name = Reference(
        source_package_name_id, 'SourcePackageName.id')

    last_package_diff_id = Int(
        name='last_package_diff', allow_none=True)
    last_package_diff = Reference(
        last_package_diff_id, 'PackageDiff.id')

    activity_log = Unicode(name='activity_log', allow_none=True)
    status = DBEnum(name='status', allow_none=False,
                    enum=DistroSeriesDifferenceStatus)
    difference_type = DBEnum(name='difference_type', allow_none=False,
                             enum=DistroSeriesDifferenceType)

    @staticmethod
    def new(derived_series, source_package_name, difference_type,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION):
        """See `IDistroSeriesDifferenceSource`."""
        if derived_series.parent_series is None:
            raise NotADerivedSeriesError()

        store = IMasterStore(DistroSeriesDifference)
        diff = DistroSeriesDifference()
        diff.derived_series = derived_series
        diff.source_package_name = source_package_name
        diff.status = status
        diff.difference_type = difference_type
        return store.add(diff)

    @property
    def source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestPubForDistroSeries(
            self.derived_series, self.source_package_name)

    @property
    def parent_source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestPubForDistroSeries(
            self.derived_series.parent_series, self.source_package_name)

    def _getLatestPubForDistroSeries(self, distro_series, source_package_name):
        # XXX 2010-08-25 This will move to
        # DistroSeries.getCurrentSourcePub() and tested in a following branch.
        from storm.store import Store
        store = Store.of(self)

        from lp.soyuz.model.publishing import SourcePackagePublishingHistory
        SPPH = SourcePackagePublishingHistory
        from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
        result = store.find(
            SPPH,
            SPPH.sourcepackagerelease == SourcePackageRelease.id,
            SourcePackageRelease.sourcepackagename == source_package_name,
            SPPH.distroseries == distro_series).order_by(SPPH.id)

        return result.first()
