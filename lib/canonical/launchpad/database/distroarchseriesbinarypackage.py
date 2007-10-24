
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent a binary package in a distroarchseries."""

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackage',
    ]

from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease
    )
from canonical.launchpad.database.distroarchseriesbinarypackagerelease import (
    DistroArchSeriesBinaryPackageRelease
    )
from canonical.launchpad.database.distroseriespackagecache import (
    DistroSeriesPackageCache
    )
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory
    )
from canonical.launchpad.interfaces import (
    IDistroArchSeriesBinaryPackage, NotFoundError, PackagePublishingStatus
    )


class DistroArchSeriesBinaryPackage:
    """A Binary Package in the context of a Distro Arch Series.

    Binary Packages are "magic": they don't really exist in the
    database. Instead, they are synthesized based on information from
    the publishing and binarypackagerelease tables.
    """

    implements(IDistroArchSeriesBinaryPackage)

    def __init__(self, distroarchseries, binarypackagename):
        self.distroarchseries = distroarchseries
        self.binarypackagename = binarypackagename

    @property
    def name(self):
        """See IDistroArchSeriesBinaryPackage."""
        return self.binarypackagename.name

    @property
    def distroseries(self):
        """See IDistroArchSeries."""
        return self.distroarchseries.distroseries

    @property
    def distribution(self):
        """See IDistroArchSeries."""
        return self.distroseries.distribution

    @property
    def displayname(self):
        """See IDistroArchSeriesBinaryPackage."""
        return '%s in %s %s' % (
            self.binarypackagename.name,
            self.distroarchseries.distroseries.name,
            self.distroarchseries.architecturetag)

    @property
    def title(self):
        """See IDistroArchSeriesBinaryPackage."""
        return 'Binary Package "%s" in %s' % (
            self.binarypackagename.name, self.distroarchseries.title)

    @property
    def summary(self):
        """See IDistroArchSeriesBinaryPackage."""
        curr = self.currentrelease
        if curr is not None:
            return curr.summary
        general = DistroSeriesPackageCache.selectOneBy(
            distroseries=self.distroseries,
            binarypackagename=self.binarypackagename)
        if general is not None:
            return general.summary
        return None

    @property
    def description(self):
        """See IDistroArchSeriesBinaryPackage."""
        curr = self.currentrelease
        if curr is not None:
            return curr.description
        general = DistroSeriesPackageCache.selectOneBy(
            distroseries=self.distroseries,
            binarypackagename=self.binarypackagename)
        if general is not None:
            return general.description
        return None


    def __getitem__(self, version):
        """See IDistroArchSeriesBinaryPackage."""
        query = """
        BinaryPackagePublishingHistory.distroarchrelease = %s AND
        BinaryPackagePublishingHistory.archive IN %s AND
        BinaryPackagePublishingHistory.binarypackagerelease =
            BinaryPackageRelease.id AND
        BinaryPackageRelease.version = %s AND
        BinaryPackageRelease.binarypackagename = %s
        """ % sqlvalues(
                self.distroarchseries,
                self.distribution.all_distro_archive_ids,
                version,
                self.binarypackagename)

        bpph = BinaryPackagePublishingHistory.selectFirst(
            query, clauseTables=['binarypackagerelease'],
            orderBy=["-datecreated"])

        if bpph is None:
            return None

        return DistroArchSeriesBinaryPackageRelease(
            distroarchseries=self.distroarchseries,
            binarypackagerelease=bpph.binarypackagerelease)

    @property
    def releases(self):
        """See IDistroArchSeriesBinaryPackage."""
        ret = BinaryPackageRelease.select("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s
            """ % sqlvalues(
                    self.distroarchseries,
                    self.distribution.all_distro_archive_ids,
                    self.binarypackagename),
            orderBy='-datecreated',
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory'])
        result = []
        versions = set()
        for bpr in ret:
            if bpr.version not in versions:
                versions.add(bpr.version)
                darbpr = DistroArchSeriesBinaryPackageRelease(
                    distroarchseries=self.distroarchseries,
                    binarypackagerelease=bpr)
                result.append(darbpr)
        return result

    @property
    def currentrelease(self):
        """See IDistroArchSeriesBinaryPackage."""
        releases = BinaryPackageRelease.select("""
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackageRelease.id =
                BinaryPackagePublishingHistory.binarypackagerelease AND
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.status = %s
            """ % sqlvalues(
                    self.binarypackagename,
                    self.distroarchseries,
                    self.distribution.all_distro_archive_ids,
                    PackagePublishingStatus.PUBLISHED),
            orderBy='datecreated',
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory',])

        # sort by version
        if releases.count() == 0:
            return None
        return DistroArchSeriesBinaryPackageRelease(
            distroarchseries=self.distroarchseries,
            binarypackagerelease=releases[-1])

    @property
    def publishing_history(self):
        """See IDistroArchSeriesBinaryPackage."""
        return BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s
            """ % sqlvalues(
                    self.distroarchseries,
                    self.distribution.all_distro_archive_ids,
                    self.binarypackagename),
            distinct=True,
            clauseTables=['BinaryPackageRelease'],
            orderBy='-datecreated')

    @property
    def current_published(self):
        """See IDistroArchSeriesBinaryPackage."""
        current = BinaryPackagePublishingHistory.selectFirst("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackagePublishingHistory.status = %s
            """ % sqlvalues(
                    self.distroarchseries,
                    self.distribution.all_distro_archive_ids,
                    self.binarypackagename,
                    PackagePublishingStatus.PUBLISHED),
            clauseTables=['BinaryPackageRelease'],
            orderBy='-datecreated')

        if current is None:
            raise NotFoundError("Binary package %s not published in %s/%s"
                                % (self.binarypackagename.name,
                                   self.distroarchseries.distroseries.name,
                                   self.distroarchseries.architecturetag))

        return current

