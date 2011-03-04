# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes related to `IDistroSeries`."""

__metaclass__ = type

__all__ = [
    'DistroSeriesAddView',
    'DistroSeriesAdminView',
    'DistroSeriesBreadcrumb',
    'DistroSeriesEditView',
    'DistroSeriesFacets',
    'DistroSeriesInitializeView',
    'DistroSeriesLocalDifferences',
    'DistroSeriesNavigation',
    'DistroSeriesPackageSearchView',
    'DistroSeriesPackagesView',
    'DistroSeriesView',
    ]

from datetime import datetime

from pytz import utc
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.interface import (
    alsoProvides,
    Interface,
    )
from zope.lifecycleevent import ObjectCreatedEvent
from zope.schema import (
    Bool,
    Choice,
    List,
    )
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.database.constants import UTC_NOW
from canonical.launchpad import (
    _,
    helpers,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchBag
from canonical.launchpad.webapp import (
    action,
    custom_widget,
    GetitemNavigation,
    StandardLaunchpadFacets,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.menu import (
    ApplicationMenu,
    enabled_with_permission,
    Link,
    NavigationMenu,
    )
from canonical.launchpad.webapp.publisher import (
    canonical_url,
    LaunchpadView,
    stepthrough,
    stepto,
    )
from lp.app.browser.launchpadform import (
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.app.errors import NotFoundError
from lp.app.widgets.itemswidgets import (
    CheckBoxMatrixWidget,
    LabeledMultiCheckBoxWidget,
    LaunchpadBooleanRadioWidget,
    LaunchpadDropdownWidget,
    )
from lp.blueprints.browser.specificationtarget import (
    HasSpecificationsMenuMixin,
    )
from lp.bugs.browser.bugtask import BugTargetTraversalMixin
from lp.bugs.browser.structuralsubscription import (
    StructuralSubscriptionMenuMixin,
    StructuralSubscriptionTargetTraversalMixin,
    )
from lp.registry.browser import MilestoneOverlayMixin
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import (
    IDistroSeries,
    IDistroSeriesSet,
    )
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceSource,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.vocabularies import DistroSeriesVocabulary
from lp.services.features import getFeatureFlag
from lp.services.propertycache import cachedproperty
from lp.services.worlddata.interfaces.country import ICountry
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.soyuz.browser.packagesearch import PackageSearchViewBase
from lp.soyuz.interfaces.queue import IPackageUploadSet
from lp.translations.browser.distroseries import (
    check_distroseries_translations_viewable,
    )


class DistroSeriesNavigation(GetitemNavigation, BugTargetTraversalMixin,
    StructuralSubscriptionTargetTraversalMixin):

    usedfor = IDistroSeries

    @stepthrough('+lang')
    def traverse_lang(self, langcode):
        """Retrieve the DistroSeriesLanguage or a dummy if one it is None."""
        # We do not want users to see the 'en' pofile because
        # we store the messages we want to translate as English.
        if langcode == 'en':
            raise NotFoundError(langcode)

        langset = getUtility(ILanguageSet)
        try:
            lang = langset[langcode]
        except IndexError:
            # Unknown language code.
            raise NotFoundError

        distroserieslang = self.context.getDistroSeriesLanguageOrDummy(lang)

        # Check if user is able to view the translations for
        # this distribution series language.
        # If not, raise TranslationUnavailable.
        check_distroseries_translations_viewable(self.context)

        return distroserieslang

    @stepthrough('+source')
    def source(self, name):
        return self.context.getSourcePackage(name)

    # sabdfl 17/10/05 please keep this old location here for
    # LaunchpadIntegration on Breezy, unless you can figure out how to
    # redirect to the newer +source, defined above
    @stepthrough('+sources')
    def sources(self, name):
        return self.context.getSourcePackage(name)

    @stepthrough('+package')
    def package(self, name):
        return self.context.getBinaryPackage(name)

    @stepto('+latest-full-language-pack')
    def latest_full_language_pack(self):
        if self.context.last_full_language_pack_exported is None:
            return None
        else:
            return self.context.last_full_language_pack_exported.file

    @stepto('+latest-delta-language-pack')
    def redirect_latest_delta_language_pack(self):
        if self.context.last_delta_language_pack_exported is None:
            return None
        else:
            return self.context.last_delta_language_pack_exported.file

    @stepthrough('+upload')
    def traverse_queue(self, id):
        return getUtility(IPackageUploadSet).get(id)

    @stepthrough('+difference')
    def traverse_difference(self, name):
        dsd_source = getUtility(IDistroSeriesDifferenceSource)
        return dsd_source.getByDistroSeriesAndName(self.context, name)


class DistroSeriesBreadcrumb(Breadcrumb):
    """Builds a breadcrumb for an `IDistroSeries`."""

    @property
    def text(self):
        return self.context.named_version


class DistroSeriesFacets(StandardLaunchpadFacets):

    usedfor = IDistroSeries
    enable_only = ['overview', 'branches', 'bugs', 'specifications',
                   'translations']


class DistroSeriesOverviewMenu(
    ApplicationMenu, StructuralSubscriptionMenuMixin):

    usedfor = IDistroSeries
    facet = 'overview'
    links = ['edit', 'reassign', 'driver', 'answers',
             'packaging', 'needs_packaging', 'builds', 'queue',
             'add_port', 'create_milestone', 'subscribe', 'admin']

    @enabled_with_permission('launchpad.Admin')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals for this series'
        return Link('+driver', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def reassign(self):
        text = 'Change registrant'
        return Link('+reassign', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def create_milestone(self):
        text = 'Create milestone'
        summary = 'Register a new milestone for this series'
        return Link('+addmilestone', text, summary, icon='add')

    def packaging(self):
        text = 'All upstream links'
        summary = 'A listing of source packages and their upstream projects'
        return Link('+packaging', text, summary=summary, icon='info')

    def needs_packaging(self):
        text = 'Needs upstream links'
        summary = 'A listing of source packages without upstream projects'
        return Link('+needs-packaging', text, summary=summary, icon='info')

    # A search link isn't needed because the distro series overview
    # has a search form.
    def answers(self):
        text = 'Ask a question'
        url = canonical_url(self.context.distribution) + '/+addquestion'
        return Link(url, text, icon='add')

    @enabled_with_permission('launchpad.Admin')
    def add_port(self):
        text = 'Add architecture'
        return Link('+addport', text, icon='add')

    @enabled_with_permission('launchpad.Moderate')
    def admin(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')

    def builds(self):
        text = 'Show builds'
        return Link('+builds', text, icon='info')

    def queue(self):
        text = 'Show uploads'
        return Link('+queue', text, icon='info')


class DistroSeriesBugsMenu(ApplicationMenu, StructuralSubscriptionMenuMixin):

    usedfor = IDistroSeries
    facet = 'bugs'
    links = (
        'cve',
        'nominations',
        'subscribe',
        )

    def cve(self):
        return Link('+cve', 'CVE reports', icon='cve')

    def nominations(self):
        return Link('+nominations', 'Review nominations', icon='bug')


class DistroSeriesSpecificationsMenu(NavigationMenu,
                                     HasSpecificationsMenuMixin):

    usedfor = IDistroSeries
    facet = 'specifications'
    links = [
        'listall', 'listdeclined', 'assignments', 'setgoals',
        'new', 'register_sprint']


class DistroSeriesPackageSearchView(PackageSearchViewBase):
    """Customised PackageSearchView for DistroSeries"""

    def contextSpecificSearch(self):
        """See `AbstractPackageSearchView`."""
        return self.context.searchPackages(self.text)

    label = 'Search packages'


class SeriesStatusMixin:
    """A mixin that provides status field support."""

    def createStatusField(self):
        """Create the 'status' field.

        Create the status vocabulary according the current distroseries
        status:
         * stable   -> CURRENT, SUPPORTED, OBSOLETE
         * unstable -> EXPERIMENTAL, DEVELOPMENT, FROZEN, FUTURE, CURRENT
        """
        stable_status = (
            SeriesStatus.CURRENT,
            SeriesStatus.SUPPORTED,
            SeriesStatus.OBSOLETE,
            )

        if self.context.status not in stable_status:
            terms = [status for status in SeriesStatus.items
                     if status not in stable_status]
            terms.append(SeriesStatus.CURRENT)
        else:
            terms = stable_status

        status_vocabulary = SimpleVocabulary(
            [SimpleTerm(item, item.name, item.title) for item in terms])

        return form.Fields(
            Choice(__name__='status',
                   title=_('Status'),
                   default=self.context.status,
                   vocabulary=status_vocabulary,
                   description=_("Select the distroseries status."),
                   required=True))

    def updateDateReleased(self, status):
        """Update the datereleased field if the status is set to CURRENT."""
        if (self.context.datereleased is None and
            status == SeriesStatus.CURRENT):
            self.context.datereleased = UTC_NOW


class DistroSeriesView(MilestoneOverlayMixin):

    def initialize(self):
        self.displayname = '%s %s' % (
            self.context.distribution.displayname,
            self.context.version)

    @property
    def page_title(self):
        """Return the HTML page title."""
        return '%s %s in Launchpad' % (
        self.context.distribution.title, self.context.version)

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def redirectToDistroFileBug(self):
        """Redirect to the distribution's filebug page.

        Filing a bug on a distribution series is not directly
        permitted; we redirect to the distribution's file
        """
        distro_url = canonical_url(
            self.context.distribution, view_name='+filebug')
        if self.request.form.get('no-redirect') is not None:
            distro_url += '?no-redirect'
        return self.request.response.redirect(distro_url)

    @cachedproperty
    def num_linked_packages(self):
        """The number of linked packagings for this distroseries."""
        return self.context.packagings.count()

    @property
    def num_unlinked_packages(self):
        """The number of unlinked packagings for this distroseries."""
        return self.context.sourcecount - self.num_linked_packages

    @cachedproperty
    def recently_linked(self):
        """Return the packages that were most recently linked upstream."""
        return self.context.getMostRecentlyLinkedPackagings()

    @cachedproperty
    def needs_linking(self):
        """Return a list of 10 packages most in need of upstream linking."""
        # XXX sinzui 2010-02-26 bug=528648: This method causes a timeout.
        # return self.context.getPrioritizedUnlinkedSourcePackages()[:10]
        return None

    milestone_can_release = False

    @cachedproperty
    def milestone_batch_navigator(self):
        return BatchNavigator(self.context.all_milestones, self.request)


class DistroSeriesEditView(LaunchpadEditFormView, SeriesStatusMixin):
    """View class that lets you edit a DistroSeries object.

    It redirects to the main distroseries page after a successful edit.
    """
    schema = IDistroSeries
    field_names = ['displayname', 'title', 'summary', 'description']
    custom_widget('status', LaunchpadDropdownWidget)

    @property
    def label(self):
        """See `LaunchpadFormView`."""
        return 'Edit %s details' % self.context.title

    @property
    def page_title(self):
        """The page title."""
        return self.label

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    def setUpFields(self):
        """See `LaunchpadFormView`.

        In addition to setting schema fields, also initialize the
        'status' field. See `createStatusField` method.
        """
        LaunchpadEditFormView.setUpFields(self)
        is_derivitive = not self.context.distribution.full_functionality
        has_admin = check_permission('launchpad.Admin', self.context)
        if has_admin or is_derivitive:
            # The user is an admin or this is an IDerivativeDistribution.
            self.form_fields = (
                self.form_fields + self.createStatusField())

    @action("Change")
    def change_action(self, action, data):
        """Update the context and redirects to its overviw page."""
        if not self.context.distribution.full_functionality:
            self.updateDateReleased(data.get('status'))
        self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            'Your changes have been applied.')
        self.next_url = canonical_url(self.context)


class DistroSeriesAdminView(LaunchpadEditFormView, SeriesStatusMixin):
    """View class for administering a DistroSeries object.

    It redirects to the main distroseries page after a successful edit.
    """
    schema = IDistroSeries
    field_names = ['name', 'version', 'changeslist']
    custom_widget('status', LaunchpadDropdownWidget)

    @property
    def label(self):
        """See `LaunchpadFormView`."""
        return 'Administer %s' % self.context.title

    @property
    def page_title(self):
        """The page title."""
        return self.label

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    def setUpFields(self):
        """Override `LaunchpadFormView`.

        In addition to setting schema fields, also initialize the
        'status' field. See `createStatusField` method.
        """
        LaunchpadEditFormView.setUpFields(self)
        self.form_fields = (
            self.form_fields + self.createStatusField())

    @action("Change")
    def change_action(self, action, data):
        """Update the context and redirects to its overviw page.

        Also, set 'datereleased' when a unstable distroseries is made
        CURRENT.
        """
        self.updateDateReleased(data.get('status'))
        self.updateContextFromData(data)

        self.request.response.addInfoNotification(
            'Your changes have been applied.')
        self.next_url = canonical_url(self.context)


class DistroSeriesAddView(LaunchpadFormView):
    """A view to create an `IDistroSeries`."""
    schema = IDistroSeries
    field_names = [
        'name', 'displayname', 'title', 'summary', 'description', 'version',
        'parent_series']

    label = 'Register a series'
    page_title = label

    @action(_('Create Series'), name='create')
    def createAndAdd(self, action, data):
        """Create and add a new Distribution Series"""
        owner = getUtility(ILaunchBag).user

        assert owner is not None
        distroseries = self.context.newSeries(
            name=data['name'],
            displayname=data['displayname'],
            title=data['title'],
            summary=data['summary'],
            description=data['description'],
            version=data['version'],
            parent_series=data['parent_series'],
            owner=owner)
        notify(ObjectCreatedEvent(distroseries))
        self.next_url = canonical_url(distroseries)
        return distroseries

    @property
    def cancel_url(self):
        return canonical_url(self.context)


def derived_from_series_source(context):
    """A vocabulary source for series to derive from.

    Once a distribution has a series that has derived from a series in another
    distribution, all other derived series must also derive from a series in
    the same distribution.

    A distribution can have non-derived series. Any of these can be changed to
    derived at a later date, but as soon as this happens, the above rule
    applies.

    It is permissible for a distribution to have both derived and non-derived
    series at the same time.
    """
    all_serieses = getUtility(IDistroSeriesSet).search()
    context_serieses = set(IDistribution(context))
    if len(context_serieses) == 0:
        # Derive from any series.
        serieses = set(all_serieses)
    else:
        for series in context_serieses:
            if (series.parent_series is not None and
                series.parent_series not in context_serieses):
                # Derive only from series in the same distribution as other
                # derived series in this distribution.
                serieses = set(series.parent_series.distribution)
                break
        else:
            # Derive from any series, except those in this distribution.
            serieses = set(all_serieses) - context_serieses
    # Sort the series before generating the vocabulary. We want newest series
    # first so we must compose the key with the difference from a reference
    # date to the creation date.
    reference = datetime.now(utc)
    serieses = sorted(
        serieses, key=lambda series: (
            series.distribution.displayname,
            reference - series.date_created))
    return SimpleVocabulary(
        [DistroSeriesVocabulary.toTerm(series) for series in serieses])

alsoProvides(derived_from_series_source, IContextSourceBinder)


class IDistroSeriesInitializeForm(IDistroSeries):

    derived_from_series = Choice(
        title=_('Derived from distribution series'),
        default=None,
        source=derived_from_series_source,
        description=_(
            "Select the distribution series you "
            "want to derive from."),
        required=True)

    all_architectures = Bool(
        title=_('Architectures to initialize'),
        default=True,
        required=True)

    rebuild = Bool(
        title=_('Copy options'),
        description=_(
            "Choose whether to rebuild all the sources "
            "copied from the parent, or to copy their "
            "binaries."),
        default=False,
        required=True)


class DistroSeriesInitializeView(LaunchpadFormView):
    """A view to initialize an `IDistroSeries`."""

    schema = IDistroSeriesInitializeForm
    field_names = [
        "derived_from_series",
        ]

    custom_widget('derived_from_series', LaunchpadDropdownWidget)
    custom_widget(
        'all_architectures', LaunchpadBooleanRadioWidget,
        true_label='Use all architectures in parent series',
        false_label='Specify architectures below')
    custom_widget('architectures', CheckBoxMatrixWidget, column_count=5)
    custom_widget(
        'all_packagesets', LaunchpadBooleanRadioWidget,
        true_label='Copy all packagesets in parent series',
        false_label='Specify packagesets below')
    custom_widget('packagesets', CheckBoxMatrixWidget, column_count=5)
    custom_widget(
        'rebuild', LaunchpadBooleanRadioWidget,
        true_label='Copy source and rebuild',
        false_label='Copy source and binaries')

    label = 'Initialize series'
    page_title = label

    @action(_('Commence initialization'), name='initialize')
    def initialize_series(self, action, data):
        """Initialize the Distribution Series."""
        owner = getUtility(ILaunchBag).user
        assert owner is not None

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url


class DistroSeriesPackagesView(LaunchpadView):
    """A View to show series package to upstream package relationships."""

    label = 'All series packages linked to upstream project series'
    page_title = 'All upstream links'

    @cachedproperty
    def cached_packagings(self):
        """The batched upstream packaging links."""
        packagings = self.context.getPrioritizedPackagings()
        navigator = BatchNavigator(packagings, self.request, size=20)
        navigator.setHeadings('packaging', 'packagings')
        return navigator


class DistroSeriesNeedsPackagesView(LaunchpadView):
    """A View to show series package to upstream package relationships."""

    label = 'Packages that need upstream packaging links'
    page_title = 'Needs upstream links'

    @cachedproperty
    def cached_unlinked_packages(self):
        """The batched `ISourcePackage`s that needs packaging links."""
        packages = self.context.getPrioritizedUnlinkedSourcePackages()
        navigator = BatchNavigator(packages, self.request, size=20)
        navigator.setHeadings('package', 'packages')
        return navigator


class IDifferencesFormSchema(Interface):
    selected_differences = List(
        title=_('Selected differences'),
        value_type=Choice(vocabulary=SimpleVocabulary([])),
        description=_("Select the differences for syncing."),
        required=True)


class DistroSeriesLocalDifferences(LaunchpadFormView):
    """Present differences between a derived series and its parent."""
    schema = IDifferencesFormSchema
    custom_widget('selected_differences', LabeledMultiCheckBoxWidget)

    page_title = 'Local package differences'

    def initialize(self):
        """Redirect to the derived series if the feature is not enabled."""
        if not getFeatureFlag('soyuz.derived-series-ui.enabled'):
            self.request.response.redirect(canonical_url(self.context))
            return

        # Update the label for sync action.
        self.__class__.actions.byname['actions.sync'].label = (
            "Sync Selected %s Versions into %s" % (
                self.context.parent_series.displayname,
                self.context.displayname,
                ))
        super(DistroSeriesLocalDifferences, self).initialize()

    @property
    def label(self):
        return (
            "Source package differences between '%s' and "
            "parent series '%s'" % (
                self.context.displayname,
                self.context.parent_series.displayname,
                ))

    @cachedproperty
    def cached_differences(self):
        """Return a batch navigator of potentially filtered results."""
        utility = getUtility(IDistroSeriesDifferenceSource)
        differences = utility.getForDistroSeries(self.context)
        return BatchNavigator(differences, self.request)

    def setUpFields(self):
        """Add the selected differences field.

        As this field depends on other search/filtering field values
        for its own vocabulary, we set it up after all the others.
        """
        super(DistroSeriesLocalDifferences, self).setUpFields()
        check_permission('launchpad.Edit', self.context)
        terms = [
            SimpleTerm(diff, diff.source_package_name.name,
                diff.source_package_name.name)
                for diff in self.cached_differences.batch]
        diffs_vocabulary = SimpleVocabulary(terms)
        choice = self.form_fields['selected_differences'].field.value_type
        choice.vocabulary = diffs_vocabulary

    @action(_("Sync Sources"), name="sync", validator='validate_sync',
            condition='canPerformSync')
    def sync_sources(self, action, data):
        """Mark the diffs as syncing and request the sync.

        Currently this is a stub operation, the details of which will
        be implemented later.
        """
        selected_differences = data['selected_differences']
        diffs = [
            diff.source_package_name.name
                for diff in selected_differences]

        self.request.response.addNotification(
            "The following sources would have been synced if this "
            "wasn't just a stub operation: " + ", ".join(diffs))

        self.next_url = self.request.URL

    def validate_sync(self, action, data):
        """Validate selected differences."""
        form.getWidgetsData(self.widgets, self.prefix, data)

        if len(data.get('selected_differences', [])) == 0:
            self.setFieldError(
                'selected_differences', 'No differences selected.')

    def canPerformSync(self, *args):
        """Return whether a sync can be performed.

        This method is used as a condition for the above sync action, as
        well as directly in the template.
        """
        return check_permission('launchpad.Edit', self.context)
