# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent binary package releases in a
distributionarchitecture release."""

__metaclass__ = type

__all__ = [
    'DistroArchReleaseBinaryPackageRelease',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import (
    IDistroArchReleaseBinaryPackageRelease)

from canonical.database.sqlbase import sqlvalues

from canonical.lp.dbschema import PackagePublishingStatus

from canonical.launchpad.database.build import Build
from canonical.launchpad.database.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease)
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory, BinaryPackagePublishing)

class DistroArchReleaseBinaryPackageRelease:

    implements(IDistroArchReleaseBinaryPackageRelease)

    def __init__(self, distroarchrelease, binarypackagerelease):
        self.distroarchrelease = distroarchrelease
        self.binarypackagerelease = binarypackagerelease

    @property
    def name(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        return self.binarypackagerelease.binarypackagename.name

    @property
    def version(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        return self.binarypackagerelease.version

    @property
    def distrorelease(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        return self.distroarchrelease.distrorelease

    @property
    def distribution(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        return self.distroarchrelease.distrorelease.distribution

    @property
    def displayname(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        return '%s %s' % (self.name, self.version)

    @property
    def title(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        return '%s %s (%s binary) in %s %s' % (
            self.name, self.version, self.distroarchrelease.architecturetag,
            self.distribution.name, self.distrorelease.name)

    @property
    def distributionsourcepackagerelease(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        return DistributionSourcePackageRelease(
            self.distribution,
            self.build.sourcepackagerelease)

    @property
    def current_publishing_record(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        bpps = BinaryPackagePublishing.select("""
            binarypackagerelease = %s AND
            distroarchrelease = %s AND
            status = %s
            """ % sqlvalues(self.binarypackagerelease.id,
                            self.distroarchrelease.id,
                            PackagePublishingStatus.PUBLISHED),
            orderBy='-datecreated')
        if len(bpps) == 0:
            return None
        assert len(bpps) < 2, '%s multiple publishing records' % self.title
        return bpps[0]

    @property
    def publishing_history(self):
        """See IDistroArchReleaseBinaryPackage."""
        return BinaryPackagePublishingHistory.select("""
            distroarchrelease = %s AND
            binarypackagerelease = %s
            """ % sqlvalues(self.distroarchrelease.id,
                            self.binarypackagerelease.id),
            orderBy='-datecreated')

    @property
    def pocket(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        pub = self.current_publishing_record
        if pub is None:
            return None
        return pub.pocket

    @property
    def status(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        pub = self.current_publishing_record
        if pub is None:
            return None
        return pub.status

    @property
    def section(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        pub = self.current_publishing_record
        if pub is None:
            return None
        return pub.section

    @property
    def component(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        pub = self.current_publishing_record
        if pub is None:
            return None
        return pub.component

    @property
    def priority(self):
        """See IDistroArchReleaseBinaryPackageRelease."""
        pub = self.current_publishing_record
        if pub is None:
            return None
        return pub.priority

    # map the BinaryPackageRelease attributes up to this class so it
    # responds to the same interface

    @property
    def binarypackagename(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.binarypackagename

    @property
    def summary(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.summary

    @property
    def description(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.description

    @property
    def build(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.build

    @property
    def binpackageformat(self):
        """See IPackageRelease."""
        return self.binarypackagerelease.binpackageformat

    @property
    def shlibdeps(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.shlibdeps

    @property
    def depends(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.depends

    @property
    def recommends(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.recommends

    @property
    def replaces(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.replaces

    @property
    def conflicts(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.conflicts

    @property
    def provides(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.provides

    @property
    def suggests(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.suggests

    @property
    def essential(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.essential

    @property
    def installedsize(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.installedsize

    @property
    def copyright(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.copyright

    @property
    def licence(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.licence

    @property
    def architecturespecific(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.architecturespecific

    @property
    def datecreated(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.datecreated

    @property
    def files(self):
        """See IBinaryPackageRelease."""
        return self.binarypackagerelease.files

