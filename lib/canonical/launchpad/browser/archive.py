# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for archive."""

__metaclass__ = type

__all__ = [
    'archive_to_structuralheading',
    'ArchiveAdminView',
    'ArchiveActivateView',
    'ArchiveBadges',
    'ArchiveBuildsView',
    'ArchiveContextMenu',
    'ArchiveEditDependenciesView',
    'ArchiveEditView',
    'ArchiveNavigation',
    'ArchivePackageCopyingView',
    'ArchivePackageDeletionView',
    'ArchiveView',
    ]

from zope.app.form.browser import TextAreaWidget
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice, List
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.cachedproperty import cachedproperty
from canonical.database.sqlbase import flush_database_caches
from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.sourceslist import (
    SourcesListEntries, SourcesListEntriesView)
from canonical.launchpad.interfaces import (
    ArchivePurpose, BuildStatus, DistroSeriesStatus, IArchive,
    IArchiveEditDependenciesForm, IArchivePackageCopyingForm,
    IArchivePackageDeletionForm, IArchiveSourceSelectionForm, IArchiveSet,
    IBuildSet, IHasBuildRecords, ILaunchpadCelebrities, IPPAActivateForm,
    IStructuralHeaderPresentation, NotFoundError, PackagePublishingPocket,
    PackagePublishingStatus)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, enabled_with_permission,
    stepthrough, ContextMenu, LaunchpadEditFormView,
    LaunchpadFormView, LaunchpadView, Link, Navigation)
from canonical.launchpad.webapp.badge import HasBadgeBase
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.menu import structured
from canonical.widgets import LabeledMultiCheckBoxWidget
from canonical.widgets.itemswidgets import LaunchpadDropdownWidget
from canonical.widgets.textwidgets import StrippedTextWidget


class ArchiveBadges(HasBadgeBase):
    """Provides `IHasBadges` for `IArchive`."""

    def getPrivateBadgeTitle(self):
        """Return private badge info useful for a tooltip."""
        return "This archive is private."


class ArchiveNavigation(Navigation):
    """Navigation methods for IArchive."""

    usedfor = IArchive

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


class ArchiveContextMenu(ContextMenu):
    """Overview Menu for IArchive."""

    usedfor = IArchive
    links = ['ppa', 'admin', 'edit', 'builds', 'delete', 'copy',
             'edit_dependencies']

    def ppa(self):
        text = 'View PPA'
        return Link(canonical_url(self.context), text, icon='info')

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
    def delete(self):
        text = 'Delete packages'
        return Link('+delete-packages', text, icon='edit')

    @enabled_with_permission('launchpad.AnyPerson')
    def copy(self):
        text = 'Copy packages'
        return Link('+copy-packages', text, icon='info')

    @enabled_with_permission('launchpad.Edit')
    def edit_dependencies(self):
        text = 'Edit dependencies'
        return Link('+edit-dependencies', text, icon='edit')


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

    @cachedproperty
    def simplified_status_vocabulary(self):
        """Return a simplified publishing status vocabulary.

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
        return SimpleVocabulary(status_terms)


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

        See `status_vocabulary`.
        """
        status_filter = self.request.get('field.status_filter', 'published')
        self.selected_status_filter = (
            self.simplified_status_vocabulary.getTermByToken(status_filter))

        field = Choice(
            __name__='status_filter', title=_("Status Filter"),
            vocabulary=self.simplified_status_vocabulary, required=True)
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


