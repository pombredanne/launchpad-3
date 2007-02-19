# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'DistroReleaseBinaryPackage',
    ]

from zope.interface import implements

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.interfaces import IDistroReleaseBinaryPackage

from canonical.launchpad.database.distroreleasepackagecache import (
    DistroReleasePackageCache)
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory)
from canonical.lp.dbschema import PackagePublishingStatus

class DistroReleaseBinaryPackage:
    """A binary package, like "apache2.1", in a distro release like "hoary".

    Note that this does not refer necessarily to a specific release of that
    binary package, nor to a specific architecture. What is really being
    described is the "name", and from there we can jump to specific versions
    in specific DistroArchReleases.
    """

    implements(IDistroReleaseBinaryPackage)

    def __init__(self, distrorelease, binarypackagename):
        self.distrorelease = distrorelease
        self.binarypackagename = binarypackagename

    @property
    def name(self):
        """See IDistroReleaseBinaryPackage."""
        return self.binarypackagename.name

    @property
    def title(self):
        """See IDistroReleaseBinaryPackage."""
        return 'Binary package "%s" in %s %s' % (
            self.name, self.distribution.name, self.distrorelease.name)

    @property
    def distribution(self):
        """See IDistroReleaseBinaryPackage."""
        return self.distrorelease.distribution

    @property
    def cache(self):
        """See IDistroReleaseBinaryPackage."""
        return DistroReleasePackageCache.selectOne("""
            distrorelease = %s AND
            binarypackagename = %s
            """ % sqlvalues(self.distrorelease.id, self.binarypackagename.id))

    @property
    def summary(self):
        """See IDistroReleaseBinaryPackage."""
        cache = self.cache
        if cache is None:
            return None
        return cache.summary

    @property
    def description(self):
        """See IDistroReleaseBinaryPackage."""
        cache = self.cache
        if cache is None:
            return None
        return cache.description

    @property
    def current_publishings(self):
        """See IDistroReleaseBinaryPackage."""
        ret = BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.archive = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackagePublishingHistory.status != %s
            """ % sqlvalues(self.distrorelease,
                            self.distrorelease.main_archive,
                            self.binarypackagename,
                            PackagePublishingStatus.REMOVED),
            orderBy=['-datecreated'],
            clauseTables=['DistroArchRelease', 'BinaryPackageRelease'])
        return sorted(ret, key=lambda a: (
            a.distroarchrelease.architecturetag,
            a.datecreated))

