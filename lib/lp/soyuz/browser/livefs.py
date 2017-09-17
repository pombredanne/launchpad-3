# Copyright 2014-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""LiveFS views."""

__metaclass__ = type
__all__ = [
    'LiveFSAddView',
    'LiveFSDeleteView',
    'LiveFSEditView',
    'LiveFSNavigation',
    'LiveFSNavigationMenu',
    'LiveFSView',
    ]

import json

from lazr.restful import ResourceJSONEncoder
from lazr.restful.interface import (
    copy_field,
    use_template,
    )
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import (
    Choice,
    Text,
    )

from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.app.browser.lazrjs import (
    InlinePersonEditPickerWidget,
    TextLineEditorWidget,
    )
from lp.app.browser.tales import format_link
from lp.app.widgets.itemswidgets import LaunchpadRadioWidget
from lp.code.vocabularies.sourcepackagerecipe import BuildableDistroSeries
from lp.registry.interfaces.series import SeriesStatus
from lp.services.features import getFeatureFlag
from lp.services.webapp import (
    canonical_url,
    enabled_with_permission,
    LaunchpadView,
    Link,
    Navigation,
    NavigationMenu,
    stepthrough,
    )
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.breadcrumb import (
    Breadcrumb,
    NameBreadcrumb,
    )
from lp.soyuz.browser.build import get_build_by_id_str
from lp.soyuz.interfaces.livefs import (
    ILiveFS,
    ILiveFSSet,
    LIVEFS_FEATURE_FLAG,
    LiveFSFeatureDisabled,
    NoSuchLiveFS,
    )
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuildSet


class LiveFSNavigation(Navigation):
    usedfor = ILiveFS

    @stepthrough('+build')
    def traverse_build(self, name):
        build = get_build_by_id_str(ILiveFSBuildSet, name)
        if build is None or build.livefs != self.context:
            return None
        return build


class LiveFSBreadcrumb(NameBreadcrumb):

    @property
    def inside(self):
        return Breadcrumb(
            self.context.owner,
            url=canonical_url(self.context.owner, view_name="+livefs"),
            text="Live filesystems", inside=self.context.owner)


