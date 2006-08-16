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

from zope.component import getUtility

from canonical.lp.dbschema import BuildStatus

from canonical.launchpad.interfaces import (
    IHasBuildRecords, IBuild, IBuildQueueSet, UnexpectedFormData)

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
        """Only enabled for pending build records."""
        text = 'Rescore Build'
        return Link('+rescore', text, icon='edit',
                    enabled=self.context.can_be_rescored)


class BuildView(LaunchpadView):
    """Auxiliary view class for IBuild"""
    __used_for__ = IBuild

    def reset_build(self):
        """Check user confirmation and perform the build record reset."""
        if not self.context.can_be_reset:
            self.error = 'Build can not be reset'
            return

        # retrieve user confirmation
        action = self.request.form.get('RESET', None)
        # no action, return None to present the form again
        if not action:
            return None

        # invoke context method to reset the build record
        self.context.reset()
        return 'Build Record reset'

    def rescore_build(self):
        """Check user confirmation and perform the build record rescore."""
        if not self.context.can_be_rescored:
            self.error = 'Build can not be rescored'
            return

        # retrieve user score
        self.score = self.request.form.get('SCORE', '')
        action = self.request.form.get('RESCORE', '')

        if not action:
            return

        try:
            score = int(self.score)
        except ValueError:
            self.error = 'priority must be an integer not "%s"' % self.score
            return

        # invoke context method to rescore the build record
        self.context.buildqueue_record.manualScore(score)
        return 'Build Record rescored to %s' % self.score


class CompleteBuild:
    """Super object to store related IBuild & IBuildQueue."""
    def __init__(self, build, buildqueue_record):
        self.build = build
        self.buildqueue_record = buildqueue_record


def setupCompleteBuilds(batch):
    """Pre-populate new object with buildqueue items.

    Single queries, using list() statement to force fetch
    of the results in python domain.

    Receive a sequence of builds, for instance, a batch.

    Return a list of built CompleteBuild instances, or empty
    list if no builds were contained in the received batch.
    """
    builds = list(batch)

    if not builds:
        return []

    buildqueue_records = {}

    build_ids = [build.id for build in builds]
    for buildqueue in getUtility(IBuildQueueSet).fetchByBuildIds(build_ids):
        buildqueue_records[buildqueue.build.id] = buildqueue

    complete_builds = []
    for build in builds:
        proposed_buildqueue = buildqueue_records.get(build.id, None)
        complete_builds.append(
            CompleteBuild(build, proposed_buildqueue))

    return complete_builds


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
            'all': None,
            'built': BuildStatus.FULLYBUILT,
            'building': BuildStatus.BUILDING,
            'pending': BuildStatus.NEEDSBUILD,
            'failed': BuildStatus.FAILEDTOBUILD,
            'depwait': BuildStatus.MANUALDEPWAIT,
            'chrootwait': BuildStatus.CHROOTWAIT,
            'superseded': BuildStatus.SUPERSEDED,
            }
        try:
            mapped_state = state_map[self.state]
        except KeyError:
            raise UnexpectedFormData(
                'No suitable state found for value "%s"' % self.state
                )
        # request context build records according the selected state
        builds = self.context.getBuildRecords(mapped_state, name=self.text)
        self.batchnav = BatchNavigator(builds, self.request)
        # We perform this extra step because we don't what to issue one
        # extra query to retrieve the BuildQueue for each Build (batch item)
        # A more elegant approach should be extending Batching class and
        # integrating the fix into it. However the current solution is
        # simpler and shorter, producing the same result. cprov 20060810
        self.complete_builds = setupCompleteBuilds(
            self.batchnav.currentBatch())

    def showBuilderInfo(self):
        """Control the presentation of builder information.

        It allows the callsite to control if they want a builder column
        in its result table or not. It's only omitted in builder-index page.
        """
        return True

    def searchName(self):
        """Control the presentation of search box."""
        return True
