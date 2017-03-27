# Copyright 2015-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap views."""

__metaclass__ = type
__all__ = [
    'SnapAddView',
    'SnapAuthorizeView',
    'SnapContextMenu',
    'SnapDeleteView',
    'SnapEditView',
    'SnapNavigation',
    'SnapNavigationMenu',
    'SnapRequestBuildsView',
    'SnapView',
    ]

from urllib import urlencode

from lazr.restful.fields import Reference
from lazr.restful.interface import (
    copy_field,
    use_template,
    )
import yaml
from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility
from zope.interface import Interface
from zope.schema import (
    Choice,
    List,
    TextLine,
    )

from lp import _
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    render_radio_widget_part,
    )
from lp.app.browser.lazrjs import InlinePersonEditPickerWidget
from lp.app.browser.tales import format_link
from lp.app.enums import PRIVATE_INFORMATION_TYPES
from lp.app.interfaces.informationtype import IInformationType
from lp.app.widgets.itemswidgets import (
    LabeledMultiCheckBoxWidget,
    LaunchpadDropdownWidget,
    LaunchpadRadioWidget,
    )
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.code.browser.widgets.gitref import GitRefWidget
from lp.code.errors import (
    GitRepositoryBlobNotFound,
    GitRepositoryScanFault,
    )
from lp.code.interfaces.gitref import IGitRef
from lp.registry.enums import VCSType
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features import getFeatureFlag
from lp.services.helpers import english_list
from lp.services.scripts import log
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
from lp.services.webapp.breadcrumb import (
    Breadcrumb,
    NameBreadcrumb,
    )
from lp.services.webapp.url import urlappend
from lp.services.webhooks.browser import WebhookTargetNavigationMixin
from lp.snappy.browser.widgets.snaparchive import SnapArchiveWidget
from lp.snappy.browser.widgets.storechannels import StoreChannelsWidget
from lp.snappy.interfaces.snap import (
    CannotAuthorizeStoreUploads,
    ISnap,
    ISnapSet,
    NoSuchSnap,
    SNAP_PRIVATE_FEATURE_FLAG,
    SnapBuildAlreadyPending,
    SnapPrivateFeatureDisabled,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuildSet
from lp.snappy.interfaces.snappyseries import (
    ISnappyDistroSeriesSet,
    ISnappySeriesSet,
    )
from lp.snappy.interfaces.snapstoreclient import (
    BadRequestPackageUploadResponse,
    )
from lp.soyuz.browser.archive import EnableProcessorsMixin
from lp.soyuz.browser.build import get_build_by_id_str
from lp.soyuz.interfaces.archive import IArchive


class SnapNavigation(WebhookTargetNavigationMixin, Navigation):
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

    links = ('admin', 'edit', 'webhooks', 'delete')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        return Link('+admin', 'Administer snap package', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        return Link('+edit', 'Edit snap package', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def webhooks(self):
        return Link(
            '+webhooks', 'Manage webhooks', icon='edit',
            enabled=bool(getFeatureFlag('webhooks.new.enabled')))

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
            vocabularyName='AllUserTeamsParticipationPlusSelfSimpleDisplay')
        return InlinePersonEditPickerWidget(
            self.context, field, format_link(self.context.owner),
            header='Change owner', step_title='Select a new owner')

    @property
    def build_frequency(self):
        if self.context.auto_build:
            return 'Built automatically'
        else:
            return 'Built on request'

    @property
    def store_channels(self):
        return ', '.join(self.context.store_channels)


def builds_for_snap(snap):
    """A list of interesting builds.

    All pending builds are shown, as well as 1-10 recent builds.  Recent
    builds are ordered by date finished (if completed) or date_started (if
    date finished is not set due to an error building or other circumstance
    which resulted in the build not being completed).  This allows started
    but unfinished builds to show up in the view but be discarded as more
    recent builds become available.

    Builds that the user does not have permission to see are excluded (by
    the model code).
    """
    builds = list(snap.pending_builds)
    if len(builds) < 10:
        builds.extend(snap.completed_builds[:10 - len(builds)])
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
            title=u'Pocket', vocabulary=PackagePublishingPocket, required=True,
            description=u'The package stream within the source distribution '
                'series to use when building the snap package.')

    custom_widget('archive', SnapArchiveWidget)
    custom_widget('distro_arch_series', LabeledMultiCheckBoxWidget)
    custom_widget('pocket', LaunchpadDropdownWidget)

    help_links = {
        "pocket": u"/+help-snappy/snap-build-pocket.html",
        }

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def initial_values(self):
        """See `LaunchpadFormView`."""
        return {
            'archive': self.context.distro_series.main_archive,
            'distro_arch_series': self.context.getAllowedArchitectures(),
            'pocket': PackagePublishingPocket.UPDATES,
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
        'private',
        'require_virtualized',
        'auto_build',
        'store_upload',
        ])
    store_distro_series = Choice(
        vocabulary='BuildableSnappyDistroSeries', required=True,
        title=u'Series')
    vcs = Choice(vocabulary=VCSType, required=True, title=u'VCS')

    # Each of these is only required if vcs has an appropriate value.  Later
    # validation takes care of adjusting the required attribute.
    branch = copy_field(ISnap['branch'], required=True)
    git_ref = copy_field(ISnap['git_ref'], required=True)

    # These are only required if auto_build is True.  Later validation takes
    # care of adjusting the required attribute.
    auto_build_archive = copy_field(ISnap['auto_build_archive'], required=True)
    auto_build_pocket = copy_field(ISnap['auto_build_pocket'], required=True)

    # This is only required if store_upload is True.  Later validation takes
    # care of adjusting the required attribute.
    store_name = copy_field(ISnap['store_name'], required=True)
    store_channels = copy_field(ISnap['store_channels'], required=True)


