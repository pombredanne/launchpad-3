# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Classes to represent a binary package in a distroarchseries."""

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackage',
    ]

from storm.locals import Desc
from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.app.errors import NotFoundError
from lp.services.propertycache import cachedproperty
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.distroarchseriesbinarypackage import (
    IDistroArchSeriesBinaryPackage,
    )
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.distroarchseriesbinarypackagerelease import (
    DistroArchSeriesBinaryPackageRelease,
    )
from lp.soyuz.model.publishing import BinaryPackagePublishingHistory


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
        return '"%s" binary package in %s' % (
            self.binarypackagename.name, self.distroarchseries.displayname)

    @cachedproperty
    def cache(self):
        """See IDistroArchSeriesBinaryPackage."""
        from lp.soyuz.model.distroseriespackagecache import (
            DistroSeriesPackageCache)
        query = """
            distroseries = %s AND
            archive IN %s AND
            binarypackagename = %s
        """ % sqlvalues(self.distroseries,
                        self.distribution.all_distro_archive_ids,
                        self.binarypackagename)

        return DistroSeriesPackageCache.selectOne(query)

    @property
    def summary(self):
        """See IDistroArchSeriesBinaryPackage."""
        curr = self.currentrelease
        if curr is not None:
            return curr.summary
        if self.cache is not None:
            return self.cache.summary
        return None

    @property
    def description(self):
        """See IDistroArchSeriesBinaryPackage."""
        curr = self.currentrelease
        if curr is not None:
            return curr.description
        if self.cache is not None:
            return self.cache.description
        return None

    def __getitem__(self, version):
        """See IDistroArchSeriesBinaryPackage."""
        query = """
        BinaryPackagePublishingHistory.distroarchseries = %s AND
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
            BinaryPackagePublishingHistory.distroarchseries = %s AND
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
            BinaryPackagePublishingHistory.distroarchseries = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.status = %s
            """ % sqlvalues(
                    self.binarypackagename,
                    self.distroarchseries,
                    self.distribution.all_distro_archive_ids,
                    PackagePublishingStatus.PUBLISHED),
            orderBy='-datecreated',
            limit=1,
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory'])

        # Listify to limit the SQL queries to one only.
        results = list(releases)
        if len(results) == 0:
            return None
        return DistroArchSeriesBinaryPackageRelease(
            distroarchseries=self.distroarchseries,
            binarypackagerelease=results[0])

    @property
    def publishing_history(self):
        """See IDistroArchSeriesBinaryPackage."""
        return IStore(BinaryPackagePublishingHistory).find(
            BinaryPackagePublishingHistory,
            BinaryPackageRelease.binarypackagename == self.binarypackagename,
            BinaryPackagePublishingHistory.distroarchseries ==
                self.distroarchseries,
            BinaryPackagePublishingHistory.archiveID.is_in(
                self.distribution.all_distro_archive_ids),
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id).config(distinct=True).order_by(
                Desc(BinaryPackagePublishingHistory.datecreated))

    @property
    def current_published(self):
        """See IDistroArchSeriesBinaryPackage."""
        current = BinaryPackagePublishingHistory.selectFirst("""
            BinaryPackagePublishingHistory.distroarchseries = %s AND
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

    @property
    def distro_source_package(self):
        """See `IDistroArchSeriesBinaryPackage`."""
        # We provide a source package iff we have a current release
        # with a source package release.
        current_release = self.currentrelease
        if current_release is None:
            return None

        src_pkg_release = current_release.distributionsourcepackagerelease
        if src_pkg_release is None:
            return None
        else:
            return src_pkg_release.sourcepackage
