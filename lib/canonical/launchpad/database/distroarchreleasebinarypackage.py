
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent a binary package in a distroarchrelease."""

__metaclass__ = type

__all__ = [
    'DistroArchReleaseBinaryPackage',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import IDistroArchReleaseBinaryPackage

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.distroarchreleasebinarypackagerelease import \
    DistroArchReleaseBinaryPackageRelease
from distroreleasepackagecache import DistroReleasePackageCache
from canonical.launchpad.database.publishing import \
    BinaryPackagePublishingHistory
from canonical.launchpad.database.binarypackagerelease import \
    BinaryPackageRelease
from sourcerer.deb.version import Version


class DistroArchReleaseBinaryPackage:

    implements(IDistroArchReleaseBinaryPackage)

    def __init__(self, distroarchrelease, binarypackagename):
        self.distroarchrelease = distroarchrelease
        self.binarypackagename = binarypackagename

    @property
    def name(self):
        """See IDistroArchReleaseBinaryPackage."""
        return self.binarypackagename.name

    @property
    def distrorelease(self):
        """See IDistroArchRelease."""
        return self.distroarchrelease.distrorelease

    @property
    def distribution(self):
        """See IDistroArchRelease."""
        return self.distrorelease.distribution

    @property
    def displayname(self):
        """See IDistroArchReleaseBinaryPackage."""
        return '%s in %s %s' % (
            self.binarypackagename.name,
            self.distroarchrelease.distrorelease.name,
            self.distroarchrelease.architecturetag)

    @property
    def title(self):
        """See IDistroArchReleaseBinaryPackage."""
        return 'Binary Package "%s" in %s' % (
            self.binarypackagename.name, self.distroarchrelease.title)

    @property
    def summary(self):
        """See IDistroArchReleaseBinaryPackage."""
        curr = self.currentrelease
        if curr is not None:
            return curr.summary
        general = DistroReleasePackageCache.selectOneBy(
            distroreleaseID=self.distrorelease.id,
            binarypackagenameID=self.binarypackagename.id)
        if general is not None:
            return general.summary
        return None

    @property
    def description(self):
        """See IDistroArchReleaseBinaryPackage."""
        curr = self.currentrelease
        if curr is not None:
            return curr.description
        general = DistroReleasePackageCache.selectOneBy(
            distroreleaseID=self.distrorelease.id,
            binarypackagenameID=self.binarypackagename.id)
        if general is not None:
            return general.description
        return None


    def __getitem__(self, version):
        """See IDistroArchReleaseBinaryPackage."""
        bpph = BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease = 
                BinaryPackageRelease.id AND
            BinaryPackageRelease.version = %s
            """ % sqlvalues(self.distroarchrelease.id, version),
            orderBy='-datecreated',
            clauseTables=['binarypackagerelease'])
        if bpph.count() == 0:
            return None
        return DistroArchReleaseBinaryPackageRelease(
            distroarchrelease=self.distroarchrelease,
            binarypackagerelease=bpph[0].binarypackagerelease)

    @property
    def releases(self):
        """See IDistroArchReleaseBinaryPackage."""
        ret = BinaryPackageRelease.select("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s
            """ % sqlvalues(self.distroarchrelease.id,
                            self.binarypackagename.id),
            orderBy='-datecreated',
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory'])
        result = []
        versions = set()
        for bpr in ret:
            if bpr.version not in versions:
                versions.add(bpr.version)
                darbpr = DistroArchReleaseBinaryPackageRelease(
                    distroarchrelease=self.distroarchrelease,
                    binarypackagerelease=bpr)
                result.append(darbpr)
        return result

    @property
    def currentrelease(self):
        """See IDistroArchReleaseBinaryPackage."""
        bprs = BinaryPackageRelease.select("""
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackageRelease.id =
                BinaryPackagePublishing.binarypackagerelease AND
            BinaryPackagePublishing.distroarchrelease = %s
            """ % sqlvalues(self.binarypackagename.id,
                            self.distroarchrelease.id),
            orderBy='datecreated',
            distinct=True,
            clauseTables=['BinaryPackagePublishing',])
        
        # sort by version
        releases = sorted(list(bprs), key=lambda item: Version(item.version))
        if len(releases) == 0:
            return None
        return DistroArchReleaseBinaryPackageRelease(
            distroarchrelease=self.distroarchrelease,
            binarypackagerelease=releases[-1])

    @property
    def publishing_history(self):
        """See IDistroArchReleaseBinaryPackage."""
        return BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease = 
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s
            """ % sqlvalues(self.distroarchrelease.id,
                            self.binarypackagename.id),
            distinct=True,
            clauseTables=['BinaryPackageRelease'],
            orderBy='-datecreated')


