# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for archive."""

__metaclass__ = type

__all__ = [
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
    'traverse_archive',
    ]


import urllib

from zope.app.form.browser import TextAreaWidget
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.component import getUtility
from zope.formlib import form
from zope.interface import implements
from zope.schema import Choice, List
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.sourceslist import (
    SourcesListEntries, SourcesListEntriesView)
from canonical.launchpad.browser.librarian import FileNavigationMixin
from canonical.launchpad.components.archivesourcepublication import (
    ArchiveSourcePublications)
from canonical.launchpad.interfaces.archive import (
    ArchivePurpose, CannotCopy, IArchive, IArchiveEditDependenciesForm,
    IArchivePackageCopyingForm, IArchivePackageDeletionForm,
    IArchiveSet, IArchiveSourceSelectionForm, IPPAActivateForm)
from canonical.launchpad.interfaces.archivepermission import (
    ArchivePermissionType, IArchivePermissionSet)
from canonical.launchpad.interfaces.build import (
    BuildStatus, IBuildSet, IHasBuildRecords)
from canonical.launchpad.interfaces.component import IComponentSet
from canonical.launchpad.interfaces.distroseries import DistroSeriesStatus
from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities, NotFoundError)
from canonical.launchpad.interfaces.packagecopyrequest import (
    IPackageCopyRequestSet)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.publishing import (
    PackagePublishingPocket, active_publishing_status,
    inactive_publishing_status, IPublishingSet)
from canonical.launchpad.interfaces.sourcepackagename import (
    ISourcePackageNameSet)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, enabled_with_permission,
    stepthrough, ContextMenu, LaunchpadEditFormView,
    LaunchpadFormView, LaunchpadView, Link, Navigation)
from canonical.launchpad.scripts.packagecopier import (
    check_copy, do_copy)
from canonical.launchpad.webapp.badge import HasBadgeBase
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.menu import structured
from canonical.widgets import (
    LabeledMultiCheckBoxWidget, PlainMultiCheckBoxWidget)
from canonical.widgets.itemswidgets import (
    LaunchpadDropdownWidget, LaunchpadRadioWidget)
from canonical.widgets.textwidgets import StrippedTextWidget


def construct_redirect_params(data):
    '''Get part of the URL needed for package copy/delete page redirection.

    After an archive package copy/delete request concludes we need to
    redirect to the same page while preserving any context that the
    user may have established.

    The context that needs to be preserved is comprised of the name and the
    publishing status filter variables (which are part of the original POST
    request data).

    :param data: POST request data passed to the original package
        copy/delete request, contains the name and the publishing status
        filter values.

    :return: a part of the URL needed to redirect to the same page (the
        encoded HTTP GET parameters)
    '''
    url_params_string = ''
    url_params = dict()

    # Handle the name filter if set.
    name_filter = data.get('name_filter')
    if name_filter is not None:
        url_params['field.name_filter'] = name_filter

    # Handle the publishing status filter which must be one of: any,
    # published or superseded.
    status_filter = data.get('status_filter')
    if status_filter is not None:
        # Please note: the default value is 'any'.
        status_filter_value = 'any'

        # Was the status filter perhaps set to published or superseded?
        if status_filter.collection is not None:
            # The collection property is of type archive.StatusCollection,
            # we just want to figure out whether it contains either a
            # published or superseded status however.
            status_filter_string = str(status_filter.collection)
            terms_sought = ('Published', 'Superseded')
            for term in terms_sought:
                if term in status_filter_string:
                    status_filter_value = term.lower()
                    break
        url_params['field.status_filter'] = status_filter_value

    if url_params:
        url_params_string = '?%s' % urllib.urlencode(url_params)

    return url_params_string


class ArchiveBadges(HasBadgeBase):
    """Provides `IHasBadges` for `IArchive`."""

    def getPrivateBadgeTitle(self):
        """Return private badge info useful for a tooltip."""
        return "This archive is private."


def traverse_archive(distribution, name):
    """For distribution archives, traverse to the right place.

    This traversal only applies to distribution archives, not PPAs.

    :param name: The name of the archive, e.g. 'partner'
    """
    archive = getUtility(
        IArchiveSet).getByDistroAndName(distribution, name)
    if archive is None:
        return NotFoundError(name)
    else:
        return archive


