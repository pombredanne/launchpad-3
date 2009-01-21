# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to bulk copying of publishing history data."""

__metaclass__ = type

__all__ = [
    'IPackageCloner'
    ]

from zope.interface import Interface

class IPackageCloner(Interface):
    """Copies publishing history data across archives."""

    def clonePackages(origin, destination, distroarchseries_list=None):
        """Copies the source packages from origin to destination as
        well as the binary packages for the DistroArchSeries specified.

        @type origin: PackageLocation
        @param origin: the location from which packages are to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is to be copied.
        @type distroarchseries_list: list of pairs of (origin, destination)
            distroarchseries instances.
        @param distroarchseries_list: the binary packages will be copied
            for the distroarchseries pairs specified (if any).
        """

    def mergeCopy(origin, destination):
        """Copy packages that are obsolete or missing in target archive.

        Copy source packages from a given source archive that are obsolete or
        missing in the target archive.

        @type origin: PackageLocation
        @param origin: the location from which the data is to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is to be copied.
        """

    def packageSetDiff(origin, destination, diagnostic_output=None):
        """Find packages that are obsolete or missing in target archive.

        @type origin: PackageLocation
        @param origin: the location with potentially new or fresher packages.
        @type destination: PackageLocation
        @param destination: the target location.
        @type diagnostic_output: (open) file handle
        @param diagnostic_output: an optional (open) file handle to which
            details of the source packages that are fresher and new in the
            origin archive will be written.
        @return a 2-tuple (fresher, new) where each element is a sequence
            of `SecureSourcePackagePublishingHistory` keys of packages
            that are fresher and new in the origin archive respectively.
        """

