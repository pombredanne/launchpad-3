# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Soyuz vocabularies."""

__metaclass__ = type

__all__ = [
    'ComponentVocabulary',
    'FilteredDistroArchSeriesVocabulary',
    'PackageReleaseVocabulary',
    'PPAVocabulary',
    ]

from storm.locals import (
    And,
    Or,
    )
from zope.component import getUtility
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm
from zope.security.interfaces import Unauthorized

from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import Person
from lp.services.database.interfaces import IStore
from lp.services.database.stormexpr import fti_search
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webapp.vocabulary import (
    IHugeVocabulary,
    SQLObjectVocabularyBase,
    )
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.model.archive import (
    Archive,
    get_enabled_archive_filter,
    )
from lp.soyuz.model.component import Component
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


class ComponentVocabulary(SQLObjectVocabularyBase):

    _table = Component
    _orderBy = 'name'

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.name)


class FilteredDistroArchSeriesVocabulary(SQLObjectVocabularyBase):
    """All arch series of a particular distribution."""

    _table = DistroArchSeries
    _orderBy = ['DistroSeries.version', 'architecturetag', 'id']

    def toTerm(self, obj):
        name = "%s %s (%s)" % (obj.distroseries.distribution.name,
                               obj.distroseries.name, obj.architecturetag)
        return SimpleTerm(obj, obj.id, name)

    def __iter__(self):
        distribution = getUtility(ILaunchBag).distribution
        if distribution:
            results = IStore(DistroSeries).find(
                self._table,
                DistroSeries.id == DistroArchSeries.distroseriesID,
                DistroSeries.distributionID == distribution.id).order_by(
                    *self._orderBy)
            for distroarchseries in results:
                yield self.toTerm(distroarchseries)


class PackageReleaseVocabulary(SQLObjectVocabularyBase):
    _table = SourcePackageRelease
    _orderBy = 'id'

    def toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.name + " " + obj.version)


@implementer(IHugeVocabulary)
class PPAVocabulary(SQLObjectVocabularyBase):

    _table = Archive
    _orderBy = ['Person.name, Archive.name']
    _clauseTables = ['Person']
    # This should probably also filter by privacy, but that becomes
    # problematic when you need to remove a dependency that you can no
    # longer see.
    _filter = And(
        Archive._enabled == True,
        Person.q.id == Archive.q.ownerID,
        Archive.q.purpose == ArchivePurpose.PPA)
    displayname = 'Select a PPA'
    step_title = 'Search'

    def toTerm(self, archive):
        """See `IVocabulary`."""
        summary = "No description available"
        try:
            if archive.description:
                summary = archive.description.splitlines()[0]
        except Unauthorized:
            pass
        return SimpleTerm(archive, archive.reference, summary)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        obj = getUtility(IArchiveSet).getByReference(token)
        if obj is None or not obj.enabled or not obj.is_ppa:
            raise LookupError(token)
        return self.toTerm(obj)

    def search(self, query, vocab_filter=None):
        """Return a resultset of archives.

        This is a helper required by `SQLObjectVocabularyBase.searchForTerms`.
        """
        if not query:
            return self.emptySelectResults()

        query = query.lower()

        if query.startswith('~'):
            query = query.strip('~')
        if query.startswith('ppa:'):
            query = query[4:]
        try:
            query_split = query.split('/')
            if len(query_split) == 3:
                owner_name, distro_name, archive_name = query_split
            else:
                owner_name, archive_name = query_split
        except ValueError:
            search_clause = Or(
                fti_search(Archive, query), fti_search(Person, query))
        else:
            search_clause = And(
                Person.name == owner_name, Archive.name == archive_name)

        clause = And(
            self._filter,
            get_enabled_archive_filter(
                getUtility(ILaunchBag).user, purpose=ArchivePurpose.PPA,
                include_public=True),
            search_clause)
        return self._table.select(
            clause, orderBy=self._orderBy, clauseTables=self._clauseTables)
