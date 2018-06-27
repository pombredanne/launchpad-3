# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Source Package Recipe vocabularies used in the lp/code modules."""

__metaclass__ = type
__all__ = [
    'BuildableDistroSeries',
    'target_ppas_vocabulary',
    ]

from zope.component import getUtility
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.model.distroseries import DistroSeries
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webapp.sorting import sorted_dotted_numbers
from lp.services.webapp.vocabulary import (
    IHugeVocabulary,
    SQLObjectVocabularyBase,
    )
from lp.soyuz.browser.archive import make_archive_vocabulary
from lp.soyuz.interfaces.archive import IArchiveSet


@implementer(IHugeVocabulary)
class BuildableDistroSeries(SQLObjectVocabularyBase):

    _table = DistroSeries

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.id, obj.displayname)

    @classmethod
    def findSeries(self, user):
        supported_distros = set(
            getUtility(IArchiveSet).getPPADistributionsForUser(user))
        # Now add in Ubuntu.
        supported_distros.add(getUtility(ILaunchpadCelebrities).ubuntu)
        all_series = getUtility(IDistroSeriesSet).search()

        return [
            series for series in all_series
            if series.active and series.distribution in supported_distros]

    def __iter__(self):
        distroseries = self.findSeries(getUtility(ILaunchBag).user)
        series = sorted_dotted_numbers(
            [self.toTerm(s) for s in distroseries],
            key=lambda term: term.value.version)
        series.reverse()
        return iter(series)


def target_ppas_vocabulary(context):
    """Return a vocabulary of ppas that the current user can target."""
    return make_archive_vocabulary(
        getUtility(IArchiveSet).getPPAsForUser(getUtility(ILaunchBag).user))
