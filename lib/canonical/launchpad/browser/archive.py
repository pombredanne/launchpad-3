# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for archive."""

__metaclass__ = type

__all__ = [
    'ArchiveAdminView',
    'ArchiveActivateView',
    'ArchiveBadges',
    'ArchiveBreadcrumbBuilder',
    'ArchiveBuildsView',
    'ArchiveContextMenu',
    'ArchiveEditDependenciesView',
    'ArchiveEditView',
    'ArchiveNavigation',
    'ArchiveNavigationMenu',
    'ArchivePackageCopyingView',
    'ArchivePackageDeletionView',
    'ArchiveView',
    'ArchiveViewBase',
    'traverse_distro_archive',
    'traverse_named_ppa',
    ]


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
from canonical.launchpad.components.archivedependencies import (
    default_component_dependency_name, default_pocket_dependency)
from canonical.launchpad.components.archivesourcepublication import (
    ArchiveSourcePublications)
from canonical.launchpad.interfaces.archive import (
    ArchivePurpose, CannotCopy, IArchive, IArchiveEditDependenciesForm,
    IArchivePackageCopyingForm, IArchivePackageDeletionForm,
    IArchiveSet, IArchiveSourceSelectionForm, IPPAActivateForm,
    default_name_by_purpose)
from canonical.launchpad.interfaces.archivepermission import (
    ArchivePermissionType, IArchivePermissionSet)
from canonical.launchpad.interfaces.archivesubscriber import (
    IArchiveSubscriberSet)
from canonical.launchpad.interfaces.build import (
    BuildStatus, IBuildSet)
from canonical.launchpad.interfaces.buildrecords import IHasBuildRecords
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
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.badge import HasBadgeBase
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.menu import structured, NavigationMenu
from canonical.widgets import (
    LabeledMultiCheckBoxWidget, PlainMultiCheckBoxWidget)
from canonical.widgets.itemswidgets import (
    LaunchpadDropdownWidget, LaunchpadRadioWidget)
from canonical.widgets.textwidgets import StrippedTextWidget


class ArchiveBadges(HasBadgeBase):
    """Provides `IHasBadges` for `IArchive`."""

    def getPrivateBadgeTitle(self):
        """Return private badge info useful for a tooltip."""
        return "This archive is private."


def traverse_distro_archive(distribution, name):
    """For distribution archives, traverse to the right place.

    This traversal only applies to distribution archives, not PPAs.

    :param name: The name of the archive, e.g. 'partner'
    """
    archive = getUtility(
        IArchiveSet).getByDistroAndName(distribution, name)
    if archive is None:
        raise NotFoundError(name)

    return archive


def traverse_named_ppa(person_name, ppa_name):
    """For PPAs, traverse the right place.

    :param person_name: The person part of the URL
    :param ppa_name: The PPA name part of the URL
    """
    # For now, all PPAs are assumed to be Ubuntu-related.  This will
    # change when we start doing PPAs for other distros.
    ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    archive_set = getUtility(IArchiveSet)
    archive = archive_set.getPPAByDistributionAndOwnerName(
            ubuntu, person_name, ppa_name)
    if archive is None:
        raise NotFoundError("%s/%s", (person_name, ppa_name))

    return archive


class DistributionArchiveURL:
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
        return u"+archive/%s" % self.context.name