class ArchiveSourceSelectionFormView(ArchiveViewBase, LaunchpadFormView):
    """Base class to implement a source selection widget for PPAs."""

    schema = IArchiveSourceSelectionForm

    # Maximum number of 'sources' presented.
    max_sources_presented = 50

    custom_widget('selected_sources', LabeledMultiCheckBoxWidget)
    custom_widget('status_filter', LaunchpadDropdownWidget)

    def setUpFields(self):
        """Override `LaunchpadFormView`.

        In addition to setting schema fields, also initialize the
        'name_filter' and 'status_filter' widgets required to setup
        'selected_sources' field.

        See `createSimplifiedStatusFilterField` and
        `createSelectedSourcesField` methods.
        """
        LaunchpadFormView.setUpFields(self)

        # Build and store 'status_filter' field.
        status_field = self.createSimplifiedStatusFilterField()

        # Setup widgets for the for 'name_filter' and 'status_filter'
        # fields because they are required to build 'selected_sources'
        # field.
        initial_fields = status_field + self.form_fields.select('name_filter')
        self.widgets = form.setUpWidgets(
            initial_fields, self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)

        # Build and store 'selected_sources' field.
        selected_sources_field = self.createSelectedSourcesField()

        # Append the just created fields to the global form fields, so
        # `setupWidgets` will do its job.
        self.form_fields += status_field + selected_sources_field

    def setUpWidgets(self):
        """Override `LaunchpadFormView`.

        Omitting the fields already processed in setUpFields ('name_filter'
        and 'status_filter').
        """
        self.widgets += form.setUpWidgets(
            self.form_fields.omit('name_filter').omit('status_filter'),
            self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)

    def focusedElementScript(self):
        """Override `LaunchpadFormView`.

        Ensure focus is only set if there are sources actually presented.
        """
        if not self.has_sources:
            return ''
        return LaunchpadFormView.focusedElementScript(self)

    def createSimplifiedStatusFilterField(self):
        """Return a simplified publishing status filter field.

        See `status_vocabulary` and `default_status_filter`.
        """
        return form.Fields(
            Choice(__name__='status_filter', title=_("Status Filter"),
                   vocabulary=self.simplified_status_vocabulary,
                   required=True, default=self.default_status_filter.value),
            custom_widget=self.custom_widgets['status_filter'])

    def createSelectedSourcesField(self):
        """Creates the 'selected_sources' field.

        'selected_sources' is a list of elements of a vocabulary based on
        the source publications that will be presented. This way zope
        infrastructure will do the validation for us.
        """
        terms = []
        for pub in self.sources[:self.max_sources_presented]:
            terms.append(SimpleTerm(pub, str(pub.id), pub.displayname))
        return form.Fields(
            List(__name__='selected_sources',
                 title=_('Available sources'),
                 value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                 required=False,
                 default=[],
                 description=_('Select one or more sources to be submitted '
                               'to an action.')),
            custom_widget=self.custom_widgets['selected_sources'])

    def refreshSelectedSourcesWidget(self):
        """Refresh 'selected_sources' widget.

        It's called after deletions to eliminate the just-deleted records
        from the widget presented.
        """
        flush_database_caches()
        self.form_fields = self.form_fields.omit('selected_sources')
        self.form_fields = (
            self.createSelectedSourcesField() + self.form_fields)
        self.widgets = form.setUpWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)

    @property
    def sources(self):
        """Query undeleted source publishing records.

        Consider the 'name_filter' form value.
        """
        if self.widgets['name_filter'].hasInput():
            name_filter = self.widgets['name_filter'].getInputValue()
        else:
            name_filter = None

        if self.widgets['status_filter'].hasInput():
            status_filter = self.widgets['status_filter'].getInputValue()
        else:
            status_filter = self.widgets['status_filter'].context.default

        return self.getSources(
            name=name_filter, status=status_filter.collection)

    @cachedproperty
    def has_sources(self):
        """Whether or not the PPA has published source packages."""
        available_sources = self.getSources()
        return bool(available_sources)

    @property
    def available_sources_size(self):
        """Number of available sources."""
        return self.sources.count()

    @property
    def has_undisplayed_sources(self):
        """Whether or not some sources are not displayed in the widget."""
        return self.available_sources_size > self.max_sources_presented

    @property
    def default_status_filter(self):
        """Return the default status_filter value."""
        raise NotImplementedError(
            'Default status_filter should be defined by callsites')

    def getSources(self, name=None, status=None):
        """Source lookup method, should be implemented by callsites."""
        raise NotImplementedError(
            'Source lookup should be implemented by callsites')