class ArchiveURL:
    """Dynamic URL declaration for `IDistributionArchive`.

    When dealing with distribution archives we want to present them under
    IDistribution as /<distro>/+archive/<name>, for example:
    /ubuntu/+archive/partner
    """
    implements(ICanonicalUrlData)
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def inside(self):
        return self.context.distribution

    @property
    def path(self):
        return u"+archive/%s" % self.context.name.lower()


class ArchiveNavigation(Navigation, FileNavigationMixin):
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

    @stepthrough('+sourcepub')
    def traverse_sourcepub(self, name):
        try:
            pub_id = int(name)
        except ValueError:
            return None

        # The ID is not enough on its own to identify the publication,
        # we need to make sure it matches the context archive as well.
        results = getUtility(IPublishingSet).getByIdAndArchive(
            pub_id, self.context)
        if results.count() == 1:
            return results[0]

        return None

    @stepthrough('+upload')
    def traverse_upload_permission(self, name):
        """Traverse the data part of the URL for upload permissions."""
        return self._traverse_permission(name, ArchivePermissionType.UPLOAD)

    @stepthrough('+queue-admin')
    def traverse_queue_admin_permission(self, name):
        """Traverse the data part of the URL for queue admin permissions."""
        return self._traverse_permission(
            name, ArchivePermissionType.QUEUE_ADMIN)

    def _traverse_permission(self, name, permission_type):
        """Traversal helper function.

        The data part ("name") is a compound value of the format:
        user.item
        where item is a component or a source package name,
        """
        username, item = name.split(".", 1)
        user = getUtility(IPersonSet).getByName(username)
        if user is None:
            return None

        # See if "item" is a component name.
        try:
            component = getUtility(IComponentSet)[item]
        except NotFoundError:
            pass
        else:
            return getUtility(IArchivePermissionSet).checkAuthenticated(
                user, self.context, permission_type, component)[0]

        # See if "item" is a source package name.
        package = getUtility(ISourcePackageNameSet).queryByName(item)
        if package is not None:
            return getUtility(IArchivePermissionSet).checkAuthenticated(
                user, self.context, permission_type, package)[0]
        else:
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
        """Display a delete menu option for non-copy archives."""
        text = 'Delete packages'
        link = Link('+delete-packages', text, icon='edit')

        # This link should not be available for copy archives.
        if self.context.is_copy:
            link.enabled = False
        return link

    @enabled_with_permission('launchpad.AnyPerson')
    def copy(self):
        """Display a copy menu option for non-copy archives."""
        text = 'Copy packages'
        link = Link('+copy-packages', text, icon='edit')

        # This link should not be available for copy archives.
        if self.context.is_copy:
            link.enabled = False
        return link

    @enabled_with_permission('launchpad.Edit')
    def edit_dependencies(self):
        text = 'Edit dependencies'
        return Link('+edit-dependencies', text, icon='edit')


