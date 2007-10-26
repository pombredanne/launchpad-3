# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""Classes to represent source package releases in a distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesSourcePackageRelease',
    ]

from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.database.build import Build
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory)
from canonical.launchpad.database.queue import PackageUpload
from canonical.launchpad.interfaces import (
    IDistroSeriesSourcePackageRelease, ISourcePackageRelease,
    PackagePublishingStatus, PackageUploadStatus)
from canonical.launchpad.scripts.ftpmaster import ArchiveOverriderError
from canonical.lp import decorates


class DistroSeriesSourcePackageRelease:
    """This is a "Magic SourcePackageRelease in Distro Release". It is not
    an SQLObject but instead it describes the behaviour of a specific
    release of the package in the distroseries."""

    implements(IDistroSeriesSourcePackageRelease)

    decorates(ISourcePackageRelease, context='sourcepackagerelease')

    def __init__(self, distroseries, sourcepackagerelease):
        self.distroseries = distroseries
        self.sourcepackagerelease = sourcepackagerelease

    @property
    def distribution(self):
        """See IDistroSeriesSourcePackageRelease."""
        return self.distroseries.distribution

    @property
    def displayname(self):
        """See IDistroSeriesSourcePackageRelease."""
        return '%s %s' % (self.name, self.version)

    @property
    def title(self):
        """See IDistroSeriesSourcePackageRelease."""
        return '%s %s (source) in %s %s' % (
            self.name, self.version, self.distribution.name,
            self.distroseries.name)

    @property
    def version(self):
        """See IDistroSeriesSourcePackageRelease."""
        return self.sourcepackagerelease.version

    @property
    def pocket(self):
        """See IDistroSeriesSourcePackageRelease."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.pocket

    @property
    def section(self):
        """See IDistroSeriesSourcePackageRelease."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.section

    @property
    def component(self):
        """See IDistroSeriesSourcePackageRelease."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.component

    @property
    def builds(self):
        """See IDistroSeriesSourcePackageRelease."""
        return Build.select("""
            Build.sourcepackagerelease = %s AND
            Build.distroarchrelease = DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s
            """ % sqlvalues(self.sourcepackagerelease.id,
                            self.distroseries.id),
            orderBy='-id',
            clauseTables=['DistroArchRelease'])

    @property
    def files(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.files

    @property
    def binaries(self):
        """See IDistroSeriesSourcePackageRelease."""
        clauseTables = [
            'BinaryPackageRelease',
            'DistroArchRelease',
            'Build',
            'BinaryPackagePublishingHistory'
        ]

        query = """
        BinaryPackageRelease.build=Build.id AND
        DistroArchRelease.id =
            BinaryPackagePublishingHistory.distroarchrelease AND
        BinaryPackagePublishingHistory.binarypackagerelease=
            BinaryPackageRelease.id AND
        DistroArchRelease.distrorelease=%s AND
        BinaryPackagePublishingHistory.archive IN %s AND
        Build.sourcepackagerelease=%s
        """ % sqlvalues(self.distroseries,
                        self.distroseries.distribution.all_distro_archive_ids,
                        self.sourcepackagerelease)

        return BinaryPackageRelease.select(
                query, prejoinClauseTables=['Build'],
                clauseTables=clauseTables, distinct=True)

    @property
    def meta_binaries(self):
        """See IDistroSeriesSourcePackageRelease."""
        return [self.distroseries.getBinaryPackage(
                    binary.binarypackagename)
                for binary in self.binaries]

    @property
    def changesfile(self):
        """See IDistroSeriesSourcePackageRelease."""
        clauseTables = [
            'PackageUpload',
            'PackageUploadSource',
            ]
        query = """
        PackageUpload.id = PackageUploadSource.packageupload AND
        PackageUpload.distrorelease = %s AND
        PackageUploadSource.sourcepackagerelease = %s AND
        PackageUpload.status = %s
        """ % sqlvalues(self.distroseries, self.sourcepackagerelease,
                        PackageUploadStatus.DONE)
        queue_record = PackageUpload.selectOne(
            query, clauseTables=clauseTables)

        if not queue_record:
            return None

        return queue_record.changesfile

    @property
    def published_binaries(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        target_binaries = []

        # Get the binary packages in each distroarchseries and store them
        # in target_binaries for returning.  We are looking for *published*
        # binarypackagereleases in all arches for the 'source' and its
        # location.
        for binary in self.binaries:
            if binary.architecturespecific:
                considered_arches = [binary.build.distroarchseries]
            else:
                considered_arches = self.distroseries.architectures

            for distroarchseries in considered_arches:
                dasbpr = distroarchseries.getBinaryPackage(
                    binary.name)[binary.version]
                # Only include objects with published binaries.
                if dasbpr is None or dasbpr.current_publishing_record is None:
                    continue
                target_binaries.append(dasbpr)

        return target_binaries

#
# Publishing lookup methods.
#

    @property
    def publishing_history(self):
        """See IDistroSeriesSourcePackage."""
        return SourcePackagePublishingHistory.select("""
            distrorelease = %s AND
            archive IN %s AND
            sourcepackagerelease = %s
            """ % sqlvalues(
                    self.distroseries,
                    self.distroseries.distribution.all_distro_archive_ids,
                    self.sourcepackagerelease),
            orderBy='-datecreated')

    @property
    def current_publishing_record(self):
        """An internal property used by methods of this class to know where
        this release is or was published.
        """
        pub_hist = self.publishing_history
        if pub_hist.count() == 0:
            return None
        return pub_hist[0]

    @property
    def current_published(self):
        """See IDistroArchSeriesSourcePackage."""
        # Retrieve current publishing info
        current = SourcePackagePublishingHistory.selectFirst("""
        distrorelease = %s AND
        archive IN %s AND
        sourcepackagerelease = %s AND
        status = %s
        """ % sqlvalues(self.distroseries,
                        self.distroseries.distribution.all_distro_archive_ids,
                        self.sourcepackagerelease,
                        PackagePublishingStatus.PUBLISHED),
            orderBy='-datecreated')

        return current
