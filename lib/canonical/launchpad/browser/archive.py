# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for archive."""

__metaclass__ = type

__all__ = [
    'ArchiveNavigation',
    'ArchiveFacets',
    'ArchiveOverviewMenu',
    'ArchiveView',
    'ArchiveActivateView',
    'ArchiveBuildsView',
    'ArchiveEditView',
    'ArchiveAdminView',
    ]

from zope.app.form.browser import TextAreaWidget
from zope.app.form.browser.add import AddView
from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.interfaces import (
    IArchive, IArchiveSet, IBuildSet, IHasBuildRecords)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Navigation, Link, LaunchpadView,
    LaunchpadEditFormView, ApplicationMenu, enabled_with_permission,
    action, custom_widget, canonical_url, stepthrough)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.lp.dbschema import ArchivePurpose


class ArchiveNavigation(Navigation):
    """Navigation methods for IArchive."""
    usedfor = IArchive

    def breadcrumb(self):
        return self.context.title

    @stepthrough('+build')
    def traverse_build(self, name):
        try:
            build_id = int(name)
        except ValueError:
            return None
        try:
            return getUtility(IBuildSet).getByBuildID(build_id)
        except NotFoundError:
            return None


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

    def searchPackages(self):
        """Setup a batched ISPPH list.

        Return None, so use tal:condition="not: view/searchPackage" to
        invoke it in template.
        """
        self.name_filter = self.request.get('name_filter', None)
        publishing = self.context.getPublishedSources(
            name=self.name_filter)
        self.batchnav = BatchNavigator(publishing, self.request)
        self.search_results = self.batchnav.currentBatch()


class ArchiveActivateView(AddView):

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self._nextURL = '.'
        AddView.__init__(self, context, request)

        # Redirects to the PPA page if it already exists.
        if self.context.archive is not None:
            self.request.response.redirect(canonical_url(self.context.archive))

    def createAndAdd(self, data):
        ppa = getUtility(IArchiveSet).new(
            owner=self.context, purpose=ArchivePurpose.PPA,
            description=data['description'])
        self._nextURL = canonical_url(ppa)
        return ppa

    def nextURL(self):
        return self._nextURL


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