class ArchivePackageDeletionView(ArchiveSourceSelectionFormView):
    """Archive package deletion view class.

    This view presents a package selection slot in a POST form implementing
    a deletion action that can be performed upon a set of selected packages.
    """

    schema = IArchivePackageDeletionForm

    custom_widget('deletion_comment', StrippedTextWidget, displayWidth=50)

    @property
    def default_status_filter(self):
        """Present records in any status by default."""
        return self.simplified_status_vocabulary.getTermByToken('any')

    def getSources(self, name=None, status=None):
        """Return all undeleted sources in the context PPA.

        Filters the results using the given 'name'.
        See `IArchive.getSourcesForDeletion`.
        """
        return self.context.getSourcesForDeletion(name=name, status=status)

    @action(_("Update"), name="update")
    def action_update(self, action, data):
        """Simply re-issue the form with the new values."""
        # The 'selected_sources' widget will always be updated
        # considering 'name_filter' input value when the page is loaded.
        pass

    def validate_delete(self, action, data):
        """Validate deletion parameters.

        Ensure we have, at least, one source selected and deletion_comment
        is given.
        """
        form.getWidgetsData(self.widgets, 'field', data)

        if len(data.get('selected_sources', [])) == 0:
            self.setFieldError('selected_sources', 'No sources selected.')

        if data.get('deletion_comment') is None:
            self.setFieldError(
                'deletion_comment', 'Deletion comment is required.')

    @action(_("Request Deletion"), name="delete", validator="validate_delete")
    def action_delete(self, action, data):
        """Perform the deletion of the selected packages.

        The deletion will be performed upon the 'selected_sources' contents
        storing the given 'deletion_comment'.
        """
        if len(self.errors) != 0:
            return

        comment = data.get('deletion_comment')
        selected_sources = data.get('selected_sources')

        # Perform deletion of the source and its binaries.
        for source in selected_sources:
            source.requestDeletion(self.user, comment)
            for bin in source.getPublishedBinaries():
                bin.requestDeletion(self.user, comment)

        # We end up issuing the published_source query twice this way,
        # because we need the original available source vocabulary to
        # validade the the submitted deletion request. Once the deletion
        # request is validated and performed we call 'flush_database_caches'
        # and rebuild the 'selected_sources' widget.
        self.refreshSelectedSourcesWidget()

        # Present a page notification describing the action.
        messages = []
        messages.append(
            '<p>Source and binaries deleted by %s request:'
            % self.user.displayname)
        for source in selected_sources:
            messages.append('<br/>%s' % source.displayname)
        messages.append('</p>')
        # Replace the 'comment' content added by the user via structured(),
        # so it will be quoted appropriately.
        messages.append("<p>Deletion comment: %(comment)s</p>")

        notification = "\n".join(messages)
        self.request.response.addNotification(
            structured(notification, comment=comment))


class DestinationArchiveRadioWidget(LaunchpadDropdownWidget):
    """Redefining default display value as 'This PPA'."""
    _messageNoValue = _("vocabulary-copy-to-context-ppa", "This PPA")


class DestinationSeriesDropdownWidget(LaunchpadDropdownWidget):
    """Redefining default display value as 'The same series'."""
    _messageNoValue = _("vocabulary-copy-to-same-series", "The same series")


