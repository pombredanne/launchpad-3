# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Snappy vocabularies."""

__metaclass__ = type

__all__ = [
    'SnapDistroArchSeriesVocabulary',
    'SnappySeriesVocabulary',
    ]

from storm.locals import Desc
from zope.schema.vocabulary import SimpleTerm

from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.series import ACTIVE_STATUSES
from lp.services.database.interfaces import IStore
from lp.services.webapp.vocabulary import StormVocabularyBase
from lp.snappy.model.snappyseries import (
    SnappyDistroSeries,
    SnappySeries,
    )
from lp.soyuz.model.distroarchseries import DistroArchSeries


class SnapDistroArchSeriesVocabulary(StormVocabularyBase):
    """All architectures of a Snap's distribution series."""

    _table = DistroArchSeries

    def toTerm(self, das):
        return SimpleTerm(das, das.id, das.architecturetag)

    def __iter__(self):
        for obj in self.context.getAllowedArchitectures():
            yield self.toTerm(obj)

    def __len__(self):
        return len(self.context.getAllowedArchitectures())


class SnappySeriesVocabulary(StormVocabularyBase):
    """A vocabulary for searching snappy series."""

    _table = SnappySeries
    _clauses = [SnappySeries.status.is_in(ACTIVE_STATUSES)]
    _order_by = Desc(SnappySeries.date_created)


class SnappyDistroSeriesVocabulary(StormVocabularyBase):
    """A vocabulary for searching snappy/distro series combinations."""

    _table = SnappyDistroSeries
    _clauses = [
        SnappyDistroSeries.snappy_series_id == SnappySeries.id,
        SnappyDistroSeries.distro_series_id == DistroSeries.id,
        DistroSeries.distributionID == Distribution.id,
        ]

    @property
    def _entries(self):
        tables = [SnappyDistroSeries, SnappySeries, DistroSeries, Distribution]
        entries = IStore(self._table).using(*tables).find(
            self._table, *self._clauses)
        return entries.order_by(
            Distribution.display_name, Desc(DistroSeries.date_created),
            Desc(SnappySeries.date_created))

    def toTerm(self, obj):
        """See `IVocabulary`."""
        token = "%s/%s/%s" % (
            obj.distro_series.distribution.name, obj.distro_series.name,
            obj.snappy_series.name)
        return SimpleTerm(obj, token, obj.title)

    def __contains__(self, value):
        """See `IVocabulary`."""
        return value in self._entries

    def getTerm(self, value):
        """See `IVocabulary`."""
        if value not in self:
            raise LookupError(value)
        return self.toTerm(value)


class BuildableSnappyDistroSeriesVocabulary(SnappyDistroSeriesVocabulary):
    """A vocabulary for searching active snappy/distro series combinations."""

    _clauses = SnappyDistroSeriesVocabulary._clauses + [
        SnappySeries.status.is_in(ACTIVE_STATUSES),
        ]
