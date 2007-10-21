# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for builds."""

__metaclass__ = type

__all__ = [
    'BuildFacets',
    'BuildNavigation',
    'BuildOverviewMenu',
    'BuildRecordsView',
    'BuildUrl',
    'BuildView',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    BuildStatus, IBuild, IBuildQueueSet, IHasBuildRecords, UnexpectedFormData)
from canonical.launchpad.webapp import (
    enabled_with_permission, ApplicationMenu, GetitemNavigation,
    Link, LaunchpadView, StandardLaunchpadFacets)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData


class BuildUrl:
    """Dynamic URL declaration for IBuild.

    When dealing with distribution builds ('trusted') we want to present them
    under IDistributionSourcePackageRelease url:

       /ubuntu/+source/foo/1.0/+build/1234

    On the other hand, PPA builds ('untrusted') will be presented under the PPA
    page:

       /~cprov/+archive/+build/1235
    """
    implements(ICanonicalUrlData)
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def inside(self):
        if self.context.is_trusted:
            return self.context.distributionsourcepackagerelease
        return self.context.archive

    @property
    def path(self):
        return u"+build/%d" % self.context.id


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
    links = ['retry', 'rescore']

    @enabled_with_permission('launchpad.Edit')
    def retry(self):
        """Only enabled for build records that are active."""
        text = 'Retry build'
        return Link('+retry', text, icon='edit',
                    enabled=self.context.can_be_retried)

    @enabled_with_permission('launchpad.Admin')
    def rescore(self):
        """Only enabled for pending build records."""
        text = 'Rescore build'
        return Link('+rescore', text, icon='edit',
                    enabled=self.context.can_be_rescored)


class BuildView(LaunchpadView):
    """Auxiliary view class for IBuild"""
    __used_for__ = IBuild

    def retry_build(self):
        """Check user confirmation and perform the build record retry."""
        if not self.context.can_be_retried:
            self.error = 'Build can not be retried'
            return

        # retrieve user confirmation
        action = self.request.form.get('RETRY', None)
        # no action, return None to present the form again
        if not action:
            return None

        # invoke context method to retry the build record
        self.context.retry()
        return 'Build record active'

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

    @property
    def user_can_retry_build(self):
        """Return True if the user is permitted to Retry Build.

        The build must be re-tryable.
        """
        return (check_permission('launchpad.Edit', self.context)
            and self.context.can_be_retried)


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
    DistroSeries, DistroArchSeries and SourcePackage view classes.
    """
    __used_for__ = IHasBuildRecords

    def setupBuildList(self):
        """Setup a batched build records list.

        Return None, so use tal:condition="not: view/setupBuildList" to
        invoke it in template.
        """
        # recover selected build state
        state_tag = self.request.get('build_state', '')
        text_filter = self.request.get('build_text', '')

        if text_filter:
            self.text = text_filter
        else:
            self.text = None

        # build self.state & self.available_states structures
        self._setupMappedStates(state_tag)

        # request context build records according the selected state
        builds = self.context.getBuildRecords(
            build_state=self.state, name=self.text)
        self.batchnav = BatchNavigator(builds, self.request)
        # We perform this extra step because we don't what to issue one
        # extra query to retrieve the BuildQueue for each Build (batch item)
        # A more elegant approach should be extending Batching class and
        # integrating the fix into it. However the current solution is
        # simpler and shorter, producing the same result. cprov 20060810
        self.complete_builds = setupCompleteBuilds(
            self.batchnav.currentBatch())

    def _setupMappedStates(self, tag):
        """Build self.state and self.availableStates structures.

        self.state is the corresponding dbschema for requested state_tag

        self.available_states is a dictionary containing the options with
        suitables attributes (name, value, selected) to easily fill an HTML
        <select> section.

        Raise UnexpectedFormData if no corresponding state for passed 'tag'
        was found.
        """
        # default states map
        state_map = {
            'built': BuildStatus.FULLYBUILT,
            'failed': BuildStatus.FAILEDTOBUILD,
            'depwait': BuildStatus.MANUALDEPWAIT,
            'chrootwait': BuildStatus.CHROOTWAIT,
            'superseded': BuildStatus.SUPERSEDED,
            'uploadfail': BuildStatus.FAILEDTOUPLOAD,
            'all': None,
            }
        # include pristine (not yet assigned to a builder) builds
        # if requested.
        if self.showBuilderInfo():
            extra_state_map = {
                'building': BuildStatus.BUILDING,
                'pending': BuildStatus.NEEDSBUILD,
                }
            state_map.update(**extra_state_map)

        # lookup for the correspondent state or fallback to the default
        # one if tag is empty string.
        if tag:
            try:
                self.state = state_map[tag]
            except KeyError:
                raise UnexpectedFormData(
                    'No suitable state found for value "%s"' % tag)
        else:
            self.state = self.defaultBuildState()

        # build a dictionary with organized information for rendering
        # the HTML <select> section.
        self.available_states = []
        for tag, state in state_map.items():
            if state:
                name = state.title.strip()
            else:
                name = 'All states'

            if state == self.state:
                selected = True
            else:
                selected = False

            self.available_states.append(
                dict(name=name, value=tag, selected=selected)
                )

    def defaultBuildState(self):
        """Return the build state to be present as default.

        It allows the callsites to control which default status they
        want to present when the page is first loaded.
        """
        return BuildStatus.BUILDING

    def showBuilderInfo(self):
        """Control the presentation of builder information.

        It allows the callsite to control if they want a builder column
        in its result table or not. It's only omitted in builder-index page.
        """
        return True

    def searchName(self):
        """Control the presentation of search box."""
        return True

    @property
    def form_submitted(self):
        return "build_text" in self.request

    @property
    def no_results(self):
        return self.form_submitted and not self.complete_builds

