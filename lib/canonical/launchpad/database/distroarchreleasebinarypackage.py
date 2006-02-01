
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent a binary package in a distroarchrelease."""

__metaclass__ = type

__all__ = [
    'DistroArchReleaseBinaryPackage',
    ]

from zope.interface import implements

from canonical.lp.dbschema import PackagePublishingStatus

from canonical.launchpad.interfaces import (IDistroArchReleaseBinaryPackage,
                                            NotFoundError)

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.distroarchreleasebinarypackagerelease import \
    DistroArchReleaseBinaryPackageRelease
from distroreleasepackagecache import DistroReleasePackageCache
from canonical.launchpad.database.publishing import (BinaryPackagePublishingHistory,
                                                     SecureBinaryPackagePublishingHistory)
from canonical.launchpad.database.binarypackagerelease import \
    BinaryPackageRelease


class DistroArchReleaseBinaryPackage:
    """A Binary Package in the context of a Distro Arch Release. 

    Binary Packages are "magic": they don't really exist in the
    database. Instead, they are synthesized based on information from
    the publishing and binarypackagerelease tables.
    """

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
        bpph = BinaryPackagePublishingHistory.selectOne("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease = 
                BinaryPackageRelease.id AND
            BinaryPackageRelease.version = %s AND
            BinaryPackageRelease.binarypackagename = %s
            """ % sqlvalues(self.distroarchrelease.id, version, 
                            self.binarypackagename.id),
            clauseTables=['binarypackagerelease'])
        if bpph is None:
            return None
        return DistroArchReleaseBinaryPackageRelease(
            distroarchrelease=self.distroarchrelease,
            binarypackagerelease=bpph.binarypackagerelease)

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
        releases = BinaryPackageRelease.select("""
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackageRelease.id =
                BinaryPackagePublishing.binarypackagerelease AND
            BinaryPackagePublishing.distroarchrelease = %s AND
            BinaryPackagePublishing.status = %s
            """ % sqlvalues(self.binarypackagename.id,
                            self.distroarchrelease.id,
                            PackagePublishingStatus.PUBLISHED,
                            ),
            orderBy='datecreated',
            distinct=True,
            clauseTables=['BinaryPackagePublishing',])

        # sort by version
        if releases.count() == 0:
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

    def changeOverride(self, new_component=None, new_section=None,
                       new_priority=None):
        """See IDistroArchReleaseBinaryPackage."""

        # Check we have been asked to do something
        if (new_component is None and new_section is None 
            and new_priority is None):
            raise AssertionError("changeOverride must be passed a new"
                                 "component, section or priority.")

        # Retrieve current publishing info
        current = self.publishing_history[-1]

        # Check there is a change to make
        if new_component is None:
            new_component = current.component
        if new_section is None:
            new_section = current.section
        if new_priority is None:
            new_priority = current.priorty

        if (new_component == current.component and
            new_section == current.section and
            new_priority == current.priority):
            return

        # Append the modified package publishing entry
        SecureBinaryPackagePublishingHistory(
            binarypackagerelease=current.binarypackagerelease,
            distroarchrelease=current.distroarchrelease,
            component=new_component,
            section=new_section,
            priority=new_priority,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=current.pocket,
            embargo=False,
            )
        
    def supersede(self):
        """See IDistroArchReleaseBinaryPackage."""

        # Find the current publishing record
        if not self.publishing_history:
            raise NotFoundError("Binary package %s not published in %s/%s"
                                % (self.binarypackagename.name,
                                   self.distroarchrelease.distrorelease.name,
                                   self.distroarchrelease.architecturetag))

        current = self.publishing_history[-1]
        current = SecureBinaryPackagePublishingHistory.get(current.id)
        current.status = PackagePublishingStatus.SUPERSEDED
        current.datesuperseded = UTC_NOW
