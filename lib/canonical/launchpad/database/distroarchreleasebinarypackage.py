
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent a binary package in a distroarchrelease."""

__metaclass__ = type

__all__ = [
    'DistroArchReleaseBinaryPackage',
    ]

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues
from canonical.lp.dbschema import PackagePublishingStatus
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease
    )
from canonical.launchpad.database.distroarchreleasebinarypackagerelease import (
    DistroArchReleaseBinaryPackageRelease
    )
from canonical.launchpad.database.distroreleasepackagecache import (
    DistroReleasePackageCache
    )
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory, SecureBinaryPackagePublishingHistory
    )
from canonical.launchpad.interfaces import (
    IDistroArchReleaseBinaryPackage,NotFoundError
    )


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
            distrorelease=self.distrorelease,
            binarypackagename=self.binarypackagename)
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
            distrorelease=self.distrorelease,
            binarypackagename=self.binarypackagename)
        if general is not None:
            return general.description
        return None


    def __getitem__(self, version):
        """See IDistroArchReleaseBinaryPackage."""
        query = """
        BinaryPackagePublishingHistory.distroarchrelease = %s AND
        BinaryPackagePublishingHistory.binarypackagerelease =
            BinaryPackageRelease.id AND
        BinaryPackageRelease.version = %s AND
        BinaryPackageRelease.binarypackagename = %s
        """ % sqlvalues(self.distroarchrelease.id, version,
                        self.binarypackagename.id)

        bpph = BinaryPackagePublishingHistory.selectFirst(
            query, clauseTables=['binarypackagerelease'],
            orderBy=["-datecreated"])

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
                BinaryPackagePublishingHistory.binarypackagerelease AND
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.status = %s
            """ % sqlvalues(self.binarypackagename.id,
                            self.distroarchrelease.id,
                            PackagePublishingStatus.PUBLISHED,
                            ),
            orderBy='datecreated',
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory',])

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

    @property
    def current_published(self):
        """See IDistroArchReleaseBinaryPackage."""
        current = BinaryPackagePublishingHistory.selectFirst("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackagePublishingHistory.status = %s
            """ % sqlvalues(self.distroarchrelease.id,
                            self.binarypackagename.id,
                            PackagePublishingStatus.PUBLISHED),
            clauseTables=['BinaryPackageRelease'],
            orderBy='-datecreated')

        if current is None:
            raise NotFoundError("Binary package %s not published in %s/%s"
                                % (self.binarypackagename.name,
                                   self.distroarchrelease.distrorelease.name,
                                   self.distroarchrelease.architecturetag))

        return current

    def changeOverride(self, new_component=None, new_section=None,
                       new_priority=None):
        """See IDistroArchReleaseBinaryPackage."""

        # Check we have been asked to do something
        if (new_component is None and new_section is None
            and new_priority is None):
            raise AssertionError("changeOverride must be passed a new"
                                 "component, section and/or priority.")

        # Retrieve current publishing info
        current = self.current_published

        # Check there is a change to make
        if new_component is None:
            new_component = current.component
        if new_section is None:
            new_section = current.section
        if new_priority is None:
            new_priority = current.priority

        if (new_component == current.component and
            new_section == current.section and
            new_priority == current.priority):
            return

        # Append the modified package publishing entry
        SecureBinaryPackagePublishingHistory(
            binarypackagerelease=current.binarypackagerelease,
            distroarchrelease=current.distroarchrelease,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            embargo=False,
            pocket=current.pocket,
            component=new_component,
            section=new_section,
            priority=new_priority,
            )

    def supersede(self):
        """See IDistroArchReleaseBinaryPackage."""
        # Retrieve current publishing info
        current = self.current_published
        current = SecureBinaryPackagePublishingHistory.get(current.id)
        current.status = PackagePublishingStatus.SUPERSEDED
        current.datesuperseded = UTC_NOW

        return current

    def copyTo(self, distrorelease, pocket):
        """See IDistroArchReleaseBinaryPackage."""
        # both lookups may raise NotFoundError, it should be treated in
        # the callsites.
        current = self.current_published
        target_dar = distrorelease[current.distroarchrelease.architecturetag]

        assert current.distroarchrelease.distrorelease == distrorelease, (
            "For now we only allow copy between pockets in the same "
            "distrorelease.")

        copy = SecureBinaryPackagePublishingHistory(
            binarypackagerelease=current.binarypackagerelease,
            distroarchrelease=target_dar,
            component=current.component,
            section=current.section,
            priority=current.priority,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=pocket
        )
        return copy