class ArchiveViewBase:
    """Common features for Archive view classes."""

    @cachedproperty
    def is_active(self):
        """Whether or not this PPA already have publications in it."""
        # XXX cprov 20080708 bug=246200: use bool() when it gets fixed
        # in storm.
        return self.context.getPublishedSources().count() > 0

    @property
    def source_count_text(self):
        """Return the correct form of the source counter notice."""
        num_sources_published = self.context.number_of_sources_published
        if num_sources_published == 1:
            return '%s source package' % num_sources_published
        else:
            return '%s source packages' % num_sources_published

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

        status_terms = [
            SimpleTerm(StatusCollection(active_publishing_status),
                       'published', 'Published'),
            SimpleTerm(StatusCollection(inactive_publishing_status),
                       'superseded', 'Superseded'),
            SimpleTerm(StatusCollection(), 'any', 'Any Status')
            ]
        return SimpleVocabulary(status_terms)

    @property
    def archive_url(self):
        """Return an archive_url where available, or None."""
        if self.is_active and not self.context.is_copy:
            return self.context.archive_url
        else:
            return None

    @property
    def archive_label(self):
        """Return either 'PPA' or 'Archive' as the label for archives.

        It is desired to use the name 'PPA' for branding reasons where
        appropriate, even though the template logic is the same (and hence
        not worth splitting off into a separate template or macro)
        """
        if self.context.is_ppa:
            return 'PPA'
        else:
            return 'Archive'

    @cachedproperty
    def build_counters(self):
        """Return a dict representation of the build counters."""
        return self.context.getBuildCounters()


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
            self.context.distribution, self.archive_url,
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
        results = list(self.batchnav.currentBatch())
        self.search_results = ArchiveSourcePublications(results)

    @property
    def package_copy_requests(self):
        """Return any package copy requests associated with this archive."""
        return(getUtility(
                IPackageCopyRequestSet).getByTargetArchive(self.context))

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

        # Setup widgets for 'name_filter' and 'status_filter' fields
        # because they are required to build 'selected_sources' field.
        initial_fields = status_field + self.form_fields.select('name_filter')
        # XXX 2008-09-29 gary
        # The setUpWidgets method should not be called here. The re-ordering
        # of the widgets, if needed should be done in setUpWidgets.
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
        # See above XXX for the source of this ugliness. This basically
        # redoes, what the base implementation would do. It should be removed
        # once the setUpFields is fixed.
        for field in self.form_fields:
            if (field.custom_widget is None and
                field.__name__ in self.custom_widgets):
                field.custom_widget = self.custom_widgets[field.__name__]
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

        results = list(self.sources[:self.max_sources_presented])
        for pub in ArchiveSourcePublications(results):
            terms.append(SimpleTerm(pub, str(pub.id), pub.displayname))
        return form.Fields(
            List(__name__='selected_sources',
                 title=_('Available sources'),
                 value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                 required=False,
                 default=[],
                 description=_('Select one or more sources to be submitted '
                               'to an action.')))

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
        # XXX cprov 20080708 bug=246200: use bool() when it gets fixed
        # in storm.
        return available_sources.count() > 0

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
            'Default status_filter should be defined by callsites.')

    def getSources(self, name=None, status=None):
        """Source lookup method, should be implemented by callsites."""
        raise NotImplementedError(
            'Source lookup should be implemented by callsites.')



class ArchivePackageDeletionView(ArchiveSourceSelectionFormView):
    """Archive package deletion view class.

    This view presents a package selection slot in a POST form implementing
    a deletion action that can be performed upon a set of selected packages.
    """

    schema = IArchivePackageDeletionForm

    # Maximum number of 'sources' presented.
    max_sources_presented = 20

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
        publishing_set = getUtility(IPublishingSet)
        publishing_set.requestDeletion(selected_sources, self.user, comment)

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

        url_params_string = construct_redirect_params(data)
        self.next_url = '%s%s' % (self.request.URL, url_params_string)