class ArchivePackageCopyingView(ArchiveSourceSelectionFormView):
    """Archive package copying view class.

    This view presents a package selection slot in a POST form implementing
    a copying action that can be performed upon a set of selected packages.
    """
    schema = IArchivePackageCopyingForm

    custom_widget('destination_archive', DestinationArchiveRadioWidget)
    custom_widget('destination_series', DestinationSeriesDropdownWidget)

    # Maximum number of 'sources' presented.
    max_sources_presented = 20

    default_pocket = PackagePublishingPocket.RELEASE

    @property
    def default_status_filter(self):
        """Present published records by default."""
        return self.simplified_status_vocabulary.getTermByToken('published')

    def getSources(self, name=None, status=None):
        """Return all sources ever published in the context PPA.

        Filters the results using the given 'name'.
        See `IArchive.getPublishedSources`.
        """
        return self.context.getPublishedSources(name=name, status=status)

    def setUpFields(self):
        """Override `ArchiveSourceSelectionFormView`.

        See `createDestinationFields` method.
        """
        ArchiveSourceSelectionFormView.setUpFields(self)
        self.form_fields = (
            self.createDestinationArchiveField() +
            self.createDestinationSeriesField() +
            self.form_fields)

    @cachedproperty
    def ppas_for_user(self):
        """Return all PPAs for which the user accessing the page can copy."""
        return getUtility(IArchiveSet).getPPAsForUser(self.user)

    @cachedproperty
    def can_copy(self):
        """Whether or not the current user can copy packages to any PPA."""
        return self.ppas_for_user.count() > 0

    @cachedproperty
    def can_copy_to_context_ppa(self):
        """Whether or not the current user can copy to the context PPA."""
        return self.user.inTeam(self.context.owner)

    def createDestinationArchiveField(self):
        """Create the 'destination_archive' field."""
        terms = []
        required = True

        for ppa in self.ppas_for_user:
            # Do not include the context PPA in the dropdown widget
            # and make this field not required. This way we can safely
            # default to the context PPA when copying.
            if self.can_copy_to_context_ppa and self.context == ppa:
                required = False
                continue
            terms.append(SimpleTerm(ppa, str(ppa.owner.name), ppa.title))

        return form.Fields(
            Choice(__name__='destination_archive',
                   title=_('Destination PPA'),
                   vocabulary=SimpleVocabulary(terms),
                   description=_("Select the destination PPA."),
                   missing_value=self.context,
                   required=required),
            custom_widget=self.custom_widgets['destination_archive'])

    def createDestinationSeriesField(self):
        """Create the 'destination_series' field."""
        terms = []
        # XXX cprov 20080408: this code uses the context PPA series instead
        # of targeted or all series available in Launchpad. It might become
        # a problem when we support PPAs for other distribution. If we do
        # it will be probably simpler to use the DistroSeries vocabulary
        # and validate the selected value before copying.
        for series in self.context.distribution.serieses:
            if series.status == DistroSeriesStatus.OBSOLETE:
                continue
            terms.append(
                SimpleTerm(series, str(series.name), series.displayname))
        return form.Fields(
            Choice(__name__='destination_series',
                   title=_('Destination series'),
                   vocabulary=SimpleVocabulary(terms),
                   description=_("Select the destination series."),
                   required=False),
            custom_widget=self.custom_widgets['destination_series'])

    @action(_("Update"), name="update")
    def action_update(self, action, data):
        """Simply re-issue the form with the new values."""
        pass

    def _checkCopyDestination(self, source, series, pocket, archive):
        """Whether or not the given destination is allowed for copy.

        It is always ok to copy a DELETED publication.

        Return False if the given destination is the current location
        package, True otherwise.
        """
        if source.status == PackagePublishingStatus.DELETED:
            return True

        if series is not None:
            if (source.distroseries == series and
                source.archive == archive and
                source.pocket == pocket):
                return False
        else:
            if source.archive == archive and source.pocket == pocket:
                return False

        return True

    def _doCopy(self, sources, series, pocket, archive,
                include_binaries=False):
        """Perform the complete copy of the given sources.

        Copy each item of the given list of `SourcePackagePublishingHistory`
        to the given destination, also copy published binaries for each
        source if requested to.

        :param: sources: a list of `SourcePackagePublishingHistory`;
        :param: series: the target `DistroSeries`, if None is given the same
            current source distroseries will be used as destination;
        :param: pocket: the target `PackagePublishingPocket`;
        :param: archive: the target `Archive`;
        :param: include_binaries: optional boolean, controls whether or
            not the published binaries for each given source should be also
            copied along with the source;
        :return: a list of `SourcePackagePublishingHistory` and
            `BinaryPackagePublishingHistory` corresponding to the copied
            publications.
        """
        copies = []
        for source in sources:
            if series is None:
                destination_series = source.distroseries
            else:
                destination_series = series
            source_copy = source.copyTo(destination_series, pocket, archive)
            copies.append(source_copy)
            if not include_binaries:
                source_copy.createMissingBuilds()
                continue
            for binary in source.getPublishedBinaries():
                binary_copy = binary.copyTo(
                    destination_series, pocket, archive)
                copies.append(binary_copy)
        return copies

    def validate_copy(self, action, data):
        """Validate copy parameters.

        Ensure we have:

         * At least, one source selected;
         * The default series input is not given when copying to the
           context PPA;
         * The selecte destination fits all selected sources.
        """
        form.getWidgetsData(self.widgets, 'field', data)

        selected_sources = data.get('selected_sources', [])
        destination_archive = data.get('destination_archive')
        destination_series = data.get('destination_series')
        destination_pocket = self.default_pocket

        if len(selected_sources) == 0:
            self.setFieldError('selected_sources', 'No sources selected.')
            return

        broken_copies = []
        for source in selected_sources:
            if not self._checkCopyDestination(
                source, destination_series, destination_pocket,
                destination_archive):
                broken_copies.append(source)

        if len(broken_copies) == 0:
            return

        if len(broken_copies) == 1:
            error_message = """
                The following source cannot be copied because it
                was targeted to the same location: %s
            """ % broken_copies[0].displayname
        else:
            error_message = """
                The following sources cannot be copied because they
                were targeted to the same location: %s
            """ % ", ".join([source.displayname for source in broken_copies])

        self.setFieldError('selected_sources', error_message)

    @action(_("Copy Packages"), name="copy", validator="validate_copy")
    def action_copy(self, action, data):
        """Perform the copy of the selected packages."""
        if len(self.errors) != 0:
            return

        selected_sources = data.get('selected_sources')
        destination_archive = data.get('destination_archive')
        destination_series = data.get('destination_series')
        include_binaries = data.get('include_binaries')

        destination_pocket = self.default_pocket

        copies = self._doCopy(
            selected_sources, destination_series, destination_pocket,
            destination_archive, include_binaries)

        # Refresh the selected_sources, it changes when sources get
        # copied within the PPA.
        self.refreshSelectedSourcesWidget()

        # Present a page notification describing the action.
        messages = []
        messages.append(
            '<p>Packages copied to <a href="%s">%s</a>:</p>' % (
                canonical_url(destination_archive),
                destination_archive.title))

        for copy in copies:
            messages.append('<br/>%s' % copy.displayname)

        notification = "\n".join(messages)
        self.request.response.addNotification(structured(notification))


