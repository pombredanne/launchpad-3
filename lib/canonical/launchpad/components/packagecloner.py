# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Logic for bulk copying of source/binary publishing history data."""

__all__ = [
    'PackageCloner',
    ]


from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import cursor, sqlvalues

from canonical.launchpad.interfaces import PackagePublishingStatus


class PackageCloner(object):
    """Used for copying of various publishing history data across archives.
    """

    def clone_binary_packages(self, origin, destination):
        """Copy binary publishing data from origin to destination.

        @type origin: PackageLocation
        @param origin: the location from which binary publishing
            records are to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is
            to be copied.
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
                destination.distroarchseries, destination.archive,
                UTC_NOW, UTC_NOW, destination.pocket,
                origin.distroarchseries,
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED,
                origin.pocket, origin.archive))

    def clone_source_packages(self, origin, destination):
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

