# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for archive."""

__metaclass__ = type

__all__ = [
    'ArchiveNavigation',
    'ArchiveFacets',
    'ArchiveOverviewMenu',
    'ArchiveView',
    'ArchiveBuildsView',
    'ArchiveEditView',
    'ArchiveAdminView',
    ]

from zope.app.form.browser import TextAreaWidget

from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.interfaces import (
    IArchive, IHasBuildRecords)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Navigation, Link, LaunchpadView,
    LaunchpadEditFormView, ApplicationMenu, enabled_with_permission,
    action, custom_widget, canonical_url)


class ArchiveNavigation(Navigation):
    """Navigation methods for IArchive."""
    usedfor = IArchive

    def breadcrumb(self):
        return self.context.title

class ArchiveFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IArchive."""
    enable_only = ['overview']

    usedfor = IArchive


class ArchiveOverviewMenu(ApplicationMenu):
    """Overview Menu for IArchive."""
    usedfor = IArchive
    facet = 'overview'
    links = ['admin', 'edit', 'builds']

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer archive'
        return Link('+admin', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    def builds(self):
        text = 'View build records'
        return Link('+builds', text, icon='info')


class ArchiveView(LaunchpadView):
    """Default Archive view class

    Implements useful actions and colect useful set for the pagetemplate.
    """
    __used_for__ = IArchive


class ArchiveBuildsView(BuildRecordsView):
    """Build Records View for IArchive."""
    __used_for__ = IHasBuildRecords


class BaseArchiveEditView(LaunchpadEditFormView):

    schema = IArchive
    field_names = []

    @action(_("Save"), name="save")
    def action_save(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class ArchiveEditView(BaseArchiveEditView):

    field_names = ['description', 'whiteboard']
    custom_widget(
        'description', TextAreaWidget, height=10, width=30)


class ArchiveAdminView(BaseArchiveEditView):

    field_names = ['enabled', 'authorized_size', 'whiteboard']
    custom_widget(
        'whiteboard', TextAreaWidget, height=10, width=30)
