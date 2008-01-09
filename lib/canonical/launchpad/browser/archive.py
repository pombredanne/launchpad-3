# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for archive."""

__metaclass__ = type

__all__ = [
    'ArchiveNavigation',
    'ArchiveFacets',
    'ArchiveOverviewMenu',
    'ArchiveView',
    'ArchiveSearchView',
    'ArchiveActivateView',
    'ArchiveBuildsView',
    'ArchiveEditView',
    'ArchiveAdminView',
    ]

from zope.schema import Choice
from zope.app.form.browser import TextAreaWidget
from zope.app.form.utility import setUpWidget
from zope.app.form.interfaces import IInputWidget
from zope.component import getUtility
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.sourceslist import (
    SourcesListEntries, SourcesListEntriesView)
from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchive, IArchiveSet, IBuildSet, IHasBuildRecords,
    ILaunchpadCelebrities, IPPAActivateForm, IPublishingSet, NotFoundError,
    PackagePublishingStatus)
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
    links = ['admin', 'edit', 'builds', 'search']

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

    def search(self):
        text = 'Search source packages'
        return Link('+search', text, icon='info')


class ArchiveViewBase(LaunchpadView):
    """Common features for Archive view classes."""

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


class ArchiveView(ArchiveViewBase):
    """Default Archive view class

    Implements useful actions and collects useful sets for the pagetemplate.
    """

    __used_for__ = IArchive

    def initialize(self):
        """Set up select control and a batched list of publishing records."""
        entries = SourcesListEntries(
            self.context.distribution, self.context.archive_url,
            self.context.series_with_sources)
        self.sources_list_entries = SourcesListEntriesView(
            entries, self.request)

        self.name_filter = self.request.get('field.name_filter')
        status_filter = self.request.get('field.status_filter', 'published')
        self.setupStatusFilterWidget(status_filter)


class ArchiveSearchView(ArchiveViewBase):
    """Archive search view class. """

    __used_for__ = IArchive

    def initialize(self):
        """Set up a batched list of publishing records."""
        self.name_filter = self.request.get('field.name_filter')
        status_filter = self.request.get('field.status_filter', 'published')

        self.setupStatusFilterWidget(status_filter)

        publishing = self.context.getPublishedSources(
            name=self.name_filter,
            status=self.selected_status_filter.value.collection)

        self.batchnav = BatchNavigator(publishing, self.request)
        self.search_results = self.batchnav.currentBatch()

    def performPPAAction(self):
        """Execute the designed action over the selected queue items.

        Returns a message describing the action executed or None if nothing
        was done.
        """
        if self.request.method != "POST":
            return

        if not check_permission('launchpad.Edit', self.context):
            self.error = 'You do not have permission to act on this archive.'
            return

        delete = self.request.form.get('DELETE', '')
        include_binaries = self.request.form.get('DELETE_BINARIES', '')
        deletion_comment = self.request.form.get('DELETION_COMMENT', '')
        pub_src_ids = self.request.form.get('PUB_SRC_ID', '')

        if not delete or not pub_src_ids:
            self.error = "No items selected."
            return

        if not deletion_comment:
            self.error = "Deletion comment is required."
            return

        if not isinstance(pub_src_ids, list):
            pub_src_ids = [pub_src_ids]

        if include_binaries:
            target = "sources and binaries"
        else:
            target = "sources"

        header = 'Deleting %s:<br>' % target

        success = []
        failure = []
        for pub_src_id in pub_src_ids:
            info = "nahh"
            pub = getUtility(IPublishingSet).getSource(int(pub_src_id))
            if pub.id % 2:
                failure.append('FAILED: %s (%s)' %
                               (pub.displayname, pub.id))
            else:
                success.append('OK: %s' % pub.displayname)

        report = '%s<br>%s<br>%s' % (
            header, ', '.join(success + failure), deletion_comment)
        return report


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
