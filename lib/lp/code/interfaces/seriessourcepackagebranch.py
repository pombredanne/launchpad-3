# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0213

"""Interface for linking source packages in distroseries to branches."""

__metaclass__ = type
__all__ = [
    'IFindOfficialBranchLinks',
    'ISeriesSourcePackageBranch',
    'IMakeOfficialBranchLinks',
    ]


from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Int,
    )

from canonical.launchpad import _
from lp.registry.interfaces.pocket import PackagePublishingPocket


class ISeriesSourcePackageBranch(Interface):
    """Link /<distro>/<suite>/<package> to a branch."""

    id = Int()

    distroseries = Choice(
        title=_("Series"), required=True, vocabulary='DistroSeries')

    pocket = Choice(
        title=_("Pocket"), required=True, vocabulary=PackagePublishingPocket)

    sourcepackage = Attribute('The source package')

    suite_sourcepackage = Attribute('The suite source package')

    sourcepackagename = Choice(
        title=_("Package"), required=True, vocabulary='SourcePackageName')

    branchID = Attribute('The ID of the branch.')
    branch = Choice(
        title=_("Branch"), vocabulary="Branch", required=True, readonly=True)

    registrant = Attribute("The person who registered this link.")

    date_created = Datetime(
        title=_("When the branch was linked to the distribution suite."))


class IFindOfficialBranchLinks(Interface):
    """Find the links for official branches for pockets on source packages.
    """

    def findForBranch(branch):
        """Get the links to source packages from a branch.

        :param branch: An `IBranch`.
        :return: An `IResultSet` of `ISeriesSourcePackageBranch` objects.
        """

    def findForBranches(branches):
        """Get the links to source packages from a branch.

        :param branches: A an iterable of `IBranch`.
        :return: An `IResultSet` of `ISeriesSourcePackageBranch` objects.
        """

    def findForSourcePackage(sourcepackage):
        """Get the links to branches from a source package.

        :param sourcepackage: An `ISourcePackage`.
        :return: An `IResultSet` of `ISeriesSourcePackageBranch` objects.
        """

    def findForDistributionSourcePackage(distrosourcepackage):
        """Get the links to branches for a distribution source package.

        :param distrosourcepackage: An `IDistributionSourcePackage`.
        :return: An `IResultSet` of `ISeriesSourcePackageBranch` objects.
        """


class IMakeOfficialBranchLinks(Interface):
    """A set of links from source packages in distribution suites to branches.

    This doesn't really make sense as an interface, but is provided to match
    the rest of Launchpad.
    """

    def delete(sourcepackage, pocket):
        """Remove the SeriesSourcePackageBranch for sourcepackage and pocket.

        :param sourcepackage: An `ISourcePackage`.
        :param pocket: A `PackagePublishingPocket` enum item.
        """

    def new(distroseries, pocket, sourcepackagename, branch, registrant,
            date_created=None):
        """Link a source package in a distribution suite to a branch."""
