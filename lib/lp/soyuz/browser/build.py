# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for builds."""

__metaclass__ = type

__all__ = [
    'BuildBreadcrumb',
    'BuildCancelView',
    'BuildContextMenu',
    'BuildNavigation',
    'BuildNavigationMixin',
    'BuildRecordsView',
    'BuildRescoringView',
    'BuildUrl',
    'BuildView',
    'DistributionBuildRecordsView',
    ]

from lazr.batchnavigator import ListRangeFactory
from lazr.delegates import delegates
from lazr.restful.utils import safe_hasattr
from zope.component import getUtility
from zope.interface import (
    implements,
    Interface,
    )

from canonical.launchpad import _
from canonical.launchpad.browser.librarian import (
    FileNavigationMixin,
    ProxiedLibraryFileAlias,
    )
from canonical.launchpad.webapp import (
    canonical_url,
    ContextMenu,
    enabled_with_permission,
    GetitemNavigation,
    LaunchpadView,
    Link,
    StandardLaunchpadFacets,
    stepthrough,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import (
    BatchNavigator,
    StormRangeFactory,
    )
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from lp.app.browser.launchpadform import (
    action,
    LaunchpadFormView,
    )
from lp.app.errors import (
    NotFoundError,
    UnexpectedFormData,
    )
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSet
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildSource)
from lp.services.job.interfaces.job import JobStatus
from lp.services.propertycache import cachedproperty
from lp.soyuz.enums import PackageUploadStatus
from lp.soyuz.interfaces.binarypackagebuild import (
    IBinaryPackageBuild,
    IBinaryPackageBuildSet,
    IBuildRescoreForm,
    )


class BuildUrl:
    """Dynamic URL declaration for IBinaryPackageBuild.

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
    usedfor = IBinaryPackageBuild


class BuildNavigationMixin:
    """Provide a simple way to traverse to builds."""

    @stepthrough('+build')
    def traverse_build(self, name):
        try:
            build_id = int(name)
        except ValueError:
            return None
        try:
            return getUtility(IBinaryPackageBuildSet).getByID(build_id)
        except NotFoundError:
            return None

    @stepthrough('+recipebuild')
    def traverse_recipebuild(self, name):
        try:
            build_id = int(name)
        except ValueError:
            return None
        try:
            return getUtility(ISourcePackageRecipeBuildSource).getByID(
                build_id)
        except NotFoundError:
            return None

    @stepthrough('+buildjob')
    def traverse_buildjob(self, name):
        try:
            job_id = int(name)
        except ValueError:
            return None
        try:
            build_job = getUtility(IBuildFarmJobSet).getByID(job_id)
            return self.redirectSubTree(
                canonical_url(build_job.getSpecificJob()))
        except NotFoundError:
            return None


class BuildFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an
    IBinaryPackageBuild."""
    enable_only = ['overview']

    usedfor = IBinaryPackageBuild


class BuildContextMenu(ContextMenu):
    """Overview menu for build records """
    usedfor = IBinaryPackageBuild

    links = ['ppa', 'records', 'retry', 'rescore', 'cancel']

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
        text = 'Retry this build'
        return Link(
            '+retry', text, icon='retry',
            enabled=self.context.can_be_retried)

    @enabled_with_permission('launchpad.Admin')
    def rescore(self):
        """Only enabled for pending build records."""
        text = 'Rescore build'
        return Link(
            '+rescore', text, icon='edit',
            enabled=self.context.can_be_rescored)

    @enabled_with_permission('launchpad.Edit')
    def cancel(self):
        """Only enabled for pending/active virtual builds."""
        text = 'Cancel build'
        return Link(
            '+cancel', text, icon='edit',
            enabled=self.context.can_be_cancelled)


class BuildBreadcrumb(Breadcrumb):
    """Builds a breadcrumb for an `IBinaryPackageBuild`."""

    @property
    def text(self):
        # If this is a PPA or copy archive build, include the source
        # name and version. But for distro archives there are already
        # breadcrumbs for both, so we omit them.
        if self.context.archive.is_ppa or self.context.archive.is_copy:
            return '%s build of %s %s' % (
                self.context.arch_tag,
                self.context.source_package_release.sourcepackagename.name,
                self.context.source_package_release.version)
        else:
            return '%s build' % self.context.arch_tag


