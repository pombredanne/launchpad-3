# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database class for table DistroSeriesParent."""

__metaclass__ = type

__all__ = [
    'DistroSeriesParent',
    'DistroSeriesParentSet',
    ]

from storm.locals import (
    Bool,
    Int,
    Reference,
    Storm,
    )
from zope.interface import implements

from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.registry.interfaces.distroseriesparent import (
    IDistroSeriesParent,
    IDistroSeriesParentSet,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket


class DistroSeriesParent(Storm):
    """See `IDistroSeriesParent`."""
    implements(IDistroSeriesParent)
    __storm_table__ = 'DistroSeriesParent'

    id = Int(primary=True)

    parent_series_id = Int(name='parent_series', allow_none=False)
    parent_series = Reference(parent_series_id, 'DistroSeries.id')

    derived_series_id = Int(name='derived_series', allow_none=False)
    derived_series = Reference(derived_series_id, 'DistroSeries.id')

    initialized = Bool(allow_none=False)

    is_overlay = Bool(allow_none=False, default=False)

    pocket = EnumCol(
        dbName='pocket', notNull=False,
        schema=PackagePublishingPocket)

    component_id = Int(name='component', allow_none=True)
    component = Reference(component_id, 'Component.id')


class DistroSeriesParentSet:
    """See `IDistroSeriesParentSet`."""
    implements(IDistroSeriesParentSet)
    title = "Cross reference of parent and derived distroseries."

    def new(self, derived_series, parent_series, initialized,
            is_overlay=False, pocket=None, component=None):
        """Make and return a new `DistroSeriesParent`."""
        store = IMasterStore(DistroSeriesParent)
        dsp = DistroSeriesParent()
        dsp.derived_series = derived_series
        dsp.parent_series = parent_series
        dsp.initialized = initialized
        dsp.is_overlay = is_overlay
        dsp.pocket = pocket
        dsp.component = component
        store.add(dsp)
        return dsp

    def getByDerivedSeries(self, derived_series):
        """See `IDistroSeriesParentSet`."""
        store = IStore(DistroSeriesParent)
        return store.find(
            DistroSeriesParent,
            DistroSeriesParent.derived_series_id == derived_series.id)

    def getByParentSeries(self, parent_series):
        """See `IDistroSeriesParentSet`."""
        store = IStore(DistroSeriesParent)
        return store.find(
            DistroSeriesParent,
            DistroSeriesParent.parent_series_id == parent_series.id)
