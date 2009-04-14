# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Interface for linking source packages in distroseries to branches."""

__metaclass__ = type
__all__ = [
    'ISeriesSourcePackageBranch',
    'ISeriesSourcePackageBranchSet',
    ]


from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Int

from canonical.launchpad import _
from canonical.launchpad.interfaces.publishing import PackagePublishingPocket


class ISeriesSourcePackageBranch(Interface):
    """Link /<distro>/<suite>/<package> to a branch."""

    id = Int()

    distroseries = Choice(
        title=_("Series"), required=True, vocabulary='DistroSeries')

    pocket = Choice(
        title=_("Pocket"), required=True, vocabulary=PackagePublishingPocket)

    sourcepackagename = Choice(
        title=_("Package"), required=True, vocabulary='SourcePackageName')

    branch = Choice(
        title=_("Branch"), vocabulary="Branch", required=True, readonly=True)

    registrant = Attribute("The person who registered this link.")

    date_created = Datetime(
        title=_("When the branch was linked to the distribution suite."))


class ISeriesSourcePackageBranchSet(Interface):
    """A set of links from source packages in distribution suites to branches.

    This doesn't really make sense as an interface, but is provided to match
    the rest of Launchpad.
    """

    def delete(sourcepackage, pocket):
        """Remove the SeriesSourcePackageBranch for sourcepackage and pocket.

        :param sourcepackage: An `ISourcePackage`.
        :param pocket: A `PackagePublishingPocket` enum item.
        """

    def getLinks(sourcepackage):
        """Get the links to branches from a source package.

        :param sourcepackage: An `ISourcePackage`.
        :return: An `IResultSet` of `ISeriesSourcePackageBranch` objects.
        """

    def new(distroseries, pocket, sourcepackagename, branch, registrant,
            date_created=None):
        """Link a source package in a distribution suite to a branch."""