class BuildView(LaunchpadView):
    """Auxiliary view class for IBinaryPackageBuild"""

    @property
    def label(self):
        return self.context.title

    @property
    def user_can_retry_build(self):
        """Return True if the user is permitted to Retry Build.

        The build must be re-tryable.
        """
        return (check_permission('launchpad.Edit', self.context)
            and self.context.can_be_retried)

    @cachedproperty
    def package_upload(self):
        """Return the corresponding package upload for this build."""
        return self.context.package_upload

    @property
    def binarypackagetitles(self):
        """List the titles of this build's `BinaryPackageRelease`s.

        :return: A list of title strings.
        """
        return [
            binarypackagerelease.title
            for binarypackagerelease, binarypackagename
                in self.context.getBinaryPackageNamesForDisplay()]

    @cachedproperty
    def has_published_binaries(self):
        """Whether or not binaries were already published for this build."""
        # Binaries imported by gina (missing `PackageUpload` record)
        # are always published.
        imported_binaries = (
            self.package_upload is None and
            bool(self.context.binarypackages))
        # Binaries uploaded from the buildds are published when the
        # corresponding `PackageUpload` status is DONE.
        uploaded_binaries = (
            self.package_upload is not None and
            self.package_upload.status == PackageUploadStatus.DONE)

        if imported_binaries or uploaded_binaries:
            return True

        return False

    @property
    def changesfile(self):
        """Return a `ProxiedLibraryFileAlias` for the Build changesfile."""
        changesfile = self.context.upload_changesfile
        if changesfile is None:
            return None

        return ProxiedLibraryFileAlias(changesfile, self.context)

    @cachedproperty
    def is_ppa(self):
        return self.context.archive.is_ppa

    @cachedproperty
    def buildqueue(self):
        return self.context.buildqueue_record

    @cachedproperty
    def component(self):
        return self.context.current_component

    @cachedproperty
    def files(self):
        """Return `LibraryFileAlias`es for files produced by this build."""
        if not self.context.was_built:
            return None

        return [
            ProxiedLibraryFileAlias(alias, self.context)
            for bpr, bpf, alias, content
                in self.context.getBinaryFilesForDisplay()
                if not alias.deleted]

    @property
    def dispatch_time_estimate_available(self):
        """True if a dispatch time estimate is available for this build.

        The build must be in state NEEDSBUILD and the associated job must be
        in state WAITING.
        """
        return (
            self.context.status == BuildStatus.NEEDSBUILD and
            self.context.buildqueue_record.job.status == JobStatus.WAITING)

    @cachedproperty
    def eta(self):
        """The datetime when the build job is estimated to complete.

        This is the BuildQueue.estimated_duration plus the
        Job.date_started or BuildQueue.getEstimatedJobStartTime.
        """
        if self.context.buildqueue_record is None:
            return None
        queue_record = self.context.buildqueue_record
        if queue_record.job.status == JobStatus.WAITING:
            start_time = queue_record.getEstimatedJobStartTime()
            if start_time is None:
                return None
        else:
            start_time = queue_record.job.date_started
        duration = queue_record.estimated_duration
        return start_time + duration

    @cachedproperty
    def date(self):
        """The date when the build completed or is estimated to complete."""
        if self.estimate:
            return self.eta
        return self.context.date_finished

    @cachedproperty
    def estimate(self):
        """If true, the date value is an estimate."""
        if self.context.date_finished is not None:
            return False
        return self.eta is not None


class BuildRetryView(BuildView):
    """View class for retrying `IBinaryPackageBuild`s"""

    @property
    def label(self):
        return 'Retry %s' % self.context.title

    def retry_build(self):
        """Check user confirmation and perform the build record retry."""
        if not self.context.can_be_retried:
            self.request.response.addErrorNotification(
                'Build can not be retried')
        else:
            action = self.request.form.get('RETRY', None)
            # No action, return None to present the form again.
            if action is None:
                return

            # Invoke context method to retry the build record.
            self.context.retry()
            self.request.response.addInfoNotification('Build retried')

        self.request.response.redirect(canonical_url(self.context))


class BuildRescoringView(LaunchpadFormView):
    """View class for build rescoring."""

    schema = IBuildRescoreForm

    @property
    def label(self):
        return 'Rescore %s' % self.context.title

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
        self.context.rescore(score)
        self.request.response.addNotification(
            "Build rescored to %s." % score)


class BuildCancelView(LaunchpadFormView):
    """View class for build cancellation."""

    class schema(Interface):
        """Schema for cancelling a build."""

    page_title = label = "Cancel build"

    @property
    def cancel_url(self):
        return canonical_url(self.context)
    next_url = cancel_url

    @action("Cancel build", name="cancel")
    def request_action(self, action, data):
        """Cancel the build."""
        self.context.cancel()
        if self.context.status == BuildStatus.CANCELLING:
            self.request.response.addNotification(
                "Build cancellation in progress")
        elif self.context.status == BuildStatus.CANCELLED:
            self.request.response.addNotification("Build cancelled")
        else:
            self.request.response.addNotification("Unable to cancel build")


class CompleteBuild:
    """Super object to store related IBinaryPackageBuild & IBuildQueue."""
    delegates(IBinaryPackageBuild)

    def __init__(self, build, buildqueue_record):
        self.context = build
        self._buildqueue_record = buildqueue_record

    def buildqueue_record(self):
        return self._buildqueue_record


