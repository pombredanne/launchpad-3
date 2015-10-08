# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap views."""

__metaclass__ = type
__all__ = [
    'SnapAddView',
    'SnapContextMenu',
    'SnapDeleteView',
    'SnapEditView',
    'SnapNavigation',
    'SnapNavigationMenu',
    'SnapRequestBuildsView',
    'SnapView',
    ]

from lazr.restful.fields import Reference
from lazr.restful.interface import (
    copy_field,
    use_template,
    )
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import (
    Choice,
    List,
    )

from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    render_radio_widget_part,
    )
from lp.app.browser.lazrjs import InlinePersonEditPickerWidget
from lp.app.browser.tales import format_link
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.widgets.itemswidgets import (
    LabeledMultiCheckBoxWidget,
    LaunchpadRadioWidget,
    )
from lp.code.browser.widgets.gitref import GitRefWidget
from lp.code.interfaces.gitref import IGitRef
from lp.registry.enums import VCSType
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features import getFeatureFlag
from lp.services.helpers import english_list
from lp.services.webapp import (
    canonical_url,
    ContextMenu,
    enabled_with_permission,
    LaunchpadView,
    Link,
    Navigation,
    NavigationMenu,
    stepthrough,
    structured,
    )
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.breadcrumb import (
    Breadcrumb,
    NameBreadcrumb,
    )
