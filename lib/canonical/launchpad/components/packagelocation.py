# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Logic for bulk copying of source/binary publishing history data."""

__all__ = [
    'build_package_location',
    'PackageLocation',
    'PackageLocationError',
    ]


from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchiveSet, IDistributionSet, NotFoundError,
    PackagePublishingPocket)


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

    def __init__(self, archive, distribution, distroseries, pocket,
                 distroarchseries=None):
        """Initialize the PackageLocation from the given parameters."""
        self.archive = archive
        self.distribution = distribution
        self.distroseries = distroseries
        self.pocket = pocket
        self.distroarchseries = distroarchseries

    def __eq__(self, other):
        if (self.distribution == other.distribution and
            self.archive == other.archive and
            self.distroseries == other.distroseries and
            self.distroarchseries == other.distroarchseries and
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