class ArchiveEditDependenciesView(ArchiveViewBase, LaunchpadFormView):
    """Archive dependencies view class."""

    schema = IArchiveEditDependenciesForm

    custom_widget('selected_dependencies', LabeledMultiCheckBoxWidget)

    def setUpFields(self):
        """Override `LaunchpadFormView`.

        In addition to setting schema fields, also initialize the
        'selected_dependencies' field.

        See `createSelectedSourcesField` method.
        """
        LaunchpadFormView.setUpFields(self)

        self.form_fields = (
            self.createSelectedDependenciesField() + self.form_fields)

    def focusedElementScript(self):
        """Override `LaunchpadFormView`.

        Move focus to the 'dependency_candidate' input field when there is
        no recorded dependency to present. Otherwise it will default to
        the first recorded dependency checkbox.
        """
        if not self.has_dependencies:
            self.initial_focus_widget = "dependency_candidate"
        return LaunchpadFormView.focusedElementScript(self)

    def createSelectedDependenciesField(self):
        """Creates the 'selected_dependencies' field.

        'selected_dependencies' is a list of elements of a vocabulary
        containing all the current recorded dependencies for the context
        PPA.
        """
        terms = []
        for archive_dependency in self.context.dependencies:
            dependency = archive_dependency.dependency
            dependency_label = '<a href="%s">%s</a>' % (
                canonical_url(dependency), dependency.title)
            term = SimpleTerm(
                dependency, dependency.owner.name, dependency_label)
            terms.append(term)
        return form.Fields(
            List(__name__='selected_dependencies',
                 title=_('Recorded dependencies'),
                 value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                 required=False,
                 default=[],
                 description=_(
                    'Select one or more dependencies to be removed.')),
            custom_widget=self.custom_widgets['selected_dependencies'])

    def refreshSelectedDependenciesWidget(self):
        """Refresh 'selected_dependencies' widget.

        It's called after removals or additions to present up-to-date results.
        """
        flush_database_caches()
        self.form_fields = self.form_fields.omit('selected_dependencies')
        self.form_fields = (
            self.createSelectedDependenciesField() + self.form_fields)
        self.widgets = form.setUpWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)

    @cachedproperty
    def has_dependencies(self):
        """Whether or not the PPA has recorded dependencies."""
        return bool(self.context.dependencies)

    def validate_remove(self, action, data):
        """Validate dependency removal parameters.

        Ensure we have at least one dependency selected.
        """
        form.getWidgetsData(self.widgets, 'field', data)

        if len(data.get('selected_dependencies', [])) == 0:
            self.setFieldError(
                'selected_dependencies', 'No dependencies selected.')

    @action(_("Remove Dependencies"), name="remove",
            validator="validate_remove")
    def action_remove(self, action, data):
        """Perform the removal of the selected dependencies."""
        if len(self.errors) != 0:
            return

        selected_dependencies = data.get('selected_dependencies')

        # Perform deletion of the source and its binaries.
        for dependency in selected_dependencies:
            self.context.removeArchiveDependency(dependency)

        self.refreshSelectedDependenciesWidget()

        # Present a page notification describing the action.
        messages = []
        messages.append('<p>Dependencies removed:')
        for dependency in selected_dependencies:
            messages.append('<br/>%s' % dependency.title)
        messages.append('</p>')
        notification = "\n".join(messages)
        self.request.response.addNotification(structured(notification))

    def validate_add(self, action, data):
        """Validate 'add dependency' parameters.

        Ensure the following conditions

         * The dependency_candidate exists (was chosen by the user);
         * The dependency_candidate is not the context PPA (recursive);
         * The dependency_candidate is not yet recorded (duplication).

        A error message is rendered if any of those checks fails.
        """
        form.getWidgetsData(self.widgets, 'field', data)

        dependency_candidate = data.get('dependency_candidate')
        if dependency_candidate is None:
            self.setFieldError(
                'dependency_candidate', 'Choose one dependency to add.')
            return

        if dependency_candidate == self.context:
            self.setFieldError('dependency_candidate',
                               "An archive should not depend on itself.")
            return

        if self.context.getArchiveDependency(dependency_candidate):
            self.setFieldError('dependency_candidate',
                               "This dependency is already recorded.")
            return

    @action(_("Add Dependency"), name="add", validator="validate_add")
    def action_add(self, action, data):
        """Record the selected dependency."""
        if len(self.errors) != 0:
            return

        dependency_candidate = data.get('dependency_candidate')
        self.context.addArchiveDependency(dependency_candidate)
        self.refreshSelectedDependenciesWidget()

        self.request.response.addNotification(
            structured(
                '<p>Dependency added: %s</p>' % dependency_candidate.title))


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


