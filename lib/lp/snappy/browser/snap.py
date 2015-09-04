# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap views."""

__metaclass__ = type
__all__ = [
    'SnapDeleteView',
    'SnapEditView',
    'SnapNavigation',
    'SnapNavigationMenu',
    'SnapView',
    ]

from lazr.restful.interface import (
    copy_field,
    use_template,
    )
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import Choice

from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    render_radio_widget_part,
    )
from lp.app.browser.lazrjs import (
    InlinePersonEditPickerWidget,
    TextLineEditorWidget,
    )
from lp.app.browser.tales import format_link
from lp.app.widgets.itemswidgets import LaunchpadRadioWidget
from lp.registry.enums import VCSType
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
from lp.snappy.interfaces.snap import (
    ISnap,
    ISnapSet,
    NoSuchSnap,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuildSet
from lp.soyuz.browser.build import get_build_by_id_str


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
            url=canonical_url(self.context.owner, view_name="+snap"),
            text="Snap packages", inside=self.context.owner)


class SnapNavigationMenu(NavigationMenu):
    """Navigation menu for snap packages."""

    usedfor = ISnap

    facet = 'overview'

    links = ('admin', 'delete', 'edit')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        return Link('+admin', 'Administer snap package', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        return Link('+edit', 'Edit snap package', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def delete(self):
        return Link('+delete', 'Delete snap package', icon='trash-icon')


class SnapView(LaunchpadView):
    """Default view of a Snap."""

    @property
    def builds(self):
        return builds_for_snap(self.context)

    @property
    def name_widget(self):
        name = ISnap['name']
        title = "Edit the snap package name"
        return TextLineEditorWidget(
            self.context, name, title, 'h1', max_width='95%', truncate_lines=1)

    @property
    def person_picker(self):
        field = copy_field(
            ISnap['owner'],
            vocabularyName='UserTeamsParticipationPlusSelfSimpleDisplay')
        return InlinePersonEditPickerWidget(
            self.context, field, format_link(self.context.owner),
            header='Change owner', step_title='Select a new owner')

    @property
    def source(self):
        if self.context.branch is not None:
            return self.context.branch
        elif self.context.git_repository is not None:
            return self.context.git_repository.getRefByPath(
                self.context.git_path)
        else:
            return None


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
    git_repository = copy_field(ISnap['git_repository'], required=True)
    git_path = copy_field(ISnap['git_path'], required=True)


class BaseSnapAddEditView(LaunchpadEditFormView):

    schema = ISnapEditSchema

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        super(BaseSnapAddEditView, self).setUpWidgets()
        widget = self.widgets.get('vcs')
        if widget is not None:
            current_value = widget._getFormValue()
            self.vcs_bzr, self.vcs_git = [
                render_radio_widget_part(widget, value, current_value)
                for value in (VCSType.BZR, VCSType.GIT)]

    def validate_widgets(self, data, names=None):
        """See `LaunchpadFormView`."""
        if 'vcs' in self.widgets:
            # Set widgets as required or optional depending on the vcs
            # field.
            super(BaseSnapAddEditView, self).validate_widgets(data, ['vcs'])
            vcs = data.get('vcs')
            if vcs == VCSType.BZR:
                self.widgets['branch'].context.required = True
                self.widgets['git_repository'].context.required = False
                self.widgets['git_path'].context.required = False
            elif vcs == VCSType.GIT:
                self.widgets['branch'].context.required = False
                self.widgets['git_repository'].context.required = True
                self.widgets['git_path'].context.required = True
            else:
                raise AssertionError("Unknown branch type %s" % vcs)
        super(BaseSnapAddEditView, self).validate_widgets(data, names=names)


class BaseSnapEditView(BaseSnapAddEditView):

    @action('Update snap package', name='update')
    def request_action(self, action, data):
        vcs = data.pop('vcs', None)
        if vcs == VCSType.BZR:
            data['git_repository'] = None
            data['git_path'] = None
        elif vcs == VCSType.GIT:
            data['branch'] = None
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

    @property
    def adapters(self):
        """See `LaunchpadFormView`."""
        return {ISnapEditSchema: self.context}


class SnapAdminView(BaseSnapEditView):
    """View for administering snap packages."""

    @property
    def title(self):
        return 'Administer %s snap package' % self.context.name

    label = title

    field_names = ['require_virtualized']

    @property
    def initial_values(self):
        return {'require_virtualized': self.context.require_virtualized}


class SnapEditView(BaseSnapEditView):
    """View for editing snap packages."""

    @property
    def title(self):
        return 'Edit %s snap package' % self.context.name

    label = title

    field_names = [
        'owner', 'name', 'distro_series', 'vcs', 'branch', 'git_repository',
        'git_path']
    custom_widget('distro_series', LaunchpadRadioWidget)
    custom_widget('vcs', LaunchpadRadioWidget)

    @property
    def initial_values(self):
        if self.context.git_repository is not None:
            vcs = VCSType.GIT
        else:
            vcs = VCSType.BZR
        return {
            'distro_series': self.context.distro_series,
            'vcs': vcs,
            }

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


class SnapDeleteView(BaseSnapEditView):
    """View for deleting snap packages."""

    @property
    def title(self):
        return 'Delete %s snap package' % self.context.name

    label = title

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
