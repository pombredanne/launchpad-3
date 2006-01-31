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

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

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
    """Base class used to present objects that contains build records.

    It retrieves the UI build_state selector action and setup a proper
    batched list with the requested results. See further UI details in
    template/builds-list.pt and callsite details in Builder, Distribution,
    DistroRelease, DistroArchRelease and SourcePackage view classes.
    """
    __used_for__ = IHasBuildRecords

    def setupBuildList(self):
        """Setup a batched build records list.

        Return None, so use tal:condition="not: view/setupBuildList" to
        invoke it in template.
        """
        # recover selected build state
        self.state = self.request.get('build_state', '')

        # map state text tag back to dbschema
        state_map = {
            '': None,
            'pending': BuildStatus.NEEDSBUILD,
            'built': BuildStatus.FULLYBUILT,
            'failed': BuildStatus.FAILEDTOBUILD,
            'depwait': BuildStatus.MANUALDEPWAIT,
            'chrootwait': BuildStatus.CHROOTWAIT,
            }

        # request context build records according the selected state
        builds = self.context.getBuildRecords(state_map[self.state])

        # recover batch page
        start = int(self.request.get('batch_start', 0))

        # setup the batched list to present
        self.batch = Batch(builds, start)
        self.batchnav = BatchNavigator(self.batch, self.request)


    def showBuilderInfo(self):
        """Control the presentation o builder information.

        It allows the callsite to control if they want a builder column
        in its result table or not. It's only ommited in builder-index page.
        """
        return True
