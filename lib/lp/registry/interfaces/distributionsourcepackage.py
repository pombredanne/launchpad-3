# Copyright 2005-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Source package in Distribution interfaces."""

__metaclass__ = type

__all__ = [
    'IDistributionSourcePackage',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Int, TextLine

from canonical.lazr.fields import Reference
from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, export_operation_as, export_read_operation,
    exported, operation_parameters, operation_returns_collection_of,
    rename_parameters_as)

from canonical.launchpad import _
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.bugtask import IBugTask
from lp.registry.interfaces.distribution import IDistribution
from canonical.launchpad.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget)


class IDistributionSourcePackage(IBugTarget, IStructuralSubscriptionTarget):
    """Represents a source package in a distribution.

    Create IDistributionSourcePackages by invoking
    `IDistribution.getSourcePackage()`.
    """

    export_as_webservice_entry()

    distribution = exported(
        Reference(IDistribution, title=_("The distribution.")))
    sourcepackagename = Attribute("The source package name.")

    name = exported(
        TextLine(title=_("The source package name as text"), readonly=True))
    displayname = exported(
        TextLine(title=_("Display name for this package."), readonly=True),
        exported_as="display_name")
    title = exported(
        TextLine(title=_("Title for this package."), readonly=True))

    upstream_product = exported(
        Reference(
            title=_("The upstream product to which this package is linked."),
            required=False,
            readonly=True,
            # This is really an IProduct but we get a circular import
            # problem if we do that here. This is patched in
            # interfaces/product.py.
            schema=Interface))

    currentrelease = Attribute(
        "The latest published SourcePackageRelease of a source package with "
        "this name in the distribution or distroseries, or None if no source "
        "package with that name is published in this distroseries.")

    releases = Attribute(
        "The list of all releases of this source package "
        "in this distribution.")

    def getReleasesAndPublishingHistory():
        """Return a list of all releases of this source package in this
        distribution and their correspodning publishing history.

        Items in the list are tuples comprised of a
        DistributionSourcePackage and a list of
        SourcePackagePublishingHistory objects.
        """

    publishing_history = Attribute(
        "Return a list of publishing records for this source package in this "
        "distribution.")

    current_publishing_records = Attribute(
        "Return a list of CURRENT publishing records for this source "
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

    @rename_parameters_as(quantity='limit')
    @operation_parameters(
        quantity=Int(
            title=_("The maximum number of bug tasks to return"),
            min=1))
    @operation_returns_collection_of(IBugTask)
    @export_operation_as(name="getBugTasks")
    @export_read_operation()
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