def log_oops(error, request):
    """Log an oops report without raising an error."""
    info = (error.__class__, error, None)
    getUtility(IErrorReportingUtility).raising(info, request)


class SnapAuthorizeMixin:

    def requestAuthorization(self, snap):
        try:
            self.next_url = SnapAuthorizeView.requestAuthorization(
                snap, self.request)
        except BadRequestPackageUploadResponse as e:
            self.setFieldError(
                'store_upload',
                'Cannot get permission from the store to upload this package.')
            log_oops(e, self.request)


class SnapAddView(
        LaunchpadFormView, SnapAuthorizeMixin, EnableProcessorsMixin):
    """View for creating snap packages."""

    page_title = label = 'Create a new snap package'

    schema = ISnapEditSchema
    field_names = [
        'owner',
        'name',
        'store_distro_series',
        'auto_build',
        'auto_build_archive',
        'auto_build_pocket',
        'store_upload',
        'store_name',
        'store_channels',
        ]
    custom_widget('store_distro_series', LaunchpadRadioWidget)
    custom_widget('auto_build_archive', SnapArchiveWidget)
    custom_widget('store_channels', StoreChannelsWidget)
    custom_widget('auto_build_pocket', LaunchpadDropdownWidget)

    help_links = {
        "auto_build_pocket": u"/+help-snappy/snap-build-pocket.html",
        }

    def initialize(self):
        """See `LaunchpadView`."""
        super(SnapAddView, self).initialize()

        # Once initialized, if the private_snap flag is disabled, it
        # prevents snap creation for private contexts.
        if not getFeatureFlag(SNAP_PRIVATE_FEATURE_FLAG):
            if (IInformationType.providedBy(self.context) and
                self.context.information_type in PRIVATE_INFORMATION_TYPES):
                raise SnapPrivateFeatureDisabled

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        super(SnapAddView, self).setUpFields()
        self.form_fields += self.createEnabledProcessors(
            getUtility(IProcessorSet).getAll(),
            u"The architectures that this snap package builds for. Some "
            u"architectures are restricted and may only be enabled or "
            u"disabled by administrators.")

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        super(SnapAddView, self).setUpWidgets()
        self.widgets['processors'].widget_class = 'processors'

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def initial_values(self):
        store_name = None
        if self.has_snappy_distro_series and IGitRef.providedBy(self.context):
            # Try to extract Snap store name from snapcraft.yaml file.
            try:
                paths = (
                    'snap/snapcraft.yaml',
                    'snapcraft.yaml',
                    '.snapcraft.yaml',
                    )
                for i, path in enumerate(paths):
                    try:
                        blob = self.context.repository.getBlob(
                            path, self.context.name)
                        break
                    except GitRepositoryBlobNotFound:
                        if i == len(paths) - 1:
                            raise
                # Beware of unsafe yaml.load()!
                store_name = yaml.safe_load(blob).get('name')
            except GitRepositoryScanFault:
                log.exception("Failed to get Snap manifest from Git %s",
                              self.context.unique_name)
            except (AttributeError, yaml.YAMLError):
                # Ignore parsing errors from invalid, user-supplied YAML
                pass
            except Exception as e:
                log.exception(
                    "Failed to extract name from Snap manifest at Git %s: %s",
                    self.context.unique_name, unicode(e))

        store_series = getUtility(ISnappySeriesSet).getAll().first()
        if store_series.preferred_distro_series is not None:
            distro_series = store_series.preferred_distro_series
        else:
            distro_series = store_series.usable_distro_series.first()
        sds_set = getUtility(ISnappyDistroSeriesSet)
        store_distro_series = sds_set.getByBothSeries(
            store_series, distro_series)

        return {
            'store_name': store_name,
            'owner': self.user,
            'store_distro_series': store_distro_series,
            'processors': [
                p for p in getUtility(IProcessorSet).getAll()
                if p.build_by_default],
            'auto_build_archive': distro_series.main_archive,
            'auto_build_pocket': PackagePublishingPocket.UPDATES,
            }

    @property
    def has_snappy_distro_series(self):
        return not getUtility(ISnappyDistroSeriesSet).getAll().is_empty()

    def validate_widgets(self, data, names=None):
        """See `LaunchpadFormView`."""
        if self.widgets.get('auto_build') is not None:
            # Set widgets as required or optional depending on the
            # auto_build field.
            super(SnapAddView, self).validate_widgets(data, ['auto_build'])
            auto_build = data.get('auto_build', False)
            self.widgets['auto_build_archive'].context.required = auto_build
            self.widgets['auto_build_pocket'].context.required = auto_build
        if self.widgets.get('store_upload') is not None:
            # Set widgets as required or optional depending on the
            # store_upload field.
            super(SnapAddView, self).validate_widgets(data, ['store_upload'])
            store_upload = data.get('store_upload', False)
            self.widgets['store_name'].context.required = store_upload
            self.widgets['store_channels'].context.required = store_upload
        super(SnapAddView, self).validate_widgets(data, names=names)

    @action('Create snap package', name='create')
    def create_action(self, action, data):
        if IGitRef.providedBy(self.context):
            kwargs = {'git_ref': self.context}
        else:
            kwargs = {'branch': self.context}
        private = not getUtility(
            ISnapSet).isValidPrivacy(False, data['owner'], **kwargs)
        if not data.get('auto_build', False):
            data['auto_build_archive'] = None
            data['auto_build_pocket'] = None
        snap = getUtility(ISnapSet).new(
            self.user, data['owner'],
            data['store_distro_series'].distro_series, data['name'],
            auto_build=data['auto_build'],
            auto_build_archive=data['auto_build_archive'],
            auto_build_pocket=data['auto_build_pocket'],
            processors=data['processors'], private=private,
            store_upload=data['store_upload'],
            store_series=data['store_distro_series'].snappy_series,
            store_name=data['store_name'],
            store_channels=data.get('store_channels'), **kwargs)
        if data['store_upload']:
            self.requestAuthorization(snap)
        else:
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


