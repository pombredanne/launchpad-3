# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap series."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'SnapSeries',
    ]

import pytz
from storm.locals import (
    DateTime,
    Int,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from zope.interface import implementer

from lp.registry.interfaces.series import SeriesStatus
from lp.registry.model.distroseries import DistroSeries
from lp.services.database.constants import DEFAULT
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.snappy.interfaces.snapseries import (
    ISnapSeries,
    ISnapSeriesSet,
    NoSuchSnapSeries,
    )


@implementer(ISnapSeries)
class SnapSeries(Storm):
    """See `ISnapSeries`."""

    __storm_table__ = 'SnapSeries'

    id = Int(primary=True)

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    name = Unicode(name='name', allow_none=False)

    display_name = Unicode(name='display_name', allow_none=False)

    status = EnumCol(enum=SeriesStatus, notNull=True)

    def __init__(self, registrant, name, display_name, status,
                 date_created=DEFAULT):
        super(SnapSeries, self).__init__()
        self.registrant = registrant
        self.name = name
        self.display_name = display_name
        self.status = status
        self.date_created = date_created

    @property
    def title(self):
        return self.display_name

    @property
    def usable_distro_series(self):
        rows = IStore(DistroSeries).find(
            DistroSeries,
            SnapDistroSeries.snap_series == self,
            SnapDistroSeries.distro_series_id == DistroSeries.id)
        return rows.order_by(DistroSeries.id)

    @usable_distro_series.setter
    def usable_distro_series(self, value):
        enablements = dict(Store.of(self).find(
            (DistroSeries, SnapDistroSeries),
            SnapDistroSeries.snap_series == self,
            SnapDistroSeries.distro_series_id == DistroSeries.id))
        for distro_series in enablements:
            if distro_series not in value:
                Store.of(self).remove(enablements[distro_series])
        for distro_series in value:
            if distro_series not in enablements:
                link = SnapDistroSeries()
                link.snap_series = self
                link.distro_series = distro_series
                Store.of(self).add(link)


class SnapDistroSeries(Storm):
    """Link table between `SnapSeries` and `DistroSeries`."""

    __storm_table__ = 'SnapDistroSeries'
    __storm_primary__ = ('snap_series_id', 'distro_series_id')

    snap_series_id = Int(name='snap_series', allow_none=False)
    snap_series = Reference(snap_series_id, 'SnapSeries.id')

    distro_series_id = Int(name='distro_series', allow_none=False)
    distro_series = Reference(distro_series_id, 'DistroSeries.id')


@implementer(ISnapSeriesSet)
class SnapSeriesSet:
    """See `ISnapSeriesSet`."""

    def new(self, registrant, name, display_name, status,
            date_created=DEFAULT):
        """See `ISnapSeriesSet`."""
        store = IMasterStore(SnapSeries)
        snap_series = SnapSeries(
            registrant, name, display_name, status, date_created=date_created)
        store.add(snap_series)
        return snap_series

    def __iter__(self):
        """See `ISnapSeriesSet`."""
        return iter(self.getAll())

    def __getitem__(self, name):
        """See `ISnapSeriesSet`."""
        return self.getByName(name)

    def getByName(self, name):
        """See `ISnapSeriesSet`."""
        snap_series = IStore(SnapSeries).find(
            SnapSeries, SnapSeries.name == name).one()
        if snap_series is None:
            raise NoSuchSnapSeries(name)
        return snap_series

    def getByDistroSeries(self, distro_series):
        """See `ISnapSeriesSet`."""
        rows = IStore(SnapSeries).find(
            SnapSeries,
            SnapDistroSeries.snap_series_id == SnapSeries.id,
            SnapDistroSeries.distro_series == distro_series)
        return rows.order_by(SnapSeries.name)

    def getAll(self):
        """See `ISnapSeriesSet`."""
        return IStore(SnapSeries).find(SnapSeries).order_by(SnapSeries.name)
