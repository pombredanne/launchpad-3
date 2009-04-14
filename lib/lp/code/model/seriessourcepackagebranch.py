# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The content classes for links from source packages to branches.."""

__metaclass__ = type
__all__ = [
    'SeriesSourcePackageBranch',
    'SeriesSourcePackageBranchSet',
    ]

from datetime import datetime

import pytz

from storm.locals import DateTime, Int, Reference, Storm

from zope.component import getUtility
from zope.interface import implements

from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.publishing import PackagePublishingPocket
from lp.code.interfaces.seriessourcepackagebranch import (
    ISeriesSourcePackageBranch, ISeriesSourcePackageBranchSet)
from canonical.launchpad.webapp.interfaces import (
     DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


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


class SeriesSourcePackageBranchSet:
    """See `ISeriesSourcePackageBranchSet`."""

    implements(ISeriesSourcePackageBranchSet)

    def new(self, distroseries, pocket, sourcepackagename, branch, registrant,
            date_created=None):
        """See `ISeriesSourcePackageBranchSet`."""
        if date_created is None:
            date_created = datetime.now(pytz.UTC)
        sspb = SeriesSourcePackageBranch(
            distroseries, pocket, sourcepackagename, branch, registrant,
            date_created)
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        store.add(sspb)
        return sspb

    def findForSourcePackage(self, sourcepackage):
        """See `ISeriesSourcePackageBranchSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        distroseries = sourcepackage.distroseries
        sourcepackagename = sourcepackage.sourcepackagename
        return store.find(
            SeriesSourcePackageBranch,
            SeriesSourcePackageBranch.distroseries == distroseries.id,
            SeriesSourcePackageBranch.sourcepackagename ==
            sourcepackagename.id)

    def delete(self, sourcepackage, pocket):
        """See `ISeriesSourcePackageBranchSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        distroseries = sourcepackage.distroseries
        sourcepackagename = sourcepackage.sourcepackagename
        return store.find(
            SeriesSourcePackageBranch,
            SeriesSourcePackageBranch.distroseries == distroseries.id,
            SeriesSourcePackageBranch.sourcepackagename ==
            sourcepackagename.id).remove()
