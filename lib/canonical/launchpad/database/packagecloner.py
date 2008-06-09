# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Logic for bulk copying of source/binary publishing history data."""

__metaclass__ = type

__all__ = [
    'PackageCloner',
    ]


from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.interfaces import PackagePublishingStatus
from canonical.launchpad.interfaces.packagecloner import IPackageCloner


class PackageCloner:
    """Used for copying of various publishing history data across archives.
    """

    implements(IPackageCloner)

    def clonePackages(self, origin, destination, distroarchseries_list=None):
        """Copies packages from origin to destination package location.

        Binary packages are only copied for the DistroArchSeries pairs
        specified.

        @type origin: PackageLocation
        @param origin: the location from which packages are to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is to be copied.
        @type distroarchseries_list: list of pairs of (origin, destination)
            distroarchseries instances.
        @param distroarchseries_list: the binary packages will be copied
            for the distroarchseries pairs specified (if any).
        """
        # First clone the source packages.
        self._clone_source_packages(origin, destination)

        # Are we also supposed to clone binary packages from origin to
        # destination distroarchseries pairs?
        if distroarchseries_list is not None:
            for (origin_das, destination_das) in distroarchseries_list:
                self._clone_binary_packages(
                    origin, destination, origin_das, destination_das)


    def _clone_binary_packages(self, origin, destination, origin_das,
                              destination_das):
        """Copy binary publishing data from origin to destination.

        @type origin: PackageLocation
        @param origin: the location from which binary publishing
            records are to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is
            to be copied.
        @type origin_das: DistroArchSeries
        @param origin_das: the DistroArchSeries from which to copy
            binary packages
        @type destination_das: DistroArchSeries
        @param destination_das: the DistroArchSeries to which to copy
            binary packages
        """
        cur = cursor()
        cur.execute('''
            INSERT INTO SecureBinaryPackagePublishingHistory (
                binarypackagerelease, distroarchseries, status,
                component, section, priority, archive, datecreated,
                datepublished, pocket, embargo)
            SELECT bpph.binarypackagerelease, %s as distroarchseries,
                   bpph.status, bpph.component, bpph.section, bpph.priority,
                   %s as archive, %s as datecreated, %s as datepublished,
                   %s as pocket, false as embargo
            FROM BinaryPackagePublishingHistory AS bpph
            WHERE bpph.distroarchseries = %s AND bpph.status in (%s, %s)
            AND
                bpph.pocket = %s and bpph.archive = %s
            ''' % sqlvalues(
                destination_das, destination.archive,
                UTC_NOW, UTC_NOW, destination.pocket,
                origin_das,
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED,
                origin.pocket, origin.archive))

    def _clone_source_packages(self, origin, destination):
        """Copy source publishing data from origin to destination.

        @type origin: PackageLocation
        @param origin: the location from which source publishing
            records are to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is
            to be copied.
        """
        cur = cursor()
        cur.execute('''
            INSERT INTO SecureSourcePackagePublishingHistory (
                sourcepackagerelease, distroseries, status, component,
                section, archive, datecreated, datepublished, pocket,
                embargo)
            SELECT spph.sourcepackagerelease, %s as distroseries,
                   spph.status, spph.component, spph.section, %s as archive,
                   %s as datecreated, %s as datepublished,
                   %s as pocket, false as embargo
            FROM SourcePackagePublishingHistory AS spph
            WHERE spph.distroseries = %s AND spph.status in (%s, %s) AND
                  spph.pocket = %s and spph.archive = %s
            ''' % sqlvalues(
                destination.distroseries, destination.archive, UTC_NOW,
                UTC_NOW, destination.pocket, origin.distroseries,
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED,
                origin.pocket, origin.archive))

