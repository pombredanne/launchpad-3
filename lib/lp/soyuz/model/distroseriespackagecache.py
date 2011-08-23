# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'DistroSeriesPackageCache',
    ]

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from storm.locals import RawStr
from zope.interface import implements

from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.soyuz.interfaces.distroseriespackagecache import (
    IDistroSeriesPackageCache,
    )
from lp.soyuz.model.binarypackagename import BinaryPackageName


class DistroSeriesPackageCache(SQLBase):
    implements(IDistroSeriesPackageCache)
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
    def find(cls, distroseries, archive=None):
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
        bpns = set(BinaryPackageName.select("""
            BinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchSeries.distroseries = %s AND
            Archive.id = %s AND
            BinaryPackagePublishingHistory.archive = Archive.id AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishingHistory.dateremoved is NULL AND
            Archive.enabled = TRUE
            """ % sqlvalues(distroseries.id, archive.id),
            distinct=True,
            clauseTables=[
                'Archive',
                'DistroArchSeries',
                'BinaryPackagePublishingHistory',
                'BinaryPackageRelease']))

        # remove the cache entries for binary packages we no longer want
        for cache in cls.find(distroseries, archive):
            if cache.binarypackagename not in bpns:
                log.debug(
                    "Removing binary cache for '%s' (%s)"
                    % (cache.name, cache.id))
                cache.destroySelf()

