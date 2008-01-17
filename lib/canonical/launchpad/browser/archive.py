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

from zope.app.form.browser import TextAreaWidget
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice, List
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.sourceslist import (
    SourcesListEntries, SourcesListEntriesView)
from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchive, IArchiveConsoleForm, IArchiveSet, IBuildSet,
    IHasBuildRecords, ILaunchpadCelebrities, IPPAActivateForm,
    NotFoundError, PackagePublishingStatus)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, enabled_with_permission,
    stepthrough, ApplicationMenu, LaunchpadEditFormView, LaunchpadFormView,
    LaunchpadView, Link, Navigation, StandardLaunchpadFacets)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.widgets import (
    LabeledMultiCheckBoxWidget, LaunchpadDropdownWidget)
from canonical.widgets.textwidgets import StrippedTextWidget


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

    @enabled_with_permission('launchpad.Edit')
    def console(self):
        text = 'Package console'
        return Link('+console', text, icon='edit')


class ArchiveViewBase:
    """Common features for Archive view classes."""

    @property
    def is_active(self):
        """Whether or not this PPA already have publications in it."""
        return bool(self.context.getPublishedSources())

    @property
    def source_count_text(self):
        """Return the correct form of the source counter notice."""
        if self.context.number_of_sources == 1:
            return '%s source package' % self.context.number_of_sources
        else:
            return '%s source packages' % self.context.number_of_sources

    @property
    def binary_count_text(self):
        """Return the correct form of the binary counter notice."""
        if self.context.number_of_binaries == 1:
            return '%s binary package' % self.context.number_of_binaries
        else:
            return '%s binary packages' % self.context.number_of_binaries


class ArchiveView(ArchiveViewBase, LaunchpadView):
    """Default Archive view class.

    Implements useful actions and collects useful sets for the page template.
    """

    __used_for__ = IArchive

    def initialize(self):
        """Setup infrastructure for the PPA index page.

        Setup sources list entries widget, package filter widget and the
        search result list.
        """
        self.setupSourcesListEntries()
        self.setupStatusFilterWidget()
        self.setupPackageBatchResult()

    def setupStatusFilterWidget(self):
        """Build a customized publishing status select widget.

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

        status_filter = self.request.get('field.status_filter', 'published')
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

    @property
    def search_requested(self):
        """Whether or not the search form was used."""
        return self.request.get('field.name_filter') is not None

    def getPublishingRecords(self):
        """Return the publishing records results.

        It requests 'self.selected_status_filter' to be set.
        """
        name_filter = self.request.get('field.name_filter')
        return self.context.getPublishedSources(
            name=name_filter,
            status=self.selected_status_filter.value.collection)

    def setupPackageBatchResult(self):
        """Setup of the package search results."""
        self.batchnav = BatchNavigator(
            self.getPublishingRecords(), self.request)
        self.search_results = self.batchnav.currentBatch()


class PublishingStatusDropdownWidget(LaunchpadDropdownWidget):
    """Redefining 'no value' message."""

    _messageNoValue = _('Any status')


class ArchiveConsoleView(ArchiveViewBase, LaunchpadFormView):
    """Archive console view class.

    This view presents the default package-search slot associated with a
    POST form implementing actions that could be performed upon a set of
    selected packages.
    """

    schema = IArchiveConsoleForm

    # Maximum number of 'selected_sources' options presented.
    max_options_presented = 10

    custom_widget('status_filter', PublishingStatusDropdownWidget)
    custom_widget('comment', StrippedTextWidget, displayWidth=50)
    custom_widget('selected_sources', LabeledMultiCheckBoxWidget,
                  orientation='vertical', visible=True)

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpFields(self)
        # XXX cprov 20080117: we have to setup the schema widget earlier
        # because some values (name & status) are required to setup
        # 'selected_sources'. Ideally we could skip them in setUpWidgets
        # but re-setup doesn't seem to hurt.
        LaunchpadFormView.setUpWidgets(self)
        self.form_fields = (
            self.createSelectedSourcesField() + self.form_fields)

    def createSelectedSourcesField(self):
        """Creates the 'selected_sources' field.

        'selected_sources' is a list of elements of a vocabulary based on
        the search results presented. This way zope validation mechanisms
        will do the job for us.
        """
        terms = []
        for pub in self.sources[:self.max_options_presented]:
            terms.append(SimpleTerm(pub, str(pub.id), pub.displayname))
        return form.Fields(
            List(__name__='selected_sources',
                 title=_('Available sources'),
                 value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                 required=False,
                 default=[],
                 description=_('Select one or more sources to be submitted '
                               'to an action.')),
            custom_widget=self.custom_widgets['selected_sources'],
            render_context=self.render_context)

    @cachedproperty
    def sources(self):
        """Query source publishing records.

        Consider the 'name_filter' and 'status_filter' form values.
        """
        if self.widgets['name_filter'].hasInput():
            name_filter = self.widgets['name_filter'].getInputValue()
        else:
            name_filter = None

        if self.widgets['status_filter'].hasInput():
            status_filter = self.widgets['status_filter'].getInputValue()
        else:
            status_filter = None

        return self.context.getPublishedSources(
            name=name_filter, status=status_filter)

    @cachedproperty
    def available_options_size(self):
        """Number of available source options."""
        return self.sources.count()

    @property
    def has_ignored_options(self):
        """Whether of not some options got ignored."""
        return self.available_options_size > self.max_options_presented

    @action(_("Search"), name="search")
    def action_search(self, action, data):
        """Simply re-issue the form with the new values."""
        pass

    def validate_delete(self, action, data):
        """Validate deletion action."""
        comment = data.get('comment')
        selected_sources = data.get('selected_sources', [])

        if len(selected_sources) == 0:
            self.addError("No sources selected.")

        if comment is None:
            self.addError("Comment should be provided for deletions.")

        # XXX cprov 20080115: this check belongs to the content class.
        for source in selected_sources:
            if source.status != PackagePublishingStatus.PUBLISHED:
                self.addError('Cannot delete non-published source (%s).'
                              % source.displayname)

    @action(_("Delete"), name="delete")
    def action_delete(self, action, data):
        """Perform the deletion of the selected packages.

        The deletion will be performed upon the 'selected_sources' contents
        respecting the auxiliary parameter, 'including_binaries' and
        'comment'.
        """
        # XXX cprov 20080115: using the "@action(validator='validate_delete')
        # property passes empty 'data'. We are calling it manually for now.
        self.validate_delete(action, data)
        if len(self.errors) != 0:
            return

        include_binaries = data.get('include_binaries')
        comment = data.get('comment')
        selected_sources = data.get('selected_sources')

        # Perform deletion.
        for source in selected_sources:
            source.requestDeletion(self.user, comment)
            if include_binaries:
                for bin in source.getPublishedBinaries():
                    bin.requestDeletion(self.user, comment)

        # Present a page notification describing the action.
        if include_binaries:
            target = "Sources and binaries"
        else:
            target = "Sources"
        messages = []
        messages.append(
            '<p>%s deleted by %s request:' % (target, self.user.displayname))
        for source in selected_sources:
            messages.append('<br/>%s' % source.displayname)
        messages.append('</p>')
        messages.append("<p>Deletion comment: %s</p>" % comment)

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