class ArchiveBuildsView(ArchiveViewBase, BuildRecordsView):
    """Build Records View for IArchive."""

    __used_for__ = IHasBuildRecords

    @property
    def default_build_state(self):
        """See `IBuildRecordsView`.

        Present NEEDSBUILD build records by default for PPAs.
        """
        return BuildStatus.NEEDSBUILD


class BaseArchiveEditView(ArchiveViewBase, LaunchpadEditFormView):

    schema = IArchive
    field_names = []

    @action(_("Save"), name="save", validator="validate_save")
    def action_save(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self.next_url = canonical_url(self.context)

    def validate_save(self, action, data):
        """Default save validation does nothing."""
        pass

class ArchiveEditView(BaseArchiveEditView):

    field_names = ['description', 'whiteboard']
    custom_widget(
        'description', TextAreaWidget, height=10, width=30)


class ArchiveAdminView(BaseArchiveEditView):

    field_names = ['enabled', 'private', 'require_virtualized',
                   'buildd_secret', 'authorized_size', 'whiteboard']
    custom_widget(
        'whiteboard', TextAreaWidget, height=10, width=30)

    def validate_save(self, action, data):
        """Validate the save action on ArchiveAdminView.

        buildd_secret can only be set, and must be set, when
        this is a private archive.
        """
        form.getWidgetsData(self.widgets, 'field', data)

        if data.get('buildd_secret') is None and data['private']:
            self.setFieldError(
                'buildd_secret',
                'Required for private archives.')

        if data.get('buildd_secret') is not None and not data['private']:
            self.setFieldError(
                'buildd_secret',
                'Do not specify for non-private archives')


def archive_to_structuralheading(archive):
    """Adapts an `IArchive` into an `IStructuralHeaderPresentation`."""
    if archive.owner is not None:
        return IStructuralHeaderPresentation(archive.owner)
    else:
        return IStructuralHeaderPresentation(archive.distribution)

