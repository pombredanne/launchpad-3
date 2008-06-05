# Copyright 2005-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Source package in Distribution interfaces."""

__metaclass__ = type

__all__ = [
    'IDistributionSourcePackage',
    ]

from zope.interface import Attribute

from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget)


class IDistributionSourcePackage(IBugTarget, IStructuralSubscriptionTarget):
    """Represents a source package in a distribution.

    Create IDistributionSourcePackages by invoking
    `IDistribution.getSourcePackage()`.
    """

    distribution = Attribute("The distribution.")
    sourcepackagename = Attribute("The source package name.")

    name = Attribute("The source package name as text")
    displayname = Attribute("Display name for this package.")
    title = Attribute("Title for this package.")

    currentrelease = Attribute(
        "The latest published SourcePackageRelease of a source package with "
        "this name in the distribution or distroseries, or None if no source "
        "package with that name is published in this distroseries.")

    releases = Attribute(
        "The list of all releases of this source package "
        "in this distribution.")

    publishing_history = Attribute(
        "Return a list of publishing records for this source package in this "
        "distribution.")

    current_publishing_records = Attribute(
        "Return a list of CURRENT publishing records for this source "
        "package in this distribution.")

    binary_package_names = Attribute(
        "A string of al the binary package names associated with this source "
        "package in this distribution.")

    def __getitem__(version):
        """Should map to getVersion."""

    def getVersion(version):
        """Return the a DistributionSourcePackageRelease with the given
        version, or None if there has never been a release with that
        version in this distribution.
        """

    def get_distroseries_packages(active_only=True):
        """Return a list of DistroSeriesSourcePackage objects, each 
        representing this same source package in the serieses of this
        distribution.

        By default, this will return SourcePackage's in active
        distroseries only. You can set only_active=False to return a
        source package for EVERY series where this source package was
        published.
        """

    latest_overall_publication = Attribute(
        """The latest publication for this package across its distribution.

        The criteria for determining the publication are:
            - Only PUBLISHED or OBSOLETE publications
            - Only updates, security or release pockets
            - PUBLISHED wins over OBSOLETE
            - The latest distroseries wins
            - updates > security > release

        See https://bugs.edge.launchpad.net/soyuz/+bug/236922 for a plan
        on how this criteria will be centrally encoded.
        """)

    def bugtasks(quantity=None):
        """Bug tasks on this source package, sorted newest first.

        If needed, you can limit the number of bugtasks you are interested
        in using the quantity parameter.
        """

    def __eq__(other):
        """IDistributionSourcePackage comparison method.

        Distro sourcepackages compare equal only if their distribution and
        sourcepackagename compare equal.
        """

    def __ne__(other):
        """IDistributionSourcePackage comparison method.

        Distro sourcepackages compare not equal if either of their distribution
        or sourcepackagename compare not equal.
        """

