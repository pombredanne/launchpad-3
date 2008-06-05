# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Logic for bulk copying of source/binary publishing history data."""

__all__ = [
    'build_package_location',
    'PackageLocation',
    'PackageLocationError',
    'PubHistoryCopier',
    ]


from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import cursor, sqlvalues

from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchiveSet, IDistributionSet, NotFoundError,
    PackagePublishingPocket, PackagePublishingStatus)


class PackageLocation(object):
    """Object used to model locations when copying publications.

    It groups distribution, distroseries and pocket in a way they
    can be easily manipulated and compared.
    """
    archive = None
    distribution = None
    distroseries = None
    pocket = None
    distroarchseries = None
    component = None

    def __init__(self, archive, distribution, distroseries, pocket,
                 distroarchseries=None, component=None):
        """Initialize the PackageLocation from the given parameters."""
        self.archive = archive
        self.distribution = distribution
        self.distroseries = distroseries
        self.pocket = pocket
        self.distroarchseries = distroarchseries
        self.component = component

    def __eq__(self, other):
        if (self.distribution == other.distribution and
            self.archive == other.archive and
            self.distroseries == other.distroseries and
            self.distroarchseries == other.distroarchseries and
            self.component == other.component and
            self.pocket == other.pocket):
            return True
        return False

    def __str__(self):
        # Use ASCII-only for PPA titles, owner names can contain unicode.
        if self.archive.purpose == ArchivePurpose.PPA:
            title = self.archive.owner.name
        else:
            title = self.archive.title
        return '%s: %s-%s' % (
            title, self.distroseries.name, self.pocket.name)


class PackageLocationError(Exception):
    """Raised when something went wrong when building PackageLocation."""


def build_package_location(distribution_name, suite=None, purpose=None,
                           person_name=None):
    """Convenience function to build PackageLocation objects."""

    # XXX: we need a way to specify exactly what location we want
    # through strings in the commandline. Until we do, we will end up
    # with this horrible set of self-excluding options that make sense
    # to nobody. Perhaps:
    #   - ppa.launchpad.net/cprov/ubuntu/warty
    #   - archive.ubuntu.com/ubuntu-security/hoary
    #   - security.ubuntu.com/ubuntu/hoary
    #   - archive.canonical.com/gutsy
    #                                           -- kiko, 2007-10-24

    try:
        distribution = getUtility(IDistributionSet)[distribution_name]
    except NotFoundError, err:
        raise PackageLocationError(
            "Could not find distribution %s" % err)

    if purpose == ArchivePurpose.PPA:
        assert person_name is not None, (
            "person_name should be passed for PPA archives.")
        archive = getUtility(IArchiveSet).getPPAByDistributionAndOwnerName(
            distribution, person_name)
        if archive is None:
            raise PackageLocationError(
                "Could not find a PPA for %s" % person_name)
        if distribution != archive.distribution:
            raise PackageLocationError(
                "The specified archive is not for distribution %s"
                % distribution_name)
    elif purpose == ArchivePurpose.PARTNER:
        assert person_name is None, (
            "person_name shoudn't be passed for PARTNER archive.")
        archive = getUtility(IArchiveSet).getByDistroPurpose(
            distribution, purpose)
        if archive is None:
            raise PackageLocationError(
                "Could not find %s archive for %s" % (
                purpose.title, distribution_name))
    else:
        assert person_name is None, (
            "person_name shoudn't be passed when purpose is omitted.")
        archive = distribution.main_archive

    if suite is not None:
        try:
            distroseries, pocket = distribution.getDistroSeriesAndPocket(
                suite)
        except NotFoundError, err:
            raise PackageLocationError(
                "Could not find suite %s" % err)
    else:
        distroseries = distribution.currentseries
        pocket = PackagePublishingPocket.RELEASE

    return PackageLocation(archive, distribution, distroseries, pocket)


class PubHistoryCopier(object):
    """Used for copying of various publishing history data across archives.
    """

    def copy_binary_publishing_data(self, origin, destination):
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

    def copy_source_publishing_data(self, origin, destination):
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

