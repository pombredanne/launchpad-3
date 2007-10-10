# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'DistroSeriesBinaryPackage',
    ]

from zope.interface import implements

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.interfaces import IDistroSeriesBinaryPackage

from canonical.launchpad.database.distroseriespackagecache import (
    DistroSeriesPackageCache)
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory)
from canonical.lp.dbschema import PackagePublishingStatus

class DistroSeriesBinaryPackage:
    """A binary package, like "apache2.1", in a distro series like "hoary".

    Note that this does not refer necessarily to a specific release of that
    binary package, nor to a specific architecture. What is really being
    described is the "name", and from there we can jump to specific versions
    in specific DistroArchSeriess.
    """

    implements(IDistroSeriesBinaryPackage)

    def __init__(self, distroseries, binarypackagename):
        self.distroseries = distroseries
        self.binarypackagename = binarypackagename

    @property
    def name(self):
        """See IDistroSeriesBinaryPackage."""
        return self.binarypackagename.name

    @property
    def title(self):
        """See IDistroSeriesBinaryPackage."""
        return 'Binary package "%s" in %s %s' % (
            self.name, self.distribution.name, self.distroseries.name)

    @property
    def distribution(self):
        """See IDistroSeriesBinaryPackage."""
        return self.distroseries.distribution

    @property
    def cache(self):
        """See IDistroSeriesBinaryPackage."""
        return DistroSeriesPackageCache.selectOne("""
            distrorelease = %s AND
            binarypackagename = %s
            """ % sqlvalues(self.distroseries.id, self.binarypackagename.id))

    @property
    def summary(self):
        """See IDistroSeriesBinaryPackage."""
        cache = self.cache
        if cache is None:
            return None
        return cache.summary

    @property
    def description(self):
        """See IDistroSeriesBinaryPackage."""
        cache = self.cache
        if cache is None:
            return None
        return cache.description

    @property
    def current_publishings(self):
        """See IDistroSeriesBinaryPackage."""
        ret = BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackagePublishingHistory.status != %s
            """ % sqlvalues(
                    self.distroseries,
                    self.distroseries.distribution.all_distro_archive_ids,
                    self.binarypackagename,
                    PackagePublishingStatus.REMOVED),
            orderBy=['-datecreated'],
            clauseTables=['DistroArchRelease', 'BinaryPackageRelease'])
        return sorted(ret, key=lambda a: (
            a.distroarchseries.architecturetag,
            a.datecreated))

