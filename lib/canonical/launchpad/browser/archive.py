# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for archive."""

__metaclass__ = type

__all__ = [
    'ArchiveNavigation',
    'ArchiveFacets',
    'ArchiveOverviewMenu',
    'ArchiveView',
    'ArchiveConsoleView',
    'ArchiveActivateView',
    'ArchiveBuildsView',
    'ArchiveEditView',
    'ArchiveAdminView',
    ]

from zope.schema import Choice
from zope.app.form.browser import TextAreaWidget, CheckBoxWidget
from zope.app.form.utility import setUpWidget
from zope.app.form.interfaces import IInputWidget
from zope.component import getUtility
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.sourceslist import (
    SourcesListEntries, SourcesListEntriesView)
from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchive, IArchiveConsoleForm, IArchiveSet, IBuildSet,
    IHasBuildRecords, ILaunchpadCelebrities, IPPAActivateForm, IPublishingSet,
    NotFoundError, PackagePublishingStatus)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, enabled_with_permission,
    stepthrough, ApplicationMenu, LaunchpadEditFormView, LaunchpadFormView,
    LaunchpadView, Link, Navigation, StandardLaunchpadFacets)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.authorization import check_permission


class ArchiveNavigation(Navigation):
    """Navigation methods for IArchive."""

    usedfor = IArchive

    def breadcrumb(self):
        if self.context.purpose == ArchivePurpose.PPA:
            return "PPA"
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
    links = ['admin', 'edit', 'builds', 'console']

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

    @enabled_with_permission('launchpad.Admin')
    def console(self):
        text = 'Package console'
        return Link('+console', text, icon='edit')


class ArchiveViewBase(LaunchpadView):
    """Common features for Archive view classes."""

    # Whether to present or not default results on page load.
    show_default_results = True

    @property
    def is_active(self):
        return bool(self.context.getPublishedSources())

    def source_count_text(self):
        if self.context.number_of_sources == 1:
            return '%s source package' % self.context.number_of_sources
        else:
            return '%s source packages' % self.context.number_of_sources

    def binary_count_text(self):
        if self.context.number_of_binaries == 1:
            return '%s binary package' % self.context.number_of_binaries
        else:
            return '%s binary packages' % self.context.number_of_binaries

    def setupStatusFilterWidget(self, status_filter):
        """Setup a customized publishing status select widget.

        Receives the one of the established field values:

        ('published', 'superseded', 'any').

        Allow user to select between:

         * Published:  PENDING and PUBLISHED records,
         * Superseded: SUPERSEDED and DELETED records,
         * Any Status

        """
        class StatusCollection:
            def __init__(self, collection=None):
                self.collection = collection

        published_status = [PackagePublishingStatus.PENDING,
                            PackagePublishingStatus.PUBLISHED]
        superseded_status = [PackagePublishingStatus.SUPERSEDED,
                             PackagePublishingStatus.DELETED]

        status_terms = [
            SimpleTerm(StatusCollection(published_status),
                       'published', 'Published'),
            SimpleTerm(StatusCollection(superseded_status),
                       'superseded', 'Superseded'),
            SimpleTerm(StatusCollection(), 'any', 'Any Status')
            ]
        status_vocabulary = SimpleVocabulary(status_terms)

        self.selected_status_filter = status_vocabulary.getTermByToken(
            status_filter)

        field = Choice(
            __name__='status_filter', title=_("Status Filter"),
            vocabulary=status_vocabulary, required=True)
        setUpWidget(self, 'status_filter',  field, IInputWidget)

    @property
    def plain_status_filter_widget(self):
        """Render a <select> control with no <div>s around it."""
        return self.status_filter_widget.renderValue(
            self.selected_status_filter.value)

    def setupSourcesListEntries(self):
        """Setup of the sources list entries widget."""
        entries = SourcesListEntries(
            self.context.distribution, self.context.archive_url,
            self.context.series_with_sources)
        self.sources_list_entries = SourcesListEntriesView(
            entries, self.request)

    def setupPackageFilters(self):
        """Setup of the package search form."""
        self.name_filter = self.request.get('field.name_filter')
        status_filter = self.request.get('field.status_filter', 'published')
        self.setupStatusFilterWidget(status_filter)

    def setupPackageSearchResult(self):
        """Setup a list of results for the package search."""
        if self.name_filter is not None or self.show_default_results:
            publishing = self.context.getPublishedSources(
                name=self.name_filter,
                status=self.selected_status_filter.value.collection)
        else:
            publishing = []
        self.batchnav = BatchNavigator(publishing, self.request)
        self.search_results = self.batchnav.currentBatch()


