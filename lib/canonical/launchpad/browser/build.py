# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for builds."""

__metaclass__ = type

__all__ = [
    'BuildContextMenu',
    'BuildNavigation',
    'BuildRecordsView',
    'BuildRescoringView',
    'BuildUrl',
    'BuildView',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad import _
from canonical.launchpad.browser.librarian import FileNavigationMixin
from canonical.launchpad.interfaces.build import (
    BuildStatus, IBuild, IBuildRescoreForm, IHasBuildRecords)
from canonical.launchpad.interfaces.buildqueue import IBuildQueueSet
from canonical.launchpad.interfaces.launchpad import UnexpectedFormData
from canonical.launchpad.interfaces.package import PackageUploadStatus
from canonical.launchpad.webapp import (
    action, canonical_url, enabled_with_permission, ContextMenu,
    GetitemNavigation, Link, LaunchpadFormView, LaunchpadView,
    StandardLaunchpadFacets)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData


class BuildUrl:
    """Dynamic URL declaration for IBuild.

    When dealing with distribution builds we want to present them
    under IDistributionSourcePackageRelease url:

       /ubuntu/+source/foo/1.0/+build/1234

    On the other hand, PPA builds will be presented under the PPA page:

       /~cprov/+archive/+build/1235

    Copy archives will be presented under the archives page:
       /ubuntu/+archive/my-special-archive/+build/1234
    """
    implements(ICanonicalUrlData)
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def inside(self):
        if self.context.archive.is_ppa or self.context.archive.is_copy:
            return self.context.archive
        else:
            return self.context.distributionsourcepackagerelease

    @property
    def path(self):
        return u"+build/%d" % self.context.id


class BuildNavigation(GetitemNavigation, FileNavigationMixin):
    usedfor = IBuild


class BuildFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IBuild."""
    enable_only = ['overview']

    usedfor = IBuild


class BuildContextMenu(ContextMenu):
    """Overview menu for build records """
    usedfor = IBuild

    links = ['ppa', 'records', 'retry', 'rescore']

    @property
    def is_ppa_build(self):
        """Some links are only displayed on PPA."""
        return self.context.archive.is_ppa

    def ppa(self):
        return Link(
            canonical_url(self.context.archive), text='View PPA',
            enabled=self.is_ppa_build)

    def records(self):
        return Link(
            canonical_url(self.context.archive, view_name='+builds'),
            text='View build records', enabled=self.is_ppa_build)

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

    @property
    def user_can_retry_build(self):
        """Return True if the user is permitted to Retry Build.

        The build must be re-tryable.
        """
        return (check_permission('launchpad.Edit', self.context)
            and self.context.can_be_retried)

    @property
    def has_done_upload(self):
        """Return True if this build's package upload is done."""
        package_upload = self.context.package_upload

        if package_upload is None:
            return False

        if package_upload.status == PackageUploadStatus.DONE:
            return True

        return False

class BuildRescoringView(LaunchpadFormView):
    """View class for build rescoring."""

    schema = IBuildRescoreForm

    def initialize(self):
        """See `ILaunchpadFormView`.

        It redirects attempts to rescore builds that cannot be rescored
        to the build context page, so the current page-scrapping libraries
        won't cause any oops.

        It also sets next_url and cancel_url to the build context page, so
        any action will send the user back to the context build page.
        """
        build_url = canonical_url(self.context)
        self.next_url = self.cancel_url = build_url

        if not self.context.can_be_rescored:
            self.request.response.redirect(build_url)

        LaunchpadFormView.initialize(self)

    @action(_("Rescore"), name="rescore")
    def action_rescore(self, action, data):
        """Set the given score value."""
        score = data.get('priority')
        self.context.buildqueue_record.manualScore(score)
        self.request.response.addNotification(
            "Build rescored to %s." % score)


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
            build_state=self.state, name=self.text, user=self.user)
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
        # Default states map.
        state_map = {
            'built': BuildStatus.FULLYBUILT,
            'failed': BuildStatus.FAILEDTOBUILD,
            'depwait': BuildStatus.MANUALDEPWAIT,
            'chrootwait': BuildStatus.CHROOTWAIT,
            'superseded': BuildStatus.SUPERSEDED,
            'uploadfail': BuildStatus.FAILEDTOUPLOAD,
            'all': None,
            }
        # Include pristine (not yet assigned to a builder) builds,
        # if requested.
        if self.show_builder_info:
            extra_state_map = {
                'building': BuildStatus.BUILDING,
                'pending': BuildStatus.NEEDSBUILD,
                }
            state_map.update(**extra_state_map)

        # Lookup for the correspondent state or fallback to the default
        # one if tag is empty string.
        if tag:
            try:
                self.state = state_map[tag]
            except (KeyError, TypeError):
                raise UnexpectedFormData(
                    'No suitable state found for value "%s"' % tag)
        else:
            self.state = self.default_build_state

        # Build a dictionary with organized information for rendering
        # the HTML <select> section.
        self.available_states = []
        for tag, state in state_map.items():
            if state:
                name = state.title.strip()
            else:
                name = 'All states'

            if state == self.state:
                selected = 'selected'
            else:
                selected = None

            self.available_states.append(
                dict(name=name, value=tag, selected=selected)
                )

    @property
    def default_build_state(self):
        """The build state to be present as default.

        It allows the callsites to control which default status they
        want to present when the page is first loaded.
        """
        return BuildStatus.BUILDING

    @property
    def show_builder_info(self):
        """Control the presentation of builder information.

        It allows the callsite to control if they want a builder column
        in its result table or not. It's only omitted in builder-index page.
        """
        return True

    @property
    def search_name(self):
        """Control the presentation of search box."""
        return True

    @property
    def form_submitted(self):
        return "build_state" in self.request.form

    @property
    def no_results(self):
        return self.form_submitted and not self.complete_builds