class LiveFSNavigationMenu(NavigationMenu):
    """Navigation menu for live filesystems."""

    usedfor = ILiveFS

    facet = 'overview'

    links = ('admin', 'delete', 'edit')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        return Link('+admin', 'Administer live filesystem', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        return Link('+edit', 'Edit live filesystem', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def delete(self):
        return Link('+delete', 'Delete live filesystem', icon='trash-icon')


class LiveFSView(LaunchpadView):
    """Default view of a LiveFS."""

    @property
    def page_title(self):
        return "%(name)s's %(livefs_name)s live filesystem in %(series)s" % {
            'name': self.context.owner.displayname,
            'livefs_name': self.context.name,
            'series': self.context.distro_series.fullseriesname,
            }

    label = page_title

    @property
    def builds(self):
        return builds_for_livefs(self.context)

    @property
    def person_picker(self):
        field = copy_field(
            ILiveFS['owner'],
            vocabularyName='UserTeamsParticipationPlusSelfSimpleDisplay')
        return InlinePersonEditPickerWidget(
            self.context, field, format_link(self.context.owner),
            header='Change owner', step_title='Select a new owner')

    @property
    def name_widget(self):
        name = ILiveFS['name']
        title = "Edit the live filesystem name"
        return TextLineEditorWidget(
            self.context, name, title, 'h1', max_width='95%', truncate_lines=1)

    @property
    def sorted_metadata_items(self):
        if self.context.metadata is None:
            return []
        return sorted(self.context.metadata.items())


def builds_for_livefs(livefs):
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
        build for build in livefs.pending_builds
        if check_permission('launchpad.View', build)]
    for build in livefs.completed_builds:
        if not check_permission('launchpad.View', build):
            continue
        builds.append(build)
        if len(builds) >= 10:
            break
    return builds


class ILiveFSEditSchema(Interface):
    """Schema for adding or editing a live filesystem."""

    use_template(ILiveFS, include=[
        'owner',
        'name',
        'require_virtualized',
        'relative_build_score',
        ])
    distro_series = Choice(
        vocabulary='BuildableDistroSeries', title=u'Distribution series')
    metadata = Text(
        title=u'Live filesystem build metadata',
        description=(
            u'A JSON dictionary of data about the image.  Entries here will '
             'be passed to the builder slave.'))


class LiveFSMetadataValidatorMixin:
    """Class to validate that live filesystem properties are valid."""

    def validate(self, data):
        if data['metadata']:
            try:
                json.loads(data['metadata'])
            except Exception as e:
                self.setFieldError('metadata', str(e))


class LiveFSAddView(LiveFSMetadataValidatorMixin, LaunchpadFormView):
    """View for creating live filesystems."""

    title = label = 'Create a new live filesystem'

    schema = ILiveFSEditSchema
    field_names = ['owner', 'name', 'distro_series', 'metadata']
    custom_widget('distro_series', LaunchpadRadioWidget)

    def initialize(self):
        """See `LaunchpadView`."""
        if not getFeatureFlag(LIVEFS_FEATURE_FLAG):
            raise LiveFSFeatureDisabled
        super(LiveFSAddView, self).initialize()

    @property
    def initial_values(self):
        series = [
            term.value for term in BuildableDistroSeries()
            if term.value.status in (
                SeriesStatus.CURRENT, SeriesStatus.DEVELOPMENT)][0]
        return {
            'owner': self.user,
            'distro_series': series,
            'metadata': '{}',
            }

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action('Create live filesystem', name='create')
    def request_action(self, action, data):
        livefs = getUtility(ILiveFSSet).new(
            self.user, data['owner'], data['distro_series'], data['name'],
            json.loads(data['metadata']))
        self.next_url = canonical_url(livefs)

    def validate(self, data):
        super(LiveFSAddView, self).validate(data)
        owner = data.get('owner', None)
        distro_series = data['distro_series']
        name = data.get('name', None)
        if owner and name:
            if getUtility(ILiveFSSet).exists(owner, distro_series, name):
                self.setFieldError(
                    'name',
                    'There is already a live filesystem for %s owned by %s '
                    'with this name.' % (
                        distro_series.displayname, owner.displayname))


class BaseLiveFSEditView(LaunchpadEditFormView):

    schema = ILiveFSEditSchema

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action('Update live filesystem', name='update')
    def request_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

    @property
    def adapters(self):
        """See `LaunchpadFormView`."""
        return {ILiveFSEditSchema: self.context}


class LiveFSAdminView(BaseLiveFSEditView):
    """View for administering live filesystems."""

    @property
    def title(self):
        return 'Administer %s live filesystem' % self.context.name

    label = title

    field_names = ['require_virtualized', 'relative_build_score']

    @property
    def initial_values(self):
        return {
            'require_virtualized': self.context.require_virtualized,
            'relative_build_score': self.context.relative_build_score,
            }


class LiveFSEditView(LiveFSMetadataValidatorMixin, BaseLiveFSEditView):
    """View for editing live filesystems."""

    @property
    def title(self):
        return 'Edit %s live filesystem' % self.context.name

    label = title

    field_names = ['owner', 'name', 'distro_series', 'metadata']
    custom_widget('distro_series', LaunchpadRadioWidget)

    @property
    def initial_values(self):
        return {
            'distro_series': self.context.distro_series,
            'metadata': json.dumps(
                self.context.metadata, ensure_ascii=False,
                cls=ResourceJSONEncoder),
            }

    def updateContextFromData(self, data, context=None, notify_modified=True):
        """See `LaunchpadEditFormView`."""
        if 'metadata' in data:
            data['metadata'] = json.loads(data['metadata'])
        super(LiveFSEditView, self).updateContextFromData(
            data, context=context, notify_modified=notify_modified)

    def validate(self, data):
        super(LiveFSEditView, self).validate(data)
        owner = data.get('owner', None)
        distro_series = data['distro_series']
        name = data.get('name', None)
        if owner and name:
            try:
                livefs = getUtility(ILiveFSSet).getByName(
                    owner, distro_series, name)
                if livefs != self.context:
                    self.setFieldError(
                        'name',
                        'There is already a live filesystem for %s owned by '
                        '%s with this name.' % (
                            distro_series.displayname, owner.displayname))
            except NoSuchLiveFS:
                pass


class LiveFSDeleteView(BaseLiveFSEditView):
    """View for deleting live filesystems."""

    @property
    def title(self):
        return 'Delete %s live filesystem' % self.context.name

    label = title

    field_names = []

    @property
    def has_builds(self):
        return not self.context.builds.is_empty()

    @action('Delete live filesystem', name='delete')
    def delete_action(self, action, data):
        owner = self.context.owner
        self.context.destroySelf()
        # XXX cjwatson 2015-05-07 bug=1332479: This should go to
        # Person:+livefs once that exists.
        self.next_url = canonical_url(owner)
