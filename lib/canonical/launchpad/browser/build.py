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

from canonical.launchpad.interfaces import IHasBuildRecords, IBuild

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, GetitemNavigation, ApplicationMenu,
    LaunchpadView, enabled_with_permission)
from canonical.launchpad.webapp.batching import BatchNavigator


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
    links = ['reset', 'rescore']

    @enabled_with_permission('launchpad.Admin')
    def reset(self):
        """Only enabled for build records that are resetable."""
        text = 'Reset Build'
        return Link('+reset', text, icon='edit',
                    enabled=self.context.can_be_reset)

    @enabled_with_permission('launchpad.Admin')
    def rescore(self):
        """Only enabled for build records that are not resetable."""
        text = 'Rescore Build'
        enabled = not self.context.can_be_reset
        return Link('+rescore', text, icon='edit',
                    enabled=enabled)


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

    def rescore_build(self):
        """Check user confirmation and perform the build record rescore."""
        # dismiss if builder can't be reset and return a user warn.
        if self.context.can_be_reset:
            return '<p>Build Record is already processed.</p>'

        # retrieve user score
        self.score = self.request.form.get('SCORE', '')
        self.manual = self.request.form.get('MANUAL', '')
        action = self.request.form.get('RESCORE', '')

        if not action:
            return None

        if not self.manual:
            self.context.buildqueue_record.autoScore()
            return '<p>Auto Scoring.</p>'

        # invoke context method to rescore the build record
        self.context.buildqueue_record.manualScore(int(self.score))
        return '<p>Build Record rescored to %s.</p>' % self.score


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
        self.text = self.request.get('build_text', '')

        if not self.text:
            self.text = None

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
        builds = self.context.getBuildRecords(state_map[self.state],
                                              name=self.text)
        self.batchnav = BatchNavigator(builds, self.request)


    def showBuilderInfo(self):
        """Control the presentation of builder information.

        It allows the callsite to control if they want a builder column
        in its result table or not. It's only ommited in builder-index page.
        """
        return True

    def searchName(self):
        """Control the presentation of search box."""
        return True
