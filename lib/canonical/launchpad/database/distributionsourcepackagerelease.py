# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""Classes to represent source package releases in a distribution."""

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageRelease',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import(
    IDistributionSourcePackageRelease, ISourcePackageRelease)

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.binarypackagename import BinaryPackageName
from canonical.launchpad.database.distroseriesbinarypackage import (
    DistroSeriesBinaryPackage)
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory)
from canonical.launchpad.database.build import Build
from canonical.launchpad.database.publishing import \
    SourcePackagePublishingHistory

from canonical.lp import decorates


class DistributionSourcePackageRelease:
    """This is a "Magic Distribution Source Package Release". It is not an
    SQLObject, but it represents the concept of a specific source package
    release in the distribution. You can then query it for useful
    information.
    """

    implements(IDistributionSourcePackageRelease)
    decorates(ISourcePackageRelease, context='sourcepackagerelease')

    def __init__(self, distribution, sourcepackagerelease):
        self.distribution = distribution
        self.sourcepackagerelease = sourcepackagerelease

    @property
    def sourcepackage(self):
        """See IDistributionSourcePackageRelease"""
        return self.distribution.getSourcePackage(
            self.sourcepackagerelease.sourcepackagename)

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
    def publishing_history(self):
        """See IDistributionSourcePackageRelease."""
        return SourcePackagePublishingHistory.select("""
            DistroSeries.distribution = %s AND
            SourcePackagePublishingHistory.distroseries =
                DistroSeries.id AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.sourcepackagerelease = %s
            """ % sqlvalues(self.distribution,
                            self.distribution.all_distro_archive_ids,
                            self.sourcepackagerelease),
            clauseTables=['DistroSeries'],
            orderBy='-datecreated')

    @property
    def builds(self):
        """See IDistributionSourcePackageRelease."""
        return Build.select("""
            Build.sourcepackagerelease = %s AND
            Build.distroarchseries = DistroArchSeries.id AND
            DistroArchSeries.distroseries = DistroSeries.id AND
            DistroSeries.distribution = %s
            """ % sqlvalues(self.sourcepackagerelease.id,
                            self.distribution.id),
            orderBy='-datecreated',
            clauseTables=['distroarchseries', 'distroseries'])

    @property
    def binary_package_names(self):
        """See IDistributionSourcePackageRelease."""
        return BinaryPackageName.select("""
            BinaryPackageName.id =
                BinaryPackageRelease.binarypackagename AND
            BinaryPackageRelease.build = Build.id AND
            Build.sourcepackagerelease = %s
            """ % sqlvalues(self.sourcepackagerelease.id),
            clauseTables=['BinaryPackageRelease', 'Build'],
            orderBy='name',
            distinct=True)

    @property
    def sample_binary_packages(self):
        """See IDistributionSourcePackageRelease."""
        all_published = BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchSeries.distroseries = DistroSeries.id AND
            DistroSeries.distribution = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.build = Build.id AND
            Build.sourcepackagerelease = %s
            """ % sqlvalues(self.distribution,
                            self.distribution.all_distro_archive_ids,
                            self.sourcepackagerelease),
            distinct=True,
            orderBy=['-datecreated'],
            clauseTables=['DistroArchSeries', 'DistroSeries',
                          'BinaryPackageRelease', 'Build'])
        samples = []
        names = set()
        for publishing in all_published:
            if publishing.binarypackagerelease.binarypackagename not in names:
                names.add(publishing.binarypackagerelease.binarypackagename)
                samples.append(
                    DistroSeriesBinaryPackage(
                        publishing.distroarchseries.distroseries,
                        publishing.binarypackagerelease.binarypackagename))
        return samples