class DestinationArchiveDropdownWidget(LaunchpadDropdownWidget):
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

    custom_widget('destination_archive', DestinationArchiveDropdownWidget)
    custom_widget('destination_series', DestinationSeriesDropdownWidget)
    custom_widget('include_binaries', LaunchpadRadioWidget)

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
            self.createIncludeBinariesField() +
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
                   required=required))

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
                   required=False))

    def createIncludeBinariesField(self):
        """Create the 'include_binaries' field.

        'include_binaries' widget is a choice, rendered as radio-buttons,
        with two options that provides a Boolean as its value:

         ||      Option     || Value ||
         || REBUILD_SOURCES || False ||
         || COPY_BINARIES   || True  ||

        When omitted in the form, this widget defaults for REBUILD_SOURCES
        option when rendered.
        """
        rebuild_sources = SimpleTerm(
                False, 'REBUILD_SOURCES', _('Rebuild the copied sources'))
        copy_binaries = SimpleTerm(
            True, 'COPY_BINARIES', _('Copy existing binaries'))
        terms = [rebuild_sources, copy_binaries]

        return form.Fields(
            Choice(__name__='include_binaries',
                   title=_('Copy options'),
                   vocabulary=SimpleVocabulary(terms),
                   description=_("How the selected sources should be copied "
                                 "to the destination archive."),
                   missing_value=rebuild_sources,
                   default=False,
                   required=True))

    @action(_("Update"), name="update")
    def action_update(self, action, data):
        """Simply re-issue the form with the new values."""
        pass

    def validate_copy(self, action, data):
        """Validate copy parameters.

        Ensure we have:

         * At least, one source selected;
         * The default series input is not given when copying to the
           context PPA;
         * The select destination fits all selected sources.
        """
        form.getWidgetsData(self.widgets, 'field', data)

        selected_sources = data.get('selected_sources', [])
        destination_archive = data.get('destination_archive')
        destination_series = data.get('destination_series')
        include_binaries = data.get('include_binaries')
        destination_pocket = self.default_pocket

        if len(selected_sources) == 0:
            self.setFieldError('selected_sources', 'No sources selected.')
            return

        broken_copies = []
        for source in selected_sources:
            if destination_series is None:
                destination_series = source.distroseries
            try:
                check_copy(
                    source, destination_archive, destination_series,
                    destination_pocket, include_binaries)
            except CannotCopy, reason:
                broken_copies.append(
                    "%s (%s)" % (source.displayname, reason))

        if len(broken_copies) == 0:
            return

        if len(broken_copies) == 1:
            error_message = (
                "The following source cannot be copied: %s"
                % broken_copies[0])
        else:
            error_message = (
                "The following sources cannot be copied:\n%s" %
                ",\n".join(broken_copies))

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

        copies = do_copy(
            selected_sources, destination_archive, destination_series,
            destination_pocket, include_binaries)

        # Present a page notification describing the action.
        messages = []
        if len(copies) == 0:
            messages.append(
                '<p>All packages already copied to '
                '<a href="%s">%s</a>.</p>' % (
                    canonical_url(destination_archive),
                    destination_archive.title))
        else:
            messages.append(
                '<p>Packages copied to <a href="%s">%s</a>:</p>' % (
                    canonical_url(destination_archive),
                    destination_archive.title))
            messages.append('<ul>')
            messages.append(
                "\n".join(['<li>%s</li>' % copy.displayname
                           for copy in copies]))
            messages.append('</ul>')

        notification = "\n".join(messages)
        self.request.response.addNotification(structured(notification))

        url_params_string = construct_redirect_params(data)
        self.next_url = '%s%s' % (self.request.URL, url_params_string)


