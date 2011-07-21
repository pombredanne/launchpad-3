# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0231

"""The content classes for links from source packages to branches.."""

__metaclass__ = type
__all__ = [
    'SeriesSourcePackageBranch',
    'SeriesSourcePackageBranchSet',
    ]

from datetime import datetime

import pytz
from storm.locals import (
    DateTime,
    Int,
    Reference,
    Storm,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.database.enumcol import DBEnum
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from lp.code.interfaces.seriessourcepackagebranch import (
    IFindOfficialBranchLinks,
    ISeriesSourcePackageBranch,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket


class SeriesSourcePackageBranch(Storm):
    """See `ISeriesSourcePackageBranch`."""

    __storm_table__ = 'SeriesSourcePackageBranch'
    implements(ISeriesSourcePackageBranch)

    id = Int(primary=True)
    distroseriesID = Int('distroseries')
    distroseries = Reference(distroseriesID, 'DistroSeries.id')

    pocket = DBEnum(enum=PackagePublishingPocket)

    sourcepackagenameID = Int('sourcepackagename')
    sourcepackagename = Reference(
        sourcepackagenameID, 'SourcePackageName.id')

    branchID = Int('branch')
    branch = Reference(branchID, 'Branch.id')

    registrantID = Int('registrant')
    registrant = Reference(registrantID, 'Person.id')

    date_created = DateTime(allow_none=False)

    def __init__(self, distroseries, pocket, sourcepackagename, branch,
                 registrant, date_created):
        """Construct an `ISeriesSourcePackageBranch`."""
        self.distroseries = distroseries
        self.pocket = pocket
        self.sourcepackagename = sourcepackagename
        self.branch = branch
        self.registrant = registrant
        self.date_created = date_created

    @property
    def sourcepackage(self):
        return self.distroseries.getSourcePackage(self.sourcepackagename)

    @property
    def suite_sourcepackage(self):
        return self.sourcepackage.getSuiteSourcePackage(self.pocket)


class SeriesSourcePackageBranchSet:
    """See `ISeriesSourcePackageBranchSet`."""

    implements(IFindOfficialBranchLinks)

    @staticmethod
    def new(distroseries, pocket, sourcepackagename, branch, registrant,
            date_created=None):
        """Link a source package in a distribution suite to a branch."""
        if date_created is None:
            date_created = datetime.now(pytz.UTC)
        sspb = SeriesSourcePackageBranch(
            distroseries, pocket, sourcepackagename, branch, registrant,
            date_created)
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        store.add(sspb)
        return sspb

    def findForBranch(self, branch):
        """See `IFindOfficialBranchLinks`."""
        return self.findForBranches([branch])

    def findForBranches(self, branches):
        """See `IFindOfficialBranchLinks`."""
        branch_ids = set(branch.id for branch in branches)
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            SeriesSourcePackageBranch,
            SeriesSourcePackageBranch.branchID.is_in(branch_ids))

    def findForSourcePackage(self, sourcepackage):
        """See `IFindOfficialBranchLinks`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        distroseries = sourcepackage.distroseries
        sourcepackagename = sourcepackage.sourcepackagename
        return store.find(
            SeriesSourcePackageBranch,
            SeriesSourcePackageBranch.distroseries == distroseries.id,
            SeriesSourcePackageBranch.sourcepackagename ==
            sourcepackagename.id)

    def findForDistributionSourcePackage(self, distrosourcepackage):
        """See `IFindOfficialBranchLinks`."""
        # To prevent circular imports.
        from lp.registry.model.distroseries import DistroSeries
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        distro = distrosourcepackage.distribution
        sourcepackagename = distrosourcepackage.sourcepackagename
        return store.find(
            SeriesSourcePackageBranch,
            DistroSeries.distribution == distro.id,
            SeriesSourcePackageBranch.distroseries == DistroSeries.id,
            SeriesSourcePackageBranch.sourcepackagename ==
            sourcepackagename.id)

    @staticmethod
    def delete(sourcepackage, pocket):
        """Remove the SeriesSourcePackageBranch for sourcepackage and pocket.

        :param sourcepackage: An `ISourcePackage`.
        :param pocket: A `PackagePublishingPocket` enum item.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        distroseries = sourcepackage.distroseries
        sourcepackagename = sourcepackage.sourcepackagename
        return store.find(
            SeriesSourcePackageBranch,
            SeriesSourcePackageBranch.distroseries == distroseries.id,
            SeriesSourcePackageBranch.sourcepackagename ==
            sourcepackagename.id,
            SeriesSourcePackageBranch.pocket == pocket).remove()
