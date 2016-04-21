# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Snappy vocabularies."""

__metaclass__ = type

__all__ = [
    'SnapDistroArchSeriesVocabulary',
    'SnapSeriesVocabulary',
    ]

from zope.schema.vocabulary import SimpleTerm

from lp.registry.model.series import ACTIVE_STATUSES
from lp.services.webapp.vocabulary import StormVocabularyBase
from lp.snappy.model.snapseries import SnapSeries
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


class SnapSeriesVocabulary(StormVocabularyBase):
    """A vocabulary for searching snap series."""

    _table = SnapSeries
    _clauses = [SnapSeries.status.is_in(ACTIVE_STATUSES)]
