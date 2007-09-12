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
from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.interfaces import (
    IArchive, IPPAActivateForm, IArchiveSet, IBuildSet, IHasBuildRecords,
    NotFoundError)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, enabled_with_permission,
    stepthrough, ApplicationMenu, LaunchpadEditFormView, LaunchpadFormView,
    LaunchpadView, Link, Navigation, StandardLaunchpadFacets)
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

    usedfor = IArchive
    enable_only = ['overview']


class ArchiveOverviewMenu(ApplicationMenu):
    """Overview Menu for IArchive."""

    usedfor = IArchive
    facet = 'overview'
    links = ['admin', 'edit', 'builds', 'view_tos']

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

    @enabled_with_permission('launchpad.Edit')
    def view_tos(self):
        text = 'Review terms of service'
        return Link('+view-tos', text, icon='info')


class ArchiveView(LaunchpadView):
    """Default Archive view class

    Implements useful actions and collects useful sets for the pagetemplate.
    """

    __used_for__ = IArchive

    def initialize(self):
        """Setup a batched `ISourcePackagePublishingHistory` list."""
        self.name_filter = self.request.get('name_filter', None)
        publishing = self.context.getPublishedSources(
            name=self.name_filter)
        self.batchnav = BatchNavigator(publishing, self.request)
        self.search_results = self.batchnav.currentBatch()


class ArchiveActivateView(LaunchpadFormView):
    """PPA activation view class.

    Ensure user has accepted the PPA Terms of Use by clicking in the
    'accepted' checkbox.

    It redirects to PPA page when PPA is already activated.
    """

    schema = IPPAActivateForm

    def initialize(self):
        """Redirects user to the PPA page if it is already activated."""
        LaunchpadFormView.initialize(self)
        if self.context.archive is not None:
            self.request.response.redirect(canonical_url(self.context.archive))

    def validate(self, data):
        """Ensure user has checked the 'accepted' checkbox."""
        if len(self.errors) == 0:
            if not data.get('accepted'):
                self.addError(
                    "PPA ToS has to be accepted to complete the activation.")

    @action(_("Activate"), name="activate")
    def action_save(self, action, data):
        """Activate PPA and moves to its page."""
        ppa = getUtility(IArchiveSet).ensure(
            owner=self.context, distribution=None, purpose=ArchivePurpose.PPA,
            description=data['description'])
        self.next_url = canonical_url(ppa)


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