class BaseSnapEditView(LaunchpadEditFormView, SnapAuthorizeMixin):

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

    @property
    def has_snappy_distro_series(self):
        return not getUtility(ISnappyDistroSeriesSet).getAll().is_empty()

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
        if self.widgets.get('auto_build') is not None:
            # Set widgets as required or optional depending on the
            # auto_build field.
            super(BaseSnapEditView, self).validate_widgets(
                data, ['auto_build'])
            auto_build = data.get('auto_build', False)
            self.widgets['auto_build_archive'].context.required = auto_build
            self.widgets['auto_build_pocket'].context.required = auto_build
        if self.widgets.get('store_upload') is not None:
            # Set widgets as required or optional depending on the
            # store_upload field.
            super(BaseSnapEditView, self).validate_widgets(
                data, ['store_upload'])
            store_upload = data.get('store_upload', False)
            self.widgets['store_name'].context.required = store_upload
            self.widgets['store_channels'].context.required = store_upload
        super(BaseSnapEditView, self).validate_widgets(data, names=names)

    def _needStoreReauth(self, data):
        """Does this change require reauthorizing to the store?"""
        store_upload = data.get('store_upload', False)
        store_distro_series = data.get('store_distro_series')
        store_name = data.get('store_name')
        if (not store_upload or
                store_distro_series is None or store_name is None):
            return False
        if not self.context.store_upload:
            return True
        if store_distro_series.snappy_series != self.context.store_series:
            return True
        if store_name != self.context.store_name:
            return True
        return False

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
        if not data.get('auto_build', False):
            if 'auto_build_archive' in data:
                del data['auto_build_archive']
            if 'auto_build_pocket' in data:
                del data['auto_build_pocket']
        store_upload = data.get('store_upload', False)
        if not store_upload:
            if 'store_name' in data:
                del data['store_name']
            if 'store_channels' in data:
                del data['store_channels']
        need_store_reauth = self._needStoreReauth(data)
        self.updateContextFromData(data)
        if need_store_reauth:
            self.requestAuthorization(self.context)
        else:
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

    field_names = ['private', 'require_virtualized']

    def validate(self, data):
        super(SnapAdminView, self).validate(data)
        private = data.get('private', None)
        if private is not None:
            if not getUtility(ISnapSet).isValidPrivacy(
                    private, self.context.owner, self.context.branch,
                    self.context.git_ref):
                self.setFieldError(
                    'private',
                    u'This snap contains private information and cannot '
                    u'be public.'
                )


