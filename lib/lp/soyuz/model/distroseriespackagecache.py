# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'DistroSeriesPackageCache',
    ]

from collections import defaultdict
from operator import attrgetter

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from storm.expr import (
    Desc,
    Max,
    Select,
    )
from storm.locals import RawStr
from zope.interface import implementer

from lp.services.database import bulk
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import SQLBase
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.distroseriespackagecache import (
    IDistroSeriesPackageCache,
    )
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.publishing import BinaryPackagePublishingHistory


@implementer(IDistroSeriesPackageCache)
class DistroSeriesPackageCache(SQLBase):
    _table = 'DistroSeriesPackageCache'

    archive = ForeignKey(dbName='archive',
        foreignKey='Archive', notNull=True)
    distroseries = ForeignKey(dbName='distroseries',
        foreignKey='DistroSeries', notNull=True)
    binarypackagename = ForeignKey(dbName='binarypackagename',
        foreignKey='BinaryPackageName', notNull=True)

    fti = RawStr(allow_none=True, default=None)
    name = StringCol(notNull=False, default=None)
    summary = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False, default=None)
    summaries = StringCol(notNull=False, default=None)
    descriptions = StringCol(notNull=False, default=None)

    @classmethod
    def findCurrentBinaryPackageNames(cls, archive, distroseries):
        bpn_ids = IStore(BinaryPackagePublishingHistory).find(
            BinaryPackagePublishingHistory.binarypackagenameID,
            BinaryPackagePublishingHistory.distroarchseriesID.is_in(
                Select(
                    DistroArchSeries.id, tables=[DistroArchSeries],
                    where=DistroArchSeries.distroseries == distroseries)),
            BinaryPackagePublishingHistory.archive == archive,
            BinaryPackagePublishingHistory.status.is_in((
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED))).config(
                    distinct=True)
        return bulk.load(BinaryPackageName, bpn_ids)

    @classmethod
    def _find(cls, distroseries, archive=None):
        """All of the cached binary package records for this distroseries.

        If 'archive' is not given it will return all caches stored for the
        distroseries main archives (PRIMARY and PARTNER).
        """
        if archive is not None:
            archives = [archive.id]
        else:
            archives = distroseries.distribution.all_distro_archive_ids

        return IStore(cls).find(
            cls,
            cls.distroseries == distroseries,
            cls.archiveID.is_in(archives)).order_by(cls.name)

    @classmethod
    def removeOld(cls, distroseries, archive, log):
        """Delete any records that are no longer applicable.

        Consider all binarypackages marked as REMOVED.

        Also purges all existing cache records for disabled archives.

        :param archive: target `IArchive`.
        :param log: the context logger object able to print DEBUG level
            messages.
        """
        # get the set of package names that should be there
        if not archive.enabled:
            bpns = set()
        else:
            bpns = set(
                cls.findCurrentBinaryPackageNames(archive, distroseries))

        # remove the cache entries for binary packages we no longer want
        for cache in cls._find(distroseries, archive):
            if cache.binarypackagename not in bpns:
                log.debug(
                    "Removing binary cache for '%s' (%s)"
                    % (cache.name, cache.id))
                cache.destroySelf()

    @classmethod
    def _update(cls, distroseries, binarypackagenames, archive, log):
        """Update the package cache for a given set of `IBinaryPackageName`s.

        'log' is required, it should be a logger object able to print
        DEBUG level messages.
        'ztm' is the current trasaction manager used for partial commits
        (in full batches of 100 elements)
        """
        # get the set of published binarypackagereleases
        all_details = list(IStore(BinaryPackageRelease).find(
            (BinaryPackageRelease.binarypackagenameID,
             BinaryPackageRelease.summary, BinaryPackageRelease.description,
             Max(BinaryPackageRelease.datecreated)),
            BinaryPackageRelease.id ==
                BinaryPackagePublishingHistory.binarypackagereleaseID,
            BinaryPackagePublishingHistory.binarypackagenameID.is_in(
                [bpn.id for bpn in binarypackagenames]),
            BinaryPackagePublishingHistory.distroarchseriesID.is_in(
                Select(
                    DistroArchSeries.id, tables=[DistroArchSeries],
                    where=DistroArchSeries.distroseries == distroseries)),
            BinaryPackagePublishingHistory.archive == archive,
            BinaryPackagePublishingHistory.status.is_in((
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED))
            ).group_by(
                BinaryPackageRelease.binarypackagenameID,
                BinaryPackageRelease.summary,
                BinaryPackageRelease.description
            ).order_by(
                BinaryPackageRelease.binarypackagenameID,
                Desc(Max(BinaryPackageRelease.datecreated))))
        if not all_details:
            log.debug("No binary releases found.")
            return

        details_map = defaultdict(list)
        for (bpn_id, summary, description, datecreated) in all_details:
            bpn = IStore(BinaryPackageName).get(BinaryPackageName, bpn_id)
            details_map[bpn].append((summary, description))

        all_caches = IStore(cls).find(
            cls, cls.distroseries == distroseries, cls.archive == archive,
            cls.binarypackagenameID.is_in(
                [bpn.id for bpn in binarypackagenames]))
        cache_map = {cache.binarypackagename: cache for cache in all_caches}

        for bpn in set(binarypackagenames) - set(cache_map):
            cache_map[bpn] = cls(
                archive=archive, distroseries=distroseries,
                binarypackagename=bpn)

        for bpn in binarypackagenames:
            cache = cache_map[bpn]
            details = details_map[bpn]
            # make sure the cached name, summary and description are correct
            cache.name = bpn.name
            cache.summary = details[0][0]
            cache.description = details[0][1]

            # get the sets of binary package summaries, descriptions. there is
            # likely only one, but just in case...

            summaries = set()
            descriptions = set()
            for summary, description in details:
                summaries.add(summary)
                descriptions.add(description)

            # and update the caches
            cache.summaries = ' '.join(sorted(summaries))
            cache.descriptions = ' '.join(sorted(descriptions))

    @classmethod
    def updateAll(cls, distroseries, archive, log, ztm, commit_chunk=500):
        """Update the binary package cache

        Consider all binary package names published in this distro series
        and entirely skips updates for disabled archives

        :param archive: target `IArchive`;
        :param log: logger object for printing debug level information;
        :param ztm:  transaction used for partial commits, every chunk of
            'commit_chunk' updates is committed;
        :param commit_chunk: number of updates before commit, defaults to 500.

        :return the number of packages updated.
        """
        # Do not create cache entries for disabled archives.
        if not archive.enabled:
            return

        # Get the set of package names to deal with.
        bpns = list(sorted(
            cls.findCurrentBinaryPackageNames(archive, distroseries),
            key=attrgetter('name')))

        number_of_updates = 0
        chunks = []
        chunk = []
        for bpn in bpns:
            chunk.append(bpn)
            if len(chunk) == commit_chunk:
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunks.append(chunk)
        for chunk in chunks:
            bulk.load(BinaryPackageName, [bpn.id for bpn in chunk])
            log.debug(
                "Considering binaries %s",
                ', '.join([bpn.name for bpn in chunk]))
            cls._update(distroseries, chunk, archive, log)
            number_of_updates += len(chunk)
            log.debug("Committing")
            ztm.commit()

        return number_of_updates