class ArchiveEditDependenciesView(ArchiveViewBase, LaunchpadFormView):
    """Archive dependencies view class."""

    schema = IArchiveEditDependenciesForm

    custom_widget('selected_dependencies', PlainMultiCheckBoxWidget,
                  cssClass='line-through-when-checked ppa-dependencies')
    custom_widget('primary_dependencies', LaunchpadRadioWidget,
                  cssClass='highlight-selected')
    custom_widget('primary_components', LaunchpadRadioWidget,
                  cssClass='highlight-selected')

    def initialize(self):
        self.cancel_url = canonical_url(self.context)
        self._messages = []
        LaunchpadFormView.initialize(self)

    def setUpFields(self):
        """Override `LaunchpadFormView`.

        In addition to setting schema fields, also initialize the
        'selected_dependencies' field.

        See `createSelectedSourcesField` method.
        """
        LaunchpadFormView.setUpFields(self)

        self.form_fields = (
            self.createSelectedDependenciesField() +
            self.createPrimaryDependenciesField() +
            self.createPrimaryComponentsField() +
            self.form_fields)

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
            if not dependency.is_ppa:
                continue
            dependency_label = '<a href="%s">%s</a>' % (
                canonical_url(dependency), archive_dependency.title)
            term = SimpleTerm(
                dependency, dependency.owner.name, dependency_label)
            terms.append(term)
        return form.Fields(
            List(__name__='selected_dependencies',
                 title=_('Extra dependencies'),
                 value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                 required=False,
                 default=[],
                 description=_(
                    'Select one or more dependencies to be removed.')))

    def createPrimaryDependenciesField(self):
        """Create the 'primary_dependencies' field.

        'primary_dependency' widget is a choice, rendered as radio-buttons,
        with 5 options that provides `PackagePublishingPocket` as result:

         || Option    || Value     ||
         || Release   || RELEASE   ||
         || Security  || SECURITY  ||
         || Default   || UPDATES   ||
         || Proposed  || PROPOSED  ||
         || Backports || BACKPORTS ||

        When omitted in the form, this widget defaults for 'Default'
        option when rendered.
        """
        release = SimpleTerm(
            PackagePublishingPocket.RELEASE, 'RELEASE',
            _('Basic (only released packages).'))
        security = SimpleTerm(
            PackagePublishingPocket.SECURITY, 'SECURITY',
            _('Security (basic dependencies and important security '
              'updates).'))
        updates = SimpleTerm(
            PackagePublishingPocket.UPDATES, 'UPDATES',
            _('Default (security dependencies and recommended updates).'))
        proposed = SimpleTerm(
            PackagePublishingPocket.PROPOSED, 'PROPOSED',
            _('Proposed (default dependencies and proposed updates).'))
        backports = SimpleTerm(
            PackagePublishingPocket.BACKPORTS, 'BACKPORTS',
            _('Backports (default dependencies and unsupported updates).'))

        terms = [release, security, updates, proposed, backports]

        primary_dependency = self.context.getArchiveDependency(
            self.context.distribution.main_archive)
        if primary_dependency is None:
            default_value = PackagePublishingPocket.UPDATES
        else:
            default_value = primary_dependency.pocket

        primary_dependency_vocabulary = SimpleVocabulary(terms)
        current_term = primary_dependency_vocabulary.getTerm(
            default_value)

        return form.Fields(
            Choice(__name__='primary_dependencies',
                   title=_(
                    "%s dependencies"
                    % self.context.distribution.displayname),
                   vocabulary=primary_dependency_vocabulary,
                   description=_(
                    "Select which packages of the %s primary archive "
                    "should be used as build-dependencies when building "
                    "sources in this PPA."
                    % self.context.distribution.displayname),
                   missing_value=current_term,
                   default=default_value,
                   required=True))

    def createPrimaryComponentsField(self):
        """Create the 'primary_components' field.

        'primary_components' widget is a choice, rendered as radio-buttons,
        with two options that provides an IComponent as its value:

         ||      Option    ||   Value    ||
         || ALL_COMPONENTS || multiverse ||
         || FOLLOW_PRIMARY ||    None    ||

        When omitted in the form, this widget defaults to 'All ubuntu
        components' option when rendered.
        """
        multiverse = getUtility(IComponentSet)['multiverse']

        all_components = SimpleTerm(
            multiverse, 'ALL_COMPONENTS',
            _('Use all %s components available.' %
              self.context.distribution.displayname))
        follow_primary = SimpleTerm(
            None, 'FOLLOW_PRIMARY',
            _('Use the same components used for each source in the %s '
              'primary archive.' % self.context.distribution.displayname))

        primary_dependency = self.context.getArchiveDependency(
            self.context.distribution.main_archive)
        if primary_dependency is not None:
            if primary_dependency.component == multiverse:
                default_value = multiverse
            else:
                default_value = None
        else:
            default_value = multiverse

        terms = [all_components, follow_primary]
        primary_components_vocabulary = SimpleVocabulary(terms)
        current_term = primary_components_vocabulary.getTerm(default_value)

        return form.Fields(
            Choice(__name__='primary_components',
                   title=_('%s components' %
                           self.context.distribution.displayname),
                   vocabulary=primary_components_vocabulary,
                   description=_("Which %s components of the archive pool "
                                 "should be used when fetching build "
                                 "dependencies." %
                                 self.context.distribution.displayname),
                   missing_value=current_term,
                   default=default_value,
                   required=True))

    @cachedproperty
    def has_dependencies(self):
        """Whether or not the PPA has recorded dependencies."""
        # XXX cprov 20080708 bug=246200: use bool() when it gets fixed
        # in storm.
        return self.context.dependencies.count() > 0

    @property
    def messages(self):
        return '\n'.join(self._messages)

    def _remove_dependencies(self, data):
        """Perform the removal of the selected dependencies."""
        selected_dependencies = data.get('selected_dependencies', [])

        if len(selected_dependencies) == 0:
            return

        # Perform deletion of the source and its binaries.
        for dependency in selected_dependencies:
            self.context.removeArchiveDependency(dependency)

        # Present a page notification describing the action.
        self._messages.append('<p>Dependencies removed:')
        for dependency in selected_dependencies:
            self._messages.append('<br/>%s' % dependency.title)
        self._messages.append('</p>')

    def _add_ppa_dependencies(self, data):
        """Record the selected dependency."""
        dependency_candidate = data.get('dependency_candidate')
        if dependency_candidate is None:
            return

        self.context.addArchiveDependency(
            dependency_candidate, PackagePublishingPocket.RELEASE,
            getUtility(IComponentSet)['main'])

        self._messages.append(
            '<p>Dependency added: %s</p>' % dependency_candidate.title)

    def _add_primary_dependencies(self, data):
        """Record the selected dependency."""
        dependency_pocket = data.get('primary_dependencies')
        dependency_component = data.get('primary_components')

        primary_dependency = self.context.getArchiveDependency(
            self.context.distribution.main_archive)
        multiverse = getUtility(IComponentSet)['multiverse']

        if (primary_dependency is None and
            dependency_pocket == PackagePublishingPocket.UPDATES and
            dependency_component == multiverse):
            return
        if (primary_dependency is not None and
            primary_dependency.pocket == dependency_pocket and
            primary_dependency.component == dependency_component):
            return

        # Remove any primary dependencies overrides.
        if primary_dependency is not None:
            self.context.removeArchiveDependency(
                self.context.distribution.main_archive)

        if (dependency_pocket == PackagePublishingPocket.UPDATES and
            dependency_component == multiverse):
            self._messages.append(
                '<p>Default primary dependencies restored.</p>')
            return

        # Install the required primary archive dependency override.
        primary_dependency = self.context.addArchiveDependency(
            self.context.distribution.main_archive, dependency_pocket,
            dependency_component)
        self._messages.append(
            '<p>Primary dependency added: %s</p>' % primary_dependency.title)

    def validate(self, data):
        """Validate dependency configuration changes.

        Skip checks if no dependency candidate was sent in the form.

        Validate if the requested PPA dependency is sane (different than
        the context PPA and not yet registered).

        Also check if the dependency candidate is private, if so, it can
        only be set if the user has 'launchpad.View' permission on it and
        the context PPA is also private (this way P3A credentials will be
        sanitized from buildlogs).
        """
        dependency_candidate = data.get('dependency_candidate')

        if dependency_candidate is None:
            return

        if dependency_candidate == self.context:
            self.setFieldError('dependency_candidate',
                               "An archive should not depend on itself.")
            return

        if self.context.getArchiveDependency(dependency_candidate):
            self.setFieldError('dependency_candidate',
                               "This dependency is already registered.")
            return

        from canonical.launchpad.webapp.authorization import check_permission
        if not check_permission('launchpad.View', dependency_candidate):
            self.setFieldError(
                'dependency_candidate',
                "You don't have permission to use this dependency.")
            return

        if dependency_candidate.private and not self.context.private:
            self.setFieldError(
                'dependency_candidate',
                "Public PPAs cannot depend on private ones.")

    @action(_("Save"), name="save")
    def action_save(self, action, data):
        """Save dependency configuration changes.

        See `_remove_dependencies`, `_add_ppa_dependencies` and
        `_add_primary_dependencies`.

        Redirect to the same page once the form is processed, to avoid widget
        refreshing. And render a page notification with the summary of the
        changes made.
        """
        # Redirect after POST.
        self.next_url = self.request.URL

        # Process the form.
        self._add_primary_dependencies(data)
        self._add_ppa_dependencies(data)
        self._remove_dependencies(data)

        # Issue a notification if anything was changed.
        if len(self.messages) > 0:
            self.request.response.addNotification(
                structured(self.messages))


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
        if self.context.archive is None:
            getUtility(IArchiveSet).new(
                owner=self.context, purpose=ArchivePurpose.PPA,
                description=data['description'], distribution=None)
        self.next_url = canonical_url(self.context.archive)

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