class PPAURL:
    """Dynamic URL declaration for named PPAs."""
    implements(ICanonicalUrlData)
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def inside(self):
        return self.context.owner

    @property
    def path(self):
        return u"+archive/%s" % self.context.name


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

    @stepthrough('+subscriptions')
    def traverse_subscription(self, person_name):
        try:
            person = getUtility(IPersonSet).getByName(person_name)
        except NotFoundError:
            return None

        subscriptions = getUtility(IArchiveSubscriberSet).getBySubscriber(
            person, archive=self.context)

        # If a person is subscribed with a direct subscription as well as
        # via a team, subscriptions will contain both, so need to grab
        # the direct subscription:
        for subscription in subscriptions:
            if subscription.subscriber == person:
                return subscription

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
             'edit_dependencies', 'manage_subscribers']

    def ppa(self):
        text = 'View PPA'
        return Link(canonical_url(self.context), text, icon='info')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer archive'
        return Link('+admin', text, icon='edit')

    @enabled_with_permission('launchpad.Append')
    def manage_subscribers(self):
        text = 'Manage subscriptions'
        link = Link('+subscriptions', text, icon='edit')

        # This link should only be available for private archives:
        if not self.context.private:
            link.enabled = False

        # XXX: noodles 2009-03-10 bug=340405. This link is disabled until
        # the cron-job supporting private archive subscriptions is enabled.
        link.enabled = False

        return link

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


class ArchiveNavigationMenu(NavigationMenu):
    """IArchive navigation menu.

    Deliberately empty.
    """
    usedfor = IArchive
    facet = 'overview'
    links = []


class ArchiveBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IArchive`."""

    @property
    def text(self):
        if self.context.is_ppa:
            default_ppa_name = default_name_by_purpose.get(
                self.context.purpose)
            if self.context.name == default_ppa_name:
                return 'PPA'
            return '%s PPA' % self.context.name

        if self.context.is_copy:
            return '%s Archive Copy' % self.context.name

        return '%s' % self.context.purpose.title


class ArchiveViewBase(LaunchpadView):
    """Common features for Archive view classes."""

    @cachedproperty
    def has_sources(self):
        """Whether or not this PPA has any sources for the view.

        This can be overridden by subclasses as necessary. It allows
        the view to determine whether to display "This PPA does not yet
        have any published sources" or "No sources matching 'blah'."
        """
        # XXX cprov 20080708 bug=246200: use bool() when it gets fixed
        # in storm.
        return self.context.getPublishedSources().count() > 0

    @property
    def source_count_text(self):
        """Return the correct form of the source counter notice."""
        number_of_sources = self.context.number_of_sources
        if number_of_sources == 1:
            return '%s source package' % number_of_sources
        else:
            return '%s source packages' % number_of_sources

    @property
    def binary_count_text(self):
        """Return the correct form of the binary counter notice."""
        number_of_binaries = self.context.number_of_binaries
        if number_of_binaries == 1:
            return '%s binary package' % number_of_binaries
        else:
            return '%s binary packages' % number_of_binaries

    @property
    def archive_url(self):
        """Return an archive_url where available, or None."""
        if self.has_sources and not self.context.is_copy:
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


class ArchiveSourcePackageListViewBase(ArchiveViewBase):
    """Common features for archive views with lists of packages."""

    def initialize(self):
        """Setup package filtering fields.

        Setup status filter widget and the series filter widget.
        """
        self.setupNameFilterWidget()
        self.setupStatusFilterWidget()
        self.setupSeriesFilterWidget()
        self.setupPackageBatchResult()

        # By default, this view will not present selectable sources
        self.selectable_sources = False

        super(ArchiveSourcePackageListViewBase, self).initialize()

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

    @cachedproperty
    def series_vocabulary(self):
        """Return a vocabulary for selecting a distribution series.

        This property defines the _vocabulary_ of a widget that allows the
        selection of a series
        """
        series_terms = [SimpleTerm(None, token='any', title='Any Series')]
        for distroseries in self.context.series_with_sources:
            series_terms.append(
                SimpleTerm(distroseries, token=distroseries.name,
                           title=distroseries.displayname))
        return SimpleVocabulary(series_terms)

    def setupNameFilterWidget(self):
        """Set the specified name filter property."""
        requested_name_filter = self.request.query_string_params.get(
            'field.name_filter')

        self.specified_name_filter = None
        if requested_name_filter is not None:
            self.specified_name_filter = requested_name_filter[0]

    def setupStatusFilterWidget(self):
        """Build a customized publishing status select widget.

        See `status_vocabulary`.
        """
        requested_status_filter = self.request.query_string_params.get(
            'field.status_filter')

        # If the request included a status filter, try to use it:
        self.selected_status_filter = None
        if requested_status_filter is not None:
            self.selected_status_filter = (
                self.simplified_status_vocabulary.getTermByToken(
                    requested_status_filter[0]))

        # If the request didn't include a status, or it was invalid, use
        # the default:
        if self.selected_status_filter is None:
            self.selected_status_filter = self.default_status_filter

        field = Choice(
            __name__='status_filter', title=_("Status Filter"),
            vocabulary=self.simplified_status_vocabulary, required=True)
        setUpWidget(self, 'status_filter', field, IInputWidget)

    @property
    def plain_status_filter_widget(self):
        """Render a <select> control with no <div>s around it."""
        return self.status_filter_widget.renderValue(
            self.selected_status_filter.value)

    def setupSeriesFilterWidget(self):
        """Build a customized archive series select widget.

        Allows users to select between a valid distribution series for the
        archive distribution, or 'Any Series'.
        """
        series_filter = self.request.query_string_params.get(
            'field.series_filter', ['any'])
        self.selected_series_filter = (
            self.series_vocabulary.getTermByToken(series_filter[0]))

        field = Choice(
            __name__='series_filter', title=_("Series Filter"),
            vocabulary=self.series_vocabulary, required=True)
        setUpWidget(self, 'series_filter', field, IInputWidget)

    @property
    def plain_series_filter_widget(self):
        """Render a <select> control with no <div>s around it."""
        return self.series_filter_widget.renderValue(
            self.selected_series_filter.value)

    @cachedproperty
    def filtered_sources(self):
        """Return the source results for display after filtering.

        It expects 'self.selected_status_filter' and 
        'self.selected_series_filter' to be set.
        """
        return self.context.getPublishedSources(
            name=self.specified_name_filter,
            status=self.selected_status_filter.value.collection,
            distroseries=self.selected_series_filter.value)

    @property
    def default_status_filter(self):
        """Return the default status_filter value.

        Subclasses of ArchiveViewBase can override this when required.
        """
        return self.simplified_status_vocabulary.getTermByToken('published')

    def setupPackageBatchResult(self):
        """Setup of the package search results."""
        self.batchnav = BatchNavigator(
            self.filtered_sources, self.request)
        results = list(self.batchnav.currentBatch())
        self.batched_sources = ArchiveSourcePublications(results)

    @cachedproperty
    def has_sources_for_display(self):
        """Whether or not the PPA has any source packages for display.

        This is after any filtering or overriding of the sources() method.
        """
        # XXX cprov 20080708 bug=246200: use bool() when it gets fixed
        # in storm.
        return self.filtered_sources.count() > 0


class ArchiveView(ArchiveSourcePackageListViewBase):
    """Default Archive view class.

    Implements useful actions and collects useful sets for the page template.
    """

    __used_for__ = IArchive

    def initialize(self):
        """Setup infrastructure for the PPA index page.

        Setup sources list entries widget and the search result list.
        """
        if self.context.is_main:
            self.request.response.redirect(
                canonical_url(self.context.distribution))
            return
        super(ArchiveView, self).initialize()
        self.setupSourcesListEntries()

    def setupSourcesListEntries(self):
        """Setup of the sources list entries widget."""
        entries = SourcesListEntries(
            self.context.distribution, self.archive_url,
            self.context.series_with_sources)
        self.sources_list_entries = SourcesListEntriesView(
            entries, self.request)

    @property
    def package_copy_requests(self):
        """Return any package copy requests associated with this archive."""
        return(getUtility(
                IPackageCopyRequestSet).getByTargetArchive(self.context))


class ArchiveSourceSelectionFormView(ArchiveSourcePackageListViewBase,
                                     LaunchpadFormView):
    """Base class to implement a source selection widget for PPAs."""

    schema = IArchiveSourceSelectionForm

    custom_widget('selected_sources', LabeledMultiCheckBoxWidget)

    def initialize(self):
        """Ensure both parent classes initialize methods are called.

        super() ensures this happens in left-to-right order.
        """
        super(ArchiveSourceSelectionFormView, self).initialize()
        self.selectable_sources = True

    def setNextURL(self):
        """Set self.next_url based on current context.

        This should be called during actions of subclasses.
        """
        query_string = self.request.get('QUERY_STRING', '')
        if query_string:
            self.next_url = "%s?%s" % (self.request.URL, query_string)
        else:
            self.next_url = self.request.URL

    def setUpFields(self):
        """Override `LaunchpadFormView`.

        In addition to setting schema fields, also initialize the
        'selected_sources' field.

        See `createSelectedSourcesField` method.
        """
        LaunchpadFormView.setUpFields(self)


        # Build and store 'selected_sources' field.
        selected_sources_field = self.createSelectedSourcesField()

        # Append the just created fields to the global form fields, so
        # `setupWidgets` will do its job.
        self.form_fields += selected_sources_field

    def focusedElementScript(self):
        """Override `LaunchpadFormView`.

        Ensure focus is only set if there are sources actually presented.
        """
        if not self.has_sources_for_display:
            return ''
        return LaunchpadFormView.focusedElementScript(self)

    def createSelectedSourcesField(self):
        """Creates the 'selected_sources' field.

        'selected_sources' is a list of elements of a vocabulary based on
        the source publications that will be presented. This way zope
        infrastructure will do the validation for us.
        """
        terms = []

        for pub in self.batched_sources:
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
    def action_url(self):
        """The forms should post to themselves, including GET params."""
        return "%s?%s" % (self.request.getURL(), self.request['QUERY_STRING'])


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

    @cachedproperty
    def filtered_sources(self):
        """Return the filtered results of publishing records for deletion.

        This overrides ArchiveViewBase.filtered_sources to use a
        different method on the context specific to deletion records.

        It expects 'self.selected_status_filter' and 
        'self.selected_series_filter' to be set.
        """
        return self.context.getSourcesForDeletion(
            name=self.specified_name_filter,
            status=self.selected_status_filter.value.collection,
            distroseries=self.selected_series_filter.value)

    @cachedproperty
    def has_sources(self):
        """Whether or not this PPA has any sources before filtering.

        Overrides the ArchiveViewBase.has_sources
        to ensure that it only returns true if there are sources
        that can be deleted in this archive."
        """
        # XXX cprov 20080708 bug=246200: use bool() when it gets fixed
        # in storm.
        return self.context.getSourcesForDeletion().count() > 0

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

        self.setNextURL()

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

    default_pocket = PackagePublishingPocket.RELEASE

    @property
    def default_status_filter(self):
        """Present published records by default."""
        return self.simplified_status_vocabulary.getTermByToken('published')

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
            terms.append(
                SimpleTerm(ppa, str(ppa.owner.name), ppa.displayname))

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
                    destination_archive.displayname))
        else:
            messages.append(
                '<p>Packages copied to <a href="%s">%s</a>:</p>' % (
                    canonical_url(destination_archive),
                    destination_archive.displayname))
            messages.append('<ul>')
            messages.append(
                "\n".join(['<li>%s</li>' % copy.displayname
                           for copy in copies]))
            messages.append('</ul>')

        notification = "\n".join(messages)
        self.request.response.addNotification(structured(notification))

        self.setNextURL()

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
            default_value = default_pocket_dependency
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
        if primary_dependency is None:
            default_value = getUtility(IComponentSet)[
                default_component_dependency_name]
        else:
            default_value = primary_dependency.component

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
            self._messages.append('<br/>%s' % dependency.displayname)
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
            '<p>Dependency added: %s</p>' % dependency_candidate.displayname)

    def _add_primary_dependencies(self, data):
        """Record the selected dependency."""
        # Received values.
        dependency_pocket = data.get('primary_dependencies')
        dependency_component = data.get('primary_components')

        # Check if the given values correspond to the default scenario
        # for the context archive.
        default_component_dependency = getUtility(IComponentSet)[
            default_component_dependency_name]
        is_default_dependency = (
            dependency_pocket == default_pocket_dependency and
            dependency_component == default_component_dependency)

        primary_dependency = self.context.getArchiveDependency(
            self.context.distribution.main_archive)

        # No action is required if there is no primary_dependency
        # override set and the given values match it.
        if primary_dependency is None and is_default_dependency:
            return

        # Similarly, no action is required if the given values match
        # the existing primary_dependency override.
        if (primary_dependency is not None and
            primary_dependency.pocket == dependency_pocket and
            primary_dependency.component == dependency_component):
            return

        # Remove any primary dependencies overrides.
        if primary_dependency is not None:
            self.context.removeArchiveDependency(
                self.context.distribution.main_archive)

        if is_default_dependency:
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
    """PPA activation view class."""

    schema = IPPAActivateForm
    custom_widget('description', TextAreaWidget, height=3)

    def setUpFields(self):
        """Override `LaunchpadFormView`.

        Reorder the fields in a way the make more sense to users and also
        omit 'name' and present a checkbox for acknowledging the PPA-ToS
        if the user is creating his first PPA.
        """
        LaunchpadFormView.setUpFields(self)

        if self.context.archive is not None:
            self.form_fields = self.form_fields.select(
                'name', 'description')
        else:
            self.form_fields = self.form_fields.select(
                'accepted', 'description')

    def validate(self, data):
        """Ensure user has checked the 'accepted' checkbox."""
        if len(self.errors) > 0:
            return

        default_ppa = self.context.archive

        proposed_name = data.get('name')
        if proposed_name is None and default_ppa is not None:
            self.addError(
                'The default PPA is already activated. Please specify a '
                'name for the new PPA and resubmit the form.')

        # XXX cprov 2009-03-27 bug=188564: We currently only create PPAs
        # for Ubuntu distribution. This check should be revisited when we
        # start supporting PPAs for other distribution (debian, mainly).
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        if proposed_name is not None and proposed_name == ubuntu.name:
            self.setFieldError(
                'name',
                "Archives cannot have the same name as its distribution.")

        if self.context.getPPAByName(proposed_name):
            self.setFieldError(
                'name',
                "You already have a PPA named '%s'." % proposed_name)

        if default_ppa is None and not data.get('accepted'):
            self.setFieldError(
                'accepted',
                "PPA Terms of Service must be accepted to activate a PPA.")

    @action(_("Activate"), name="activate")
    def action_save(self, action, data):
        """Activate a PPA and moves to its page."""

        # 'name' field is omitted from the form data for default PPAs and
        # it's dealt with by IArchive.new(), which will use the default
        # PPA name.
        name = data.get('name', None)

        # XXX cprov 2009-03-27 bug=188564: We currently only create PPAs
        # for Ubuntu distribution. PPA creation should be revisited when we
        # start supporting other distribution (debian, mainly).
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu

        ppa = getUtility(IArchiveSet).new(
            owner=self.context, purpose=ArchivePurpose.PPA,
            distribution=ubuntu, name=name, description=data['description'])
        self.next_url = canonical_url(ppa)


class ArchiveBuildsView(ArchiveViewBase, BuildRecordsView):
    """Build Records View for IArchive."""

    __used_for__ = IHasBuildRecords

    @property
    def default_build_state(self):
        """See `IBuildRecordsView`.

        Present NEEDSBUILD build records by default for PPAs.
        """
        return BuildStatus.NEEDSBUILD


class BaseArchiveEditView(LaunchpadEditFormView, ArchiveViewBase):

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
