# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent source package releases in a distribution."""

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageRelease',
    'DistributionSourcePackageReleaseSet'
    ]

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistributionSourcePackageRelease, IDistributionSourcePackageReleaseSet,
    IDistributionSourcePackageSet)

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.binarypackagename import BinaryPackageName
from canonical.launchpad.database.distroreleasebinarypackage import (
    DistroReleaseBinaryPackage)
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory)
from canonical.launchpad.database.build import Build
from canonical.launchpad.database.publishing import \
    SourcePackagePublishingHistory


class DistributionSourcePackageRelease:
    """This is a "Magic Distribution Source Package Release". It is not an
    SQLObject, but it represents the concept of a specific source package
    release in the distribution. You can then query it for useful
    information.
    """

    implements(IDistributionSourcePackageRelease)

    def __init__(self, distribution, sourcepackagerelease):
        self.distribution = distribution
        self.sourcepackagerelease = sourcepackagerelease

    @property
    def sourcepackage(self):
        """See IDistributionSourcePackageRelease"""
        return getUtility(IDistributionSourcePackageSet).generate(
            self.distribution, self.sourcepackagerelease.sourcepackagename)

    @property
    def name(self):
        """See IDistributionSourcePackageRelease."""
        return '%s' % self.sourcepackagerelease.sourcepackagename.name

    @property
    def displayname(self):
        """See IDistributionSourcePackageRelease."""
        return '%s in %s' % (self.name, self.distribution.name)

    @property
    def title(self):
        """See IDistributionSourcePackageRelease."""
        return '%s %s (source) in %s' % (
            self.name, self.version, self.distribution.displayname)

    @property
    def version(self):
        """See IDistributionSourcePackageRelease."""
        return self.sourcepackagerelease.version

    @property
    def publishing_history(self):
        """See IDistributionSourcePackageRelease."""
        return SourcePackagePublishingHistory.select("""
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.distrorelease = 
                DistroRelease.id AND
            SourcePackagePublishingHistory.sourcepackagerelease = %s
            """ % sqlvalues(self.distribution.id,
                            self.sourcepackagerelease.id),
            clauseTables=['DistroRelease'],
            orderBy='-datecreated')

    @property
    def builds(self):
        """See IDistributionSourcePackageRelease."""
        return Build.select("""
            Build.sourcepackagerelease = %s AND
            Build.distroarchrelease = DistroArchRelease.id AND
            DistroArchRelease.distrorelease = DistroRelease.id AND
            DistroRelease.distribution = %s
            """ % sqlvalues(self.sourcepackagerelease.id,
                            self.distribution.id),
            orderBy='-datecreated',
            clauseTables=['distroarchrelease', 'distrorelease'])

    @property
    def binary_package_names(self):
        """See IDistributionSourcePackageRelease."""
        return BinaryPackageName.select("""
            BinaryPackageName.id =
                BinaryPackageRelease.binarypackagename AND
            BinaryPackageRelease.build = Build.id AND
            Build.sourcepackagerelease = %s
            """ % sqlvalues(self.sourcepackagerelease.id),
            clauseTable=['BinaryPackageRelease', 'Build'],
            orderBy='name',
            distinct=True)

    @property
    def sample_binary_packages(self):
        """See IDistributionSourcePackageRelease."""
        all_published = BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = DistroRelease.id AND
            DistroRelease.distribution = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease = 
                BinaryPackageRelease.id AND
            BinaryPackageRelease.build = Build.id AND
            Build.sourcepackagerelease = %s
            """ % sqlvalues(self.distribution.id,
                            self.sourcepackagerelease.id),
            distinct=True,
            orderBy=['-datecreated'],
            clauseTables=['DistroArchRelease', 'DistroRelease', 
                          'BinaryPackageRelease', 'Build'])
        samples = []
        names = set()
        for publishing in all_published:
            if publishing.binarypackagerelease.binarypackagename not in names:
                names.add(publishing.binarypackagerelease.binarypackagename)
                samples.append(
                    DistroReleaseBinaryPackage(
                        publishing.distroarchrelease.distrorelease,
                        publishing.binarypackagerelease.binarypackagename))
        return samples


class DistributionSourcePackageReleaseSet:
    """See IDistributionSourcePackageReleaseSet"""

    implements(IDistributionSourcePackageReleaseSet)

    def generate(self, distribution, sourcepackagerelease):
        """See IDistributionSourcePackageReleaseSet"""
        return DistributionSourcePackageRelease(distribution,
                                                sourcepackagerelease)
    