class SnapEditView(BaseSnapEditView, EnableProcessorsMixin):
    """View for editing snap packages."""

    @property
    def label(self):
        return 'Edit %s snap package' % self.context.name

    page_title = 'Edit'

    field_names = [
        'owner',
        'name',
        'store_distro_series',
        'vcs',
        'branch',
        'git_ref',
        'auto_build',
        'auto_build_archive',
        'auto_build_pocket',
        'store_upload',
        'store_name',
        'store_channels',
        ]
    custom_widget('store_distro_series', LaunchpadRadioWidget)
    custom_widget('store_channels', StoreChannelsWidget)
    custom_widget('vcs', LaunchpadRadioWidget)
    custom_widget('git_ref', GitRefWidget, allow_external=True)
    custom_widget('auto_build_archive', SnapArchiveWidget)
    custom_widget('auto_build_pocket', LaunchpadDropdownWidget)

    help_links = {
        "auto_build_pocket": u"/+help-snappy/snap-build-pocket.html",
        }

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
        initial_values = {}
        if self.context.store_series is None:
            # XXX cjwatson 2016-04-26: Remove this case once all existing
            # Snaps have had a store_series backfilled.
            sds_set = getUtility(ISnappyDistroSeriesSet)
            initial_values['store_distro_series'] = sds_set.getByDistroSeries(
                self.context.distro_series).first()
        if self.context.git_ref is not None:
            initial_values['vcs'] = VCSType.GIT
        else:
            initial_values['vcs'] = VCSType.BZR
        if self.context.auto_build_pocket is None:
            initial_values['auto_build_pocket'] = (
                PackagePublishingPocket.UPDATES)
        return initial_values

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
            widget = self.widgets['processors']
            for processor in self.context.processors:
                if processor not in data['processors']:
                    if processor not in available_processors:
                        # This processor is not currently available for
                        # selection, but is enabled.  Leave it untouched.
                        data['processors'].append(processor)
                    elif processor.name in widget.disabled_items:
                        # This processor is restricted and currently
                        # enabled. Leave it untouched.
                        data['processors'].append(processor)


class SnapAuthorizationException(Exception):
    pass


class SnapAuthorizeView(LaunchpadEditFormView):
    """View for authorizing snap package uploads to the store."""

    @property
    def label(self):
        return 'Authorize store uploads of %s' % self.context.name

    page_title = 'Authorize store uploads'

    class schema(Interface):
        """Schema for authorizing snap package uploads to the store."""

        discharge_macaroon = TextLine(
            title=u'Serialized discharge macaroon', required=True)

    render_context = False

    focusedElementScript = None

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @classmethod
    def requestAuthorization(cls, snap, request):
        """Begin the process of authorizing uploads of a snap package."""
        try:
            sso_caveat_id = snap.beginAuthorization()
            base_url = canonical_url(snap, view_name='+authorize')
            login_url = urlappend(base_url, '+login')
            login_url += '?%s' % urlencode([
                ('macaroon_caveat_id', sso_caveat_id),
                ('discharge_macaroon_action', 'field.actions.complete'),
                ('discharge_macaroon_field', 'field.discharge_macaroon'),
                ])
            return login_url
        except CannotAuthorizeStoreUploads as e:
            request.response.addInfoNotification(unicode(e))
            request.response.redirect(canonical_url(snap))
            return

    @action('Begin authorization', name='begin')
    def begin_action(self, action, data):
        login_url = self.requestAuthorization(self.context, self.request)
        if login_url is not None:
            self.request.response.redirect(login_url)

    @action('Complete authorization', name='complete')
    def complete_action(self, action, data):
        if not data.get('discharge_macaroon'):
            self.addError(structured(
                _(u'Uploads of %(snap)s to the store were not authorized.'),
                snap=self.context.name))
            return
        self.context.completeAuthorization(
            discharge_macaroon=data['discharge_macaroon'])
        self.request.response.addInfoNotification(structured(
            _(u'Uploads of %(snap)s to the store are now authorized.'),
            snap=self.context.name))
        self.request.response.redirect(canonical_url(self.context))

    @property
    def adapters(self):
        """See `LaunchpadFormView`."""
        return {self.schema: self.context}


class SnapDeleteView(BaseSnapEditView):
    """View for deleting snap packages."""

    @property
    def label(self):
        return 'Delete %s snap package' % self.context.name

    page_title = 'Delete'

    field_names = []

    @action('Delete snap package', name='delete')
    def delete_action(self, action, data):
        owner = self.context.owner
        self.context.destroySelf()
        self.next_url = canonical_url(owner, view_name='+snaps')
