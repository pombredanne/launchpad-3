# Copyright 2015 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Snappy vocabularies."""

__metaclass__ = type

__all__ = [
    'SnapDistroArchSeriesVocabulary',
    ]

from zope.schema.vocabulary import SimpleTerm

from lp.services.webapp.vocabulary import StormVocabularyBase
from lp.soyuz.model.distroarchseries import DistroArchSeries


class SnapDistroArchSeriesVocabulary(StormVocabularyBase):
    """All architectures of a Snap's distribution series."""

    _table = DistroArchSeries

    def toTerm(self, das):
        return SimpleTerm(das, das.id, das.architecturetag)

    @property
    def _entries(self):
        return self.context.distro_series.buildable_architectures
