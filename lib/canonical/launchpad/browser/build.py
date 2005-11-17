# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for builds."""

__metaclass__ = type

__all__ = [
    'BuildNavigation',
    'BuildFacets',
    'BuildRecordsView',
    ]

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

    def getBuilt(self):
        """Return the build entries built within the context object."""
        return self.context.getBuildRecords(status=BuildStatus.FULLYBUILT)

    @property
    def number_built(self):
        """Return the number of build entries built for context object.

        If no result is available return None.
        """
        result = self.context.getBuildRecords(status=BuildStatus.FULLYBUILT,
                                              limit=0)
        if result:
            return result.count()
        return None

    def getPending(self):
        """Return the builds entries pending build for the context object."""
        return self.context.getBuildRecords(status=BuildStatus.NEEDSBUILD)

    @property
    def number_pending(self):
        """Return the number of build entries pending for the context object.

        If no result is available return None.
        """
        result = self.context.getBuildRecords(status=BuildStatus.NEEDSBUILD,
                                              limit=0)
        if result:
            return result.count()
        return None

    def getFailed(self):
        """Return the builds entries failed to build for the context object."""
        return self.context.getBuildRecords(status=BuildStatus.FAILEDTOBUILD)

    @property
    def number_failed(self):
        """Return the number of build entries failures for the context object.

        If no result is available return None.
        """
        result = self.context.getBuildRecords(status=BuildStatus.FAILEDTOBUILD,
                                              limit=0)
        if result:
            return result.count()
        return None


