# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for builds."""

__metaclass__ = type

__all__ = [
    'BuildNavigation',
    'BuildFacets',
    'BuildOverviewMenu',
    'BuildView',
    'BuildRecordsView',
    ]

from canonical.lp.dbschema import BuildStatus

from canonical.launchpad.interfaces import IHasBuildRecords

from canonical.launchpad.interfaces import IBuild

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, GetitemNavigation, stepthrough,
    ApplicationMenu, LaunchpadView, enabled_with_permission)


class BuildNavigation(GetitemNavigation):
    usedfor = IBuild


class BuildFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IBuild."""
    enable_only = ['overview']

    usedfor = IBuild

class BuildOverviewMenu(ApplicationMenu):
    """Overview menu for build records """
    usedfor = IBuild
    facet = 'overview'
    links = ['changes', 'buildlog', 'reset']

    def changes(self):
        text = 'View Changes'
        return Link('+changes', text, icon='info')

    def buildlog(self):
        text = 'View Buildlog'
        return Link('+buildlog', text, icon='info')

    @enabled_with_permission('launchpad.Admin')
    def reset(self):
        """Only enabled for build records that are resetable."""
        text = 'Reset Build'
        return Link('+reset', text, icon='edit',
                    enabled=self.context.can_be_reset)


class BuildView(LaunchpadView):
    """Auxiliary view class for IBuild"""
    __used_for__ = IBuild

    def reset_build(self):
        """Check user confirmation and perform the build record reset."""
        # dismiss if builder can't be reset and return a user warn.
        if not self.context.can_be_reset:
            return '<p>Build Record is already reset.</p>'

        # retrieve user confirmation
        action = self.request.form.get('RESET', None)
        # no action, return None to present the form again
        if not action:
            return None

        # invoke context method to reset the build record
        self.context.reset()
        return '<p>Build Record reset.</p>'
        

class BuildRecordsView(LaunchpadView):
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


