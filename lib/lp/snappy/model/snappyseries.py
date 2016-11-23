# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snappy series."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'SnappyDistroSeries',
    'SnappySeries',
    ]

import pytz
from storm.locals import (
    Bool,
    DateTime,
    Desc,
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
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.snappy.interfaces.snappyseries import (
    ISnappyDistroSeries,
    ISnappyDistroSeriesSet,
    ISnappySeries,
    ISnappySeriesSet,
    NoSuchSnappySeries,
    )


@implementer(ISnappySeries)
class SnappySeries(Storm):
    """See `ISnappySeries`."""

    __storm_table__ = 'SnappySeries'

    id = Int(primary=True)

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    name = Unicode(name='name', allow_none=False)

    display_name = Unicode(name='display_name', allow_none=False)

    status = EnumCol(enum=SeriesStatus, notNull=True)

    def __init__(self, registrant, name, display_name, status,
                 preferred_distro_series=None, date_created=DEFAULT):
        super(SnappySeries, self).__init__()
        self.registrant = registrant
        self.name = name
        self.display_name = display_name
        self.status = status
        self.date_created = date_created
        self.preferred_distro_series = preferred_distro_series

    @property
    def title(self):
        return self.display_name

    @cachedproperty
    def _preferred_distro_series(self):
        return Store.of(self).find(
            DistroSeries,
            SnappyDistroSeries.snappy_series == self,
            SnappyDistroSeries.distro_series_id == DistroSeries.id,
            SnappyDistroSeries.preferred == True).one()

    @property
    def preferred_distro_series(self):
        return self._preferred_distro_series

    @preferred_distro_series.setter
    def preferred_distro_series(self, value):
        current = Store.of(self).find(
            SnappyDistroSeries,
            SnappyDistroSeries.snappy_series == self,
            SnappyDistroSeries.preferred == True).one()
        if current is not None:
            if current.distro_series == value:
                return
            current.preferred = False
            get_property_cache(self)._preferred_distro_series = None
        if value is not None:
            row = Store.of(self).find(
                SnappyDistroSeries,
                SnappyDistroSeries.snappy_series == self,
                SnappyDistroSeries.distro_series == value).one()
            if row is not None:
                row.preferred = True
            else:
                row = SnappyDistroSeries(self, value, preferred=True)
                Store.of(self).add(row)
            get_property_cache(self)._preferred_distro_series = value

    @property
    def usable_distro_series(self):
        rows = IStore(DistroSeries).find(
            DistroSeries,
            SnappyDistroSeries.snappy_series == self,
            SnappyDistroSeries.distro_series_id == DistroSeries.id)
        return rows.order_by(Desc(DistroSeries.id))

    @usable_distro_series.setter
    def usable_distro_series(self, value):
        enablements = dict(Store.of(self).find(
            (DistroSeries, SnappyDistroSeries),
            SnappyDistroSeries.snappy_series == self,
            SnappyDistroSeries.distro_series_id == DistroSeries.id))
        for distro_series in enablements:
            if distro_series not in value:
                if enablements[distro_series].preferred:
                    get_property_cache(self)._preferred_distro_series = None
                Store.of(self).remove(enablements[distro_series])
        for distro_series in value:
            if distro_series not in enablements:
                link = SnappyDistroSeries(self, distro_series)
                Store.of(self).add(link)


@implementer(ISnappyDistroSeries)
class SnappyDistroSeries(Storm):
    """Link table between `SnappySeries` and `DistroSeries`."""

    __storm_table__ = 'SnappyDistroSeries'
    __storm_primary__ = ('snappy_series_id', 'distro_series_id')

    snappy_series_id = Int(name='snappy_series', allow_none=False)
    snappy_series = Reference(snappy_series_id, 'SnappySeries.id')

    distro_series_id = Int(name='distro_series', allow_none=False)
    distro_series = Reference(distro_series_id, 'DistroSeries.id')

    preferred = Bool(name='preferred', allow_none=False)

    def __init__(self, snappy_series, distro_series, preferred=False):
        super(SnappyDistroSeries, self).__init__()
        self.snappy_series = snappy_series
        self.distro_series = distro_series
        self.preferred = preferred

    @property
    def title(self):
        return "%s, for %s" % (
            self.distro_series.fullseriesname, self.snappy_series.title)


@implementer(ISnappySeriesSet)
class SnappySeriesSet:
    """See `ISnappySeriesSet`."""

    def new(self, registrant, name, display_name, status,
            preferred_distro_series=None, date_created=DEFAULT):
        """See `ISnappySeriesSet`."""
        store = IMasterStore(SnappySeries)
        snappy_series = SnappySeries(
            registrant, name, display_name, status,
            preferred_distro_series=preferred_distro_series,
            date_created=date_created)
        store.add(snappy_series)
        return snappy_series

    def __iter__(self):
        """See `ISnappySeriesSet`."""
        return iter(self.getAll())

    def __getitem__(self, name):
        """See `ISnappySeriesSet`."""
        return self.getByName(name)

    def getByName(self, name):
        """See `ISnappySeriesSet`."""
        snappy_series = IStore(SnappySeries).find(
            SnappySeries, SnappySeries.name == name).one()
        if snappy_series is None:
            raise NoSuchSnappySeries(name)
        return snappy_series

    def getByDistroSeries(self, distro_series):
        """See `ISnappySeriesSet`."""
        rows = IStore(SnappySeries).find(
            SnappySeries,
            SnappyDistroSeries.snappy_series_id == SnappySeries.id,
            SnappyDistroSeries.distro_series == distro_series)
        return rows.order_by(Desc(SnappySeries.name))

    def getAll(self):
        """See `ISnappySeriesSet`."""
        return IStore(SnappySeries).find(SnappySeries).order_by(
            Desc(SnappySeries.name))


@implementer(ISnappyDistroSeriesSet)
class SnappyDistroSeriesSet:
    """See `ISnappyDistroSeriesSet`."""

    def getByDistroSeries(self, distro_series):
        """See `ISnappyDistroSeriesSet`."""
        store = IStore(SnappyDistroSeries)
        rows = store.using(SnappyDistroSeries, SnappySeries).find(
            SnappyDistroSeries,
            SnappyDistroSeries.snappy_series_id == SnappySeries.id,
            SnappyDistroSeries.distro_series == distro_series)
        return rows.order_by(Desc(SnappySeries.name))

    def getByBothSeries(self, snappy_series, distro_series):
        """See `ISnappyDistroSeriesSet`."""
        return IStore(SnappyDistroSeries).find(
            SnappyDistroSeries,
            SnappyDistroSeries.snappy_series == snappy_series,
            SnappyDistroSeries.distro_series == distro_series).one()

    def getAll(self):
        """See `ISnappyDistroSeriesSet`."""
        return IStore(SnappyDistroSeries).find(SnappyDistroSeries)