class ArchiveView(ArchiveViewBase):
    """Default Archive view class

    Implements useful actions and collects useful sets for the pagetemplate.
    """

    __used_for__ = IArchive

    def initialize(self):
        self.setupSourcesListEntries()
        self.setupPackageFilters()
        self.setupPackageSearchResult()


class ArchiveConsoleView(ArchiveViewBase, LaunchpadFormView):
    """Archive console view class.

    This view presents the default package-search slot associated with a
    POST form implementing actions that could be performed upon a set of
    selected packages.
    """

    schema = IArchiveConsoleForm
    # Do not present search results if 'Search' button is not hit.
    show_default_results = False

    def initialize(self):
        LaunchpadFormView.initialize(self)
        self.setupPackageFilters()
        self.setupPackageSearchResult()

# XXX cprov 20080111: ideally 'field.selected_sources' should get validated
# by the zope infrastructure and obtained in delete action via data dictionary.
# Currently this field is also poorly rendered inside:
#   sourcepackagepublishing-listing-ppa-details.pt template
# which is not only confusing but also broken since it will be rendered in the
# wrong place (+index) if the user has launchpad.Admin permission.

    def _getSelectedSources(self):
        selected_sources_ids = self.request.get('field.selected_sources')

        if selected_sources_ids is None:
            return []

        if not isinstance(selected_sources_ids, list):
            selected_sources_ids = [selected_sources_ids]

        if not selected_sources_ids:
            return []

        pub_set = getUtility(IPublishingSet)
        selected_sources = []
        for source_id in selected_sources_ids:
            source = pub_set.getSource(int(source_id))
            selected_sources.append(source)

        return selected_sources

    def validate(self, data):
        """Retrieve 'selected_sources' directly from the request.

        Ensure we have only valid and published sources selected.
        """
        if len(self.errors) != 0:
            return

        selected_sources = self._getSelectedSources()
        if not selected_sources:
            self.addError("No published sources selected.")
            return

        for source in selected_sources:
            if source.status != PackagePublishingStatus.PUBLISHED:
                self.addError('Cannot delete non-published source (%s)'
                              % source.displayname)
                return
        # Finally inject 'selected_sources' in the validated form data.
        data['selected_sources'] = selected_sources

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self.next_url = canonical_url(self.context)

    @action(_("Delete"), name="delete")
    def action_delete(self, action, data):
        include_binaries = data.get('include_binaries')
        comment = data.get('comment')
        selected_sources = data.get('selected_sources')
        messages = []
        for source in selected_sources:
            source.requestDeletion(self.user, comment)
            messages.append(
                '<p>%s</p>' % source.displayname)
            if include_binaries:
                for bin in source.getPublishedBinaries():
                    bin.requestDeletion(self.user, comment)

        # Present a page notification describing the action.
        if include_binaries:
            target = "Sources and binaries"
        else:
            target = "Sources"
        messages.insert(
            0, '<p>%s deleted by %s request:</p>' % (
            target, self.user.displayname))
        messages.append("Deletion comment: %s" % comment)
        notification = "\n".join(messages)

        self.request.response.addNotification(notification)


class ArchiveActivateView(LaunchpadFormView):
    """PPA activation view class.

    Ensure user has accepted the PPA Terms of Use by clicking in the
    'accepted' checkbox.

    It redirects to PPA page when PPA is already activated.
    """

    schema = IPPAActivateForm
    custom_widget('description', TextAreaWidget, height=3)

    def initialize(self):
        """Redirects user to the PPA page if it is already activated."""
        LaunchpadFormView.initialize(self)
        self.distribution = getUtility(ILaunchpadCelebrities).ubuntu
        if self.context.archive is not None:
            self.request.response.redirect(
                canonical_url(self.context.archive))

    def validate(self, data):
        """Ensure user has checked the 'accepted' checkbox."""
        if len(self.errors) == 0:
            if not data.get('accepted'):
                self.addError(
                    "PPA Terms of Service must be accepted to activate "
                    "your PPA.")

    @action(_("Activate"), name="activate")
    def action_save(self, action, data):
        """Activate PPA and moves to its page."""
        ppa = getUtility(IArchiveSet).ensure(
            owner=self.context, purpose=ArchivePurpose.PPA,
            description=data['description'], distribution=None)
        self.next_url = canonical_url(ppa)

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self.next_url = canonical_url(self.context)


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