def setupCompleteBuilds(batch):
    """Pre-populate new object with buildqueue items.

    Single queries, using list() statement to force fetch
    of the results in python domain.

    Receive a sequence of builds, for instance, a batch.

    Return a list of built CompleteBuild instances, or empty
    list if no builds were contained in the received batch.
    """
    builds = [build.getSpecificJob() for build in batch]
    if not builds:
        return []

    # This pre-population of queue entries is only implemented for
    # IBinaryPackageBuilds.
    prefetched_data = dict()
    build_ids = [
        build.id for build in builds if IBinaryPackageBuild.providedBy(build)]
    results = getUtility(IBinaryPackageBuildSet).getQueueEntriesForBuildIDs(
        build_ids)
    for (buildqueue, _builder, build_job) in results:
        # Get the build's id, 'buildqueue', 'sourcepackagerelease' and
        # 'buildlog' (from the result set) respectively.
        prefetched_data[build_job.build.id] = buildqueue

    complete_builds = []
    for build in builds:
        if IBinaryPackageBuild.providedBy(build):
            buildqueue = prefetched_data.get(build.id)
            complete_builds.append(CompleteBuild(build, buildqueue))
        else:
            complete_builds.append(build)
    return complete_builds


class BuildRecordsView(LaunchpadView):
    """Base class used to present objects that contains build records.

    It retrieves the UI build_state selector action and setup a proper
    batched list with the requested results. See further UI details in
    template/builds-list.pt and callsite details in Builder, Distribution,
    DistroSeries, DistroArchSeries and SourcePackage view classes.
    """

    page_title = 'Builds'

    # Currenly most build records views are interested in binaries
    # only, but subclasses can set this if desired.
    binary_only = True

    range_factory = ListRangeFactory

    @property
    def label(self):
        return 'Builds for %s' % self.context.displayname

    def setupBuildList(self):
        """Setup a batched build records list.

        Return None, so use tal:condition="not: view/setupBuildList" to
        invoke it in template.
        """
        # recover selected build state
        state_tag = self.request.get('build_state', '')
        self.text = self.request.get('build_text', None)

        if self.text == '':
            self.text = None

        # build self.state & self.available_states structures
        self._setupMappedStates(state_tag)

        # By default, we use the binary_only class attribute, but we
        # ensure it is true if we are passed an arch tag or a name.
        binary_only = self.binary_only
        if self.text is not None or self.arch_tag is not None:
            binary_only = True

        # request context build records according the selected state
        builds = self.context.getBuildRecords(
            build_state=self.state, name=self.text, arch_tag=self.arch_tag,
            user=self.user, binary_only=binary_only)
        self.batchnav = BatchNavigator(
            builds, self.request, range_factory=self.range_factory(builds))
        # We perform this extra step because we don't what to issue one
        # extra query to retrieve the BuildQueue for each Build (batch item)
        # A more elegant approach should be extending Batching class and
        # integrating the fix into it. However the current solution is
        # simpler and shorter, producing the same result. cprov 20060810
        self.complete_builds = setupCompleteBuilds(
            self.batchnav.currentBatch())

    @property
    def arch_tag(self):
        """Return the architecture tag from the request."""
        arch_tag = self.request.get('arch_tag', None)
        if arch_tag == '' or arch_tag == 'all':
            return None
        else:
            return arch_tag

    @cachedproperty
    def architecture_options(self):
        """Return the architecture options for the context."""
        # Guard against contexts that cannot tell us the available
        # distroarchseries.
        if safe_hasattr(self.context, 'architectures') is False:
            return []

        # Grab all the architecture tags for the context.
        arch_tags = [
            arch.architecturetag for arch in self.context.architectures]

        # We cannot assume that the arch_tags will be distinct, so
        # create a distinct and sorted list:
        arch_tags = sorted(set(arch_tags))

        # Create the initial 'all architectures' option.
        if self.arch_tag is None:
            selected = 'selected'
        else:
            selected = None
        options = [
            dict(name='All architectures', value='all', selected=selected)]

        # Create the options for the select box, ensuring to mark
        # the currently selected one.
        for arch_tag in arch_tags:
            if arch_tag == self.arch_tag:
                selected = 'selected'
            else:
                selected = None

            options.append(
                dict(name=arch_tag, value=arch_tag, selected=selected))

        return options

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
                dict(name=name, value=tag, selected=selected))

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
    def show_arch_selector(self):
        """Control whether the architecture selector is presented.

        This allows the callsite to control if they want the architecture
        selector presented in the UI.
        """
        return False

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


class DistributionBuildRecordsView(BuildRecordsView):
    """See BuildRecordsView."""

    # SQL Queries generated by the default ListRangeFactory time out
    # for some views, like +builds?build_state=all. StormRangeFactory
    # is more efficient.
    range_factory = StormRangeFactory
