# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for builds."""

__metaclass__ = type

__all__ = [
    'BuildNavigation',
    'BuildFacets',
    'BuildRecordsView',
    ]

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from canonical.lp.dbschema import BuildStatus

from canonical.launchpad.interfaces import IHasBuildRecords

from canonical.launchpad.interfaces import IBuild

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, GetitemNavigation, stepthrough)


class BuildNavigation(GetitemNavigation):
    usedfor = IBuild


class BuildFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IBuild."""
    enable_only = ['overview']

    usedfor = IBuild


class BuildRecordsView:
    __used_for__ = IHasBuildRecords

    def getBuilds(self):
        """Setup a batched build list"""

        builds = self.context.getBuildRecords()
        self.batch = Batch(list(builds),
                           int(self.request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, self.request)

        return self.batch

    def showBuilderInfo(self):
        """Control the presentation o builder information.

        It allows the callsite to control if they want or not builder column
        in its result list (ommited in builder-index page only)
        """
        return True