from lp.snappy.browser.widgets.snaparchive import SnapArchiveWidget
from lp.snappy.interfaces.snap import (
    ISnap,
    ISnapSet,
    NoSuchSnap,
    SNAP_FEATURE_FLAG,
    SnapBuildAlreadyPending,
    SnapFeatureDisabled,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuildSet
from lp.soyuz.browser.archive import EnableProcessorsMixin
from lp.soyuz.browser.build import get_build_by_id_str
from lp.soyuz.interfaces.archive import IArchive


class SnapNavigation(Navigation):
    usedfor = ISnap

    @stepthrough('+build')
    def traverse_build(self, name):
        build = get_build_by_id_str(ISnapBuildSet, name)
        if build is None or build.snap != self.context:
            return None
        return build


class SnapBreadcrumb(NameBreadcrumb):

    @property
    def inside(self):
        return Breadcrumb(
            self.context.owner,
            url=canonical_url(self.context.owner, view_name="+snaps"),
            text="Snap packages", inside=self.context.owner)


class SnapNavigationMenu(NavigationMenu):
    """Navigation menu for snap packages."""

    usedfor = ISnap

    facet = 'overview'

    links = ('edit', 'delete', 'admin')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        return Link('+admin', 'Administer snap package', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        return Link('+edit', 'Edit snap package', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def delete(self):
        return Link('+delete', 'Delete snap package', icon='trash-icon')


class SnapContextMenu(ContextMenu):
    """Context menu for snap packages."""

    usedfor = ISnap

    facet = 'overview'

    links = ('request_builds',)

    @enabled_with_permission('launchpad.Edit')
    def request_builds(self):
        return Link('+request-builds', 'Request builds', icon='add')


class SnapView(LaunchpadView):
    """Default view of a Snap."""

    @property
    def builds(self):
        return builds_for_snap(self.context)

    @property
    def person_picker(self):
        field = copy_field(
            ISnap['owner'],
            vocabularyName='UserTeamsParticipationPlusSelfSimpleDisplay')
        return InlinePersonEditPickerWidget(
            self.context, field, format_link(self.context.owner),
            header='Change owner', step_title='Select a new owner')


def builds_for_snap(snap):
    """A list of interesting builds.

    All pending builds are shown, as well as 1-10 recent builds.  Recent
    builds are ordered by date finished (if completed) or date_started (if
    date finished is not set due to an error building or other circumstance
    which resulted in the build not being completed).  This allows started
    but unfinished builds to show up in the view but be discarded as more
    recent builds become available.

    Builds that the user does not have permission to see are excluded.
    """
    builds = [
        build for build in snap.pending_builds
        if check_permission('launchpad.View', build)]
    for build in snap.completed_builds:
        if not check_permission('launchpad.View', build):
            continue
        builds.append(build)
        if len(builds) >= 10:
            break
    return builds


def new_builds_notification_text(builds, already_pending=None):
    nr_builds = len(builds)
    if not nr_builds:
        builds_text = "All requested builds are already queued."
    elif nr_builds == 1:
        builds_text = "1 new build has been queued."
    else:
        builds_text = "%d new builds have been queued." % nr_builds
    if nr_builds and already_pending:
        return structured("<p>%s</p><p>%s</p>", builds_text, already_pending)
    else:
        return builds_text


class SnapRequestBuildsView(LaunchpadFormView):
    """A view for requesting builds of a snap package."""

    @property
    def label(self):
        return 'Request builds for %s' % self.context.name

    page_title = 'Request builds'

    class schema(Interface):
        """Schema for requesting a build."""

        archive = Reference(IArchive, title=u'Source archive', required=True)
        distro_arch_series = List(
            Choice(vocabulary='SnapDistroArchSeries'),
            title=u'Architectures', required=True)
        pocket = Choice(
            title=u'Pocket', vocabulary=PackagePublishingPocket, required=True)

    custom_widget('archive', SnapArchiveWidget)
    custom_widget('distro_arch_series', LabeledMultiCheckBoxWidget)

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def initial_values(self):
        """See `LaunchpadFormView`."""
        return {
            'archive': self.context.distro_series.main_archive,
            'distro_arch_series': self.context.getAllowedArchitectures(),
            'pocket': PackagePublishingPocket.RELEASE,
            }

    def validate(self, data):
        """See `LaunchpadFormView`."""
        arches = data.get('distro_arch_series', [])
        if not arches:
            self.setFieldError(
                'distro_arch_series',
                "You need to select at least one architecture.")

    def requestBuild(self, data):
        """User action for requesting a number of builds.

        We raise exceptions for most errors, but if there's already a
        pending build for a particular architecture, we simply record that
        so that other builds can be queued and a message displayed to the
        caller.
        """
        informational = {}
        builds = []
        already_pending = []
        for arch in data['distro_arch_series']:
            try:
                build = self.context.requestBuild(
                    self.user, data['archive'], arch, data['pocket'])
                builds.append(build)
            except SnapBuildAlreadyPending:
                already_pending.append(arch)
        if already_pending:
            informational['already_pending'] = (
                "An identical build is already pending for %s." %
                english_list(arch.architecturetag for arch in already_pending))
        return builds, informational

    @action('Request builds', name='request')
    def request_action(self, action, data):
        builds, informational = self.requestBuild(data)
        self.next_url = self.cancel_url
        already_pending = informational.get('already_pending')
        notification_text = new_builds_notification_text(
            builds, already_pending)
        self.request.response.addNotification(notification_text)


class ISnapEditSchema(Interface):
    """Schema for adding or editing a snap package."""

    use_template(ISnap, include=[
        'owner',
        'name',
        'require_virtualized',
        ])
    distro_series = Choice(
        vocabulary='BuildableDistroSeries', title=u'Distribution series')
    vcs = Choice(vocabulary=VCSType, required=True, title=u'VCS')

    # Each of these is only required if vcs has an appropriate value.  Later
    # validation takes care of adjusting the required attribute.
    branch = copy_field(ISnap['branch'], required=True)
    git_ref = copy_field(ISnap['git_ref'], required=True)


class SnapAddView(LaunchpadFormView):
    """View for creating snap packages."""

    page_title = label = 'Create a new snap package'

    schema = ISnapEditSchema
    field_names = ['owner', 'name', 'distro_series']
    custom_widget('distro_series', LaunchpadRadioWidget)

    def initialize(self):
        """See `LaunchpadView`."""
        if not getFeatureFlag(SNAP_FEATURE_FLAG):
            raise SnapFeatureDisabled
        super(SnapAddView, self).initialize()

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def initial_values(self):
        # XXX cjwatson 2015-09-18: Hack to ensure that we don't end up
        # accidentally selecting ubuntu-rtm/14.09 or similar.
        # ubuntu.currentseries will always be in BuildableDistroSeries.
        series = getUtility(ILaunchpadCelebrities).ubuntu.currentseries
        return {
            'owner': self.user,
            'distro_series': series,
            }

    @action('Create snap package', name='create')
    def request_action(self, action, data):
        if IGitRef.providedBy(self.context):
            kwargs = {'git_ref': self.context}
        else:
            kwargs = {'branch': self.context}
        snap = getUtility(ISnapSet).new(
            self.user, data['owner'], data['distro_series'], data['name'],
            **kwargs)
        self.next_url = canonical_url(snap)

    def validate(self, data):
        super(SnapAddView, self).validate(data)
        owner = data.get('owner', None)
        name = data.get('name', None)
        if owner and name:
            if getUtility(ISnapSet).exists(owner, name):
                self.setFieldError(
                    'name',
                    'There is already a snap package owned by %s with this '
                    'name.' % owner.displayname)


class BaseSnapEditView(LaunchpadEditFormView):

    schema = ISnapEditSchema

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        super(BaseSnapEditView, self).setUpWidgets()
        widget = self.widgets.get('vcs')
        if widget is not None:
            current_value = widget._getFormValue()
            self.vcs_bzr_radio, self.vcs_git_radio = [
                render_radio_widget_part(widget, value, current_value)
                for value in (VCSType.BZR, VCSType.GIT)]

    def validate_widgets(self, data, names=None):
        """See `LaunchpadFormView`."""
        if self.widgets.get('vcs') is not None:
            # Set widgets as required or optional depending on the vcs
            # field.
            super(BaseSnapEditView, self).validate_widgets(data, ['vcs'])
            vcs = data.get('vcs')
            if vcs == VCSType.BZR:
                self.widgets['branch'].context.required = True
                self.widgets['git_ref'].context.required = False
            elif vcs == VCSType.GIT:
                self.widgets['branch'].context.required = False
                self.widgets['git_ref'].context.required = True
            else:
                raise AssertionError("Unknown branch type %s" % vcs)
        super(BaseSnapEditView, self).validate_widgets(data, names=names)

    @action('Update snap package', name='update')
    def request_action(self, action, data):
        vcs = data.pop('vcs', None)
        if vcs == VCSType.BZR:
            data['git_ref'] = None
        elif vcs == VCSType.GIT:
            data['branch'] = None
        new_processors = data.get('processors')
        if new_processors is not None:
            if set(self.context.processors) != set(new_processors):
                self.context.setProcessors(
                    new_processors, check_permissions=True, user=self.user)
            del data['processors']
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

    @property
    def adapters(self):
        """See `LaunchpadFormView`."""
        return {ISnapEditSchema: self.context}


class SnapAdminView(BaseSnapEditView):
    """View for administering snap packages."""

    @property
    def label(self):
        return 'Administer %s snap package' % self.context.name

    page_title = 'Administer'

    field_names = ['require_virtualized']


class SnapEditView(BaseSnapEditView, EnableProcessorsMixin):
    """View for editing snap packages."""

    @property
    def label(self):
        return 'Edit %s snap package' % self.context.name

    page_title = 'Edit'

    field_names = [
        'owner', 'name', 'distro_series', 'vcs', 'branch', 'git_ref']
    custom_widget('distro_series', LaunchpadRadioWidget)
    custom_widget('vcs', LaunchpadRadioWidget)
    custom_widget('git_ref', GitRefWidget)

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        super(SnapEditView, self).setUpFields()
        self.form_fields += self.createEnabledProcessors(
            self.context.available_processors,
            u"The architectures that this snap package builds for. Some "
            u"architectures are restricted and may only be enabled or "
            u"disabled by administrators.")

    @property
    def initial_values(self):
        if self.context.git_ref is not None:
            vcs = VCSType.GIT
        else:
            vcs = VCSType.BZR
        return {'vcs': vcs}

    def validate(self, data):
        super(SnapEditView, self).validate(data)
        owner = data.get('owner', None)
        name = data.get('name', None)
        if owner and name:
            try:
                snap = getUtility(ISnapSet).getByName(owner, name)
                if snap != self.context:
                    self.setFieldError(
                        'name',
                        'There is already a snap package owned by %s with '
                        'this name.' % owner.displayname)
            except NoSuchSnap:
                pass
        if 'processors' in data:
            available_processors = set(self.context.available_processors)
            for processor in self.context.processors:
                if (processor not in available_processors and
                        processor not in data['processors']):
                    # This processor is not currently available for
                    # selection, but is enabled.  Leave it untouched.
                    data['processors'].append(processor)


class SnapDeleteView(BaseSnapEditView):
    """View for deleting snap packages."""

    @property
    def label(self):
        return 'Delete %s snap package' % self.context.name

    page_title = 'Delete'

    field_names = []

    @property
    def has_builds(self):
        return not self.context.builds.is_empty()

    @action('Delete snap package', name='delete')
    def delete_action(self, action, data):
        owner = self.context.owner
        self.context.destroySelf()
        # XXX cjwatson 2015-07-17: This should go to Person:+snaps or
        # similar (or something on SnapSet?) once that exists.
        self.next_url = canonical_url(owner)
