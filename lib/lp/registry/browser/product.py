# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for products."""

__metaclass__ = type

__all__ = [
    'ProductAddSeriesView',
    'ProductAddView',
    'ProductAdminView',
    'ProductBrandingView',
    'ProductBugsMenu',
    'ProductConfigureBase',
    'ProductConfigureAnswersView',
    'ProductConfigureBlueprintsView',
    'ProductDownloadFileMixin',
    'ProductDownloadFilesView',
    'ProductEditPeopleView',
    'ProductEditView',
    'ProductFacets',
    'ProductInvolvementView',
    'ProductNavigation',
    'ProductNavigationMenu',
    'ProductOverviewMenu',
    'ProductPackagesView',
    'ProductPackagesPortletView',
    'ProductRdfView',
    'ProductReviewLicenseView',
    'ProductSeriesSetView',
    'ProductSetBranchView',
    'ProductSetBreadcrumb',
    'ProductSetNavigation',
    'ProductSetReviewLicensesView',
    'ProductSetView',
    'ProductSpecificationsMenu',
    'ProductView',
    'SortSeriesMixin',
    'ProjectAddStepOne',
    'ProjectAddStepTwo',
    ]


from operator import attrgetter

from bzrlib.revision import NULL_REVISION
from lazr.delegates import delegate_to
from lazr.restful.interface import (
    copy_field,
    use_template,
    )
from lazr.restful.interfaces import IJSONRequestCache
from z3c.ptcompat import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.formlib.interfaces import WidgetInputError
from zope.formlib.widget import CustomWidgetFactory
from zope.formlib.widgets import (
    CheckBoxWidget,
    TextAreaWidget,
    TextWidget,
    )
from zope.interface import (
    implementer,
    Interface,
    )
from zope.lifecycleevent import ObjectCreatedEvent
from zope.schema import (
    Bool,
    Choice,
    )
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from lp import _
from lp.answers.browser.faqtarget import FAQTargetNavigationMixin
from lp.answers.browser.questiontarget import QuestionTargetTraversalMixin
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    render_radio_widget_part,
    ReturnToReferrerMixin,
    safe_action,
    )
from lp.app.browser.lazrjs import (
    BooleanChoiceWidget,
    InlinePersonEditPickerWidget,
    TextLineEditorWidget,
    )
from lp.app.browser.multistep import (
    MultiStepView,
    StepView,
    )
from lp.app.browser.stringformatter import FormattersAPI
from lp.app.browser.tales import (
    format_link,
    MenuAPI,
    )
from lp.app.enums import (
    InformationType,
    PROPRIETARY_INFORMATION_TYPES,
    PILLAR_INFORMATION_TYPES,
    ServiceUsage,
    )
from lp.app.errors import (
    NotFoundError,
    UnexpectedFormData,
    )
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.utilities import json_dump_information_types
from lp.app.vocabularies import InformationTypeVocabulary
from lp.app.widgets.date import DateWidget
from lp.app.widgets.itemswidgets import (
    CheckBoxMatrixWidget,
    LaunchpadRadioWidget,
    LaunchpadRadioWidgetWithDescription,
    )
from lp.app.widgets.popup import PersonPickerWidget
from lp.app.widgets.product import (
    GhostWidget,
    LicenseWidget,
    ProductNameWidget,
    )
from lp.app.widgets.textwidgets import StrippedTextWidget
from lp.blueprints.browser.specificationtarget import (
    HasSpecificationsMenuMixin,
    )
from lp.bugs.browser.buglisting import get_buglisting_search_filter_url
from lp.bugs.browser.bugtask import BugTargetTraversalMixin
from lp.bugs.browser.structuralsubscription import (
    expose_structural_subscription_data_to_js,
    StructuralSubscriptionMenuMixin,
    StructuralSubscriptionTargetTraversalMixin,
    )
from lp.bugs.interfaces.bugtask import RESOLVED_BUGTASK_STATUSES
from lp.code.browser.branch import BranchNameValidationMixin
from lp.code.browser.branchref import BranchRef
from lp.code.browser.codeimport import validate_import_url
from lp.code.browser.sourcepackagerecipelisting import HasRecipesMenuMixin
from lp.code.browser.vcslisting import TargetDefaultVCSNavigationMixin
from lp.code.enums import RevisionControlSystems
from lp.code.errors import BranchExists
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchjob import IRosettaUploadJobSource
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.codeimport import (
    ICodeImport,
    ICodeImportSet,
    )
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.registry.browser import (
    add_subscribe_link,
    BaseRdfView,
    )
from lp.registry.browser.announcement import HasAnnouncementsView
from lp.registry.browser.branding import BrandingChangeView
from lp.registry.browser.menu import (
    IRegistryCollectionNavigationMenu,
    RegistryCollectionActionMenuBase,
    )
from lp.registry.browser.pillar import (
    PillarBugsMenu,
    PillarInvolvementView,
    PillarNavigationMixin,
    PillarViewMixin,
    )
from lp.registry.enums import VCSType
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.registry.interfaces.product import (
    IProduct,
    IProductReviewSearch,
    IProductSet,
    License,
    LicenseStatus,
    )
from lp.registry.interfaces.productrelease import (
    IProductRelease,
    IProductReleaseSet,
    )
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.services.config import config
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.feeds.browser import FeedsMixin
from lp.services.fields import (
    PillarAliases,
    PublicPersonChoice,
    URIField,
    )
from lp.services.propertycache import cachedproperty
from lp.services.webapp import (
    ApplicationMenu,
    canonical_url,
    enabled_with_permission,
    LaunchpadView,
    Link,
    Navigation,
    sorted_version_numbers,
    StandardLaunchpadFacets,
    stepthrough,
    stepto,
    structured,
    )
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.batching import BatchNavigator
from lp.services.webapp.breadcrumb import Breadcrumb
from lp.services.webapp.interfaces import UnsafeFormGetSubmissionError
from lp.services.webapp.menu import NavigationMenu
from lp.services.webapp.vhosts import allvhosts
from lp.services.worlddata.helpers import browser_languages
from lp.services.worlddata.interfaces.country import ICountry
from lp.snappy.browser.hassnaps import HasSnapsMenuMixin
from lp.translations.browser.customlanguagecode import (
    HasCustomLanguageCodesTraversalMixin,
    )


OR = ' OR '
SPACE = ' '


class ProductNavigation(
    Navigation, BugTargetTraversalMixin,
    FAQTargetNavigationMixin, HasCustomLanguageCodesTraversalMixin,
    QuestionTargetTraversalMixin, StructuralSubscriptionTargetTraversalMixin,
    PillarNavigationMixin, TargetDefaultVCSNavigationMixin):

    usedfor = IProduct

    @stepto('.bzr')
    def dotbzr(self):
        if self.context.development_focus.branch:
            return BranchRef(self.context.development_focus.branch)
        else:
            return None

    @stepthrough('+spec')
    def traverse_spec(self, name):
        spec = self.context.getSpecification(name)
        if not check_permission('launchpad.LimitedView', spec):
            return None
        return spec

    @stepthrough('+milestone')
    def traverse_milestone(self, name):
        return self.context.getMilestone(name)

    @stepthrough('+release')
    def traverse_release(self, name):
        return self.context.getRelease(name)

    @stepthrough('+announcement')
    def traverse_announcement(self, name):
        return self.context.getAnnouncement(name)

    @stepthrough('+commercialsubscription')
    def traverse_commercialsubscription(self, name):
        return self.context.commercial_subscription

    def traverse(self, name):
        return self.context.getSeries(name)


class ProductSetNavigation(Navigation):

    usedfor = IProductSet

    def traverse(self, name):
        product = self.context.getByName(name)
        if product is None:
            raise NotFoundError(name)
        return self.redirectSubTree(canonical_url(product))


class ProductLicenseMixin:
    """Adds licence validation and requests reviews of licences.

    Subclasses must inherit from Launchpad[Edit]FormView as well.

    Requires the "product" attribute be set in the child
    classes' action handler.
    """

    def validate(self, data):
        """Validate 'licenses' and 'license_info'.

        'licenses' must not be empty unless the product already
        exists and never has had a licence set.

        'license_info' must not be empty if "Other/Proprietary"
        or "Other/Open Source" is checked.
        """
        licenses = data.get('licenses', [])
        license_widget = self.widgets.get('licenses')
        if (len(licenses) == 0 and license_widget is not None):
            self.setFieldError(
                'licenses',
                'You must select at least one licence.  If you select '
                'Other/Proprietary or Other/OpenSource you must include a '
                'description of the licence.')
        elif License.OTHER_PROPRIETARY in licenses:
            if not data.get('license_info'):
                self.setFieldError(
                    'license_info',
                    'A description of the "Other/Proprietary" '
                    'licence you checked is required.')
        elif License.OTHER_OPEN_SOURCE in licenses:
            if not data.get('license_info'):
                self.setFieldError(
                    'license_info',
                    'A description of the "Other/Open Source" '
                    'licence you checked is required.')
        else:
            # Launchpad is ok with all licenses used in this project.
            pass


class ProductFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IProduct."""

    usedfor = IProduct


class ProductInvolvementView(PillarInvolvementView):
    """Encourage configuration of involvement links for projects."""

    has_involvement = True

    @property
    def visible_disabled_link_names(self):
        """Show all disabled links...except blueprints"""
        involved_menu = MenuAPI(self).navigation
        all_links = involved_menu.keys()
        # The register blueprints link should not be shown since its use is
        # not encouraged.
        all_links.remove('register_blueprint')
        return all_links

    @cachedproperty
    def configuration_states(self):
        """Create a dictionary indicating the configuration statuses.

        Each app area will be represented in the return dictionary, except
        blueprints which we are not currently promoting.
        """
        states = {}
        states['configure_bugtracker'] = (
            self.context.bug_tracking_usage != ServiceUsage.UNKNOWN)
        states['configure_answers'] = (
            self.context.answers_usage != ServiceUsage.UNKNOWN)
        states['configure_translations'] = (
            self.context.translations_usage != ServiceUsage.UNKNOWN)
        states['configure_codehosting'] = (
            self.context.codehosting_usage != ServiceUsage.UNKNOWN)
        return states

    @property
    def configuration_links(self):
        """The enabled involvement links.

        Returns a list of dicts keyed by:
        'link' -- the menu link, and
        'configured' -- a boolean representing the configuration status.
        """
        overview_menu = MenuAPI(self.context).overview
        configuration_names = [
            'configure_bugtracker',
            'configure_translations',
            'configure_answers',
            #'configure_blueprints',
            ]
        config_list = []
        config_statuses = self.configuration_states
        for key in configuration_names:
            overview_menu[key].text = overview_menu[key].text.replace(
                'Configure ', '')
            config_list.append(dict(link=overview_menu[key],
                                    configured=config_statuses[key]))

        # Add the branch configuration in separately.
        configure_code = overview_menu['configure_code']
        configure_code.text = 'Code'
        configure_code.summary = "Specify the location of this project's code."
        config_list.insert(0,
            dict(link=configure_code,
                 configured=config_statuses['configure_codehosting']))
        return config_list

    @property
    def registration_completeness(self):
        """The percent complete for registration."""
        config_statuses = self.configuration_states
        configured = sum(1 for val in config_statuses.values() if val)
        scale = 100
        done = int(float(configured) / len(config_statuses) * scale)
        undone = scale - done
        return dict(done=done, undone=undone)

    @property
    def registration_done(self):
        """A boolean indicating that the services are fully configured."""
        return (self.registration_completeness['done'] == 100)


class ProductNavigationMenu(NavigationMenu):

    usedfor = IProduct
    facet = 'overview'
    links = [
        'details',
        'announcements',
        'downloads',
        ]

    def details(self):
        text = 'Details'
        return Link('', text)

    def announcements(self):
        text = 'Announcements'
        return Link('+announcements', text)

    def downloads(self):
        text = 'Downloads'
        return Link('+download', text)


class ProductEditLinksMixin(StructuralSubscriptionMenuMixin):
    """A mixin class for menus that need Product edit links."""

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.BugSupervisor')
    def configure_bugtracker(self):
        text = 'Configure Bugs'
        summary = 'Specify where bugs are tracked for this project'
        return Link('+configure-bugtracker', text, summary, icon='edit')

    @enabled_with_permission('launchpad.TranslationsAdmin')
    def configure_translations(self):
        text = 'Configure Translations'
        summary = 'Allow users to submit translations for this project'
        return Link('+configure-translations', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def configure_answers(self):
        text = 'Configure Answers'
        summary = 'Allow users to ask questions on this project'
        return Link('+configure-answers', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def configure_blueprints(self):
        text = 'Configure Blueprints'
        summary = 'Enable tracking of feature planning.'
        return Link('+configure-blueprints', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def branding(self):
        text = 'Change branding'
        return Link('+branding', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change people'
        return Link('+edit-people', text, icon='edit')

    @enabled_with_permission('launchpad.Moderate')
    def review_license(self):
        text = 'Review project'
        return Link('+review-license', text, icon='edit')

    @enabled_with_permission('launchpad.Moderate')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')

    @enabled_with_permission('launchpad.Driver')
    def sharing(self):
        return Link('+sharing', 'Sharing', icon='edit')


class IProductEditMenu(Interface):
    """A marker interface for the 'Change details' navigation menu."""


class IProductActionMenu(Interface):
    """A marker interface for the global action navigation menu."""


class ProductActionNavigationMenu(NavigationMenu, ProductEditLinksMixin):
    """A sub-menu for acting upon a Product."""

    usedfor = IProductActionMenu
    facet = 'overview'
    title = 'Actions'

    @cachedproperty
    def links(self):
        links = ['edit', 'review_license', 'administer', 'sharing']
        add_subscribe_link(links)
        return links


class ProductOverviewMenu(ApplicationMenu, ProductEditLinksMixin,
                          HasRecipesMenuMixin, HasSnapsMenuMixin):

    usedfor = IProduct
    facet = 'overview'
    links = [
        'edit',
        'configure_answers',
        'configure_blueprints',
        'configure_bugtracker',
        'configure_translations',
        'reassign',
        'top_contributors',
        'distributions',
        'packages',
        'series',
        'series_add',
        'configure_code',
        'milestones',
        'downloads',
        'announce',
        'announcements',
        'administer',
        'review_license',
        'rdf',
        'branding',
        'view_recipes',
        'view_snaps',
        ]

    def top_contributors(self):
        text = 'More contributors'
        return Link('+topcontributors', text, icon='info')

    def distributions(self):
        text = 'Distribution packaging information'
        return Link('+distributions', text, icon='info')

    def packages(self):
        text = 'Show distribution packages'
        return Link('+packages', text, icon='info')

    def series(self):
        text = 'View full history'
        return Link('+series', text, icon='info')

    @enabled_with_permission('launchpad.Driver')
    def series_add(self):
        text = 'Register a series'
        return Link('+addseries', text, icon='add')

    def milestones(self):
        text = 'View milestones'
        return Link('+milestones', text, icon='info')

    @enabled_with_permission('launchpad.Edit')
    def announce(self):
        text = 'Make announcement'
        summary = 'Publish an item of news for this project'
        return Link('+announce', text, summary, icon='add')

    def announcements(self):
        text = 'Read all announcements'
        enabled = bool(self.context.getAnnouncements())
        return Link('+announcements', text, icon='info', enabled=enabled)

    def rdf(self):
        text = structured(
            '<abbr title="Resource Description Framework">'
            'RDF</abbr> metadata')
        return Link('+rdf', text, icon='download')

    @enabled_with_permission('launchpad.Edit')
    def configure_code(self):
        """Return a link to configure code for this project."""
        text = 'Configure code'
        icon = 'edit'
        summary = 'Configure code for this project'
        return Link('+configure-code', text, summary, icon=icon)

    def downloads(self):
        text = 'Downloads'
        return Link('+download', text, icon='info')


class ProductBugsMenu(PillarBugsMenu, ProductEditLinksMixin):

    usedfor = IProduct
    facet = 'bugs'
    configurable_bugtracker = True

    @cachedproperty
    def links(self):
        links = ['filebug', 'bugsupervisor', 'cve']
        add_subscribe_link(links)
        links.append('configure_bugtracker')
        return links


class ProductSpecificationsMenu(NavigationMenu, ProductEditLinksMixin,
                                HasSpecificationsMenuMixin):
    usedfor = IProduct
    facet = 'specifications'
    links = ['configure_blueprints', 'listall', 'doc', 'assignments', 'new',
             'register_sprint']


def _cmp_distros(a, b):
    """Put Ubuntu first, otherwise in alpha order."""
    if a == 'ubuntu':
        return -1
    elif b == 'ubuntu':
        return 1
    else:
        return cmp(a, b)


class ProductSetBreadcrumb(Breadcrumb):
    """Return a breadcrumb for an `IProductSet`."""
    text = "Projects"


class SortSeriesMixin:
    """Provide access to helpers for series."""

    def _sorted_filtered_list(self, filter=None):
        """Return a sorted, filtered list of series.

        The series list is sorted by version in reverse order.  It is also
        filtered by calling `filter` on every series.  If the `filter`
        function returns False, don't include the series.  With None (the
        default, include everything).

        The development focus is always first in the list.
        """
        series_list = []
        for series in self.product.series:
            if filter is None or filter(series):
                series_list.append(series)
        # In production data, there exist development focus series that are
        # obsolete.  This may be caused by bad data, or it may be intended
        # functionality.  In either case, ensure that the development focus
        # branch is first in the list.
        if self.product.development_focus in series_list:
            series_list.remove(self.product.development_focus)
        # Now sort the list by name with newer versions before older.
        series_list = sorted_version_numbers(series_list,
                                             key=attrgetter('name'))
        series_list.insert(0, self.product.development_focus)
        return series_list

    @property
    def sorted_series_list(self):
        """Return a sorted list of series.

        The series list is sorted by version in reverse order.
        The development focus is always first in the list.
        """
        return self._sorted_filtered_list()

    @property
    def sorted_active_series_list(self):
        """Like `sorted_series_list()` but filters out OBSOLETE series."""
        # Callback for the filter which only allows series that have not been
        # marked obsolete.
        def check_active(series):
            return series.status != SeriesStatus.OBSOLETE
        return self._sorted_filtered_list(check_active)


@delegate_to(IProduct, context='product')
class ProductWithSeries:
    """A decorated product that includes series data.

    The extra data is included in this class to avoid repeated
    database queries.  Rather than hitting the database, the data is
    cached locally and simply returned.
    """

    # `series` and `development_focus` need to be declared as class
    # attributes so that this class will not delegate the actual instance
    # variables to self.product, which would bypass the caching.
    series = None
    development_focus = None

    def __init__(self, product):
        self.product = product
        self.series = []
        for series in self.product.series:
            series_with_releases = SeriesWithReleases(series, parent=self)
            self.series.append(series_with_releases)
            if self.product.development_focus == series:
                self.development_focus = series_with_releases

        # Get all of the releases for all of the series in a single
        # query.  The query sorts the releases properly so we know the
        # resulting list is sorted correctly.
        series_by_id = dict((series.id, series) for series in self.series)
        self.release_by_id = {}
        milestones_and_releases = list(
            self.product.getMilestonesAndReleases())
        for milestone, release in milestones_and_releases:
            series = series_by_id[milestone.productseries.id]
            release_delegate = ReleaseWithFiles(release, parent=series)
            series.addRelease(release_delegate)
            self.release_by_id[release.id] = release_delegate


@delegate_to(IProductSeries, context='series')
class DecoratedSeries:
    """A decorated series that includes helper attributes for templates."""

    def __init__(self, series):
        self.series = series

    @property
    def css_class(self):
        """The highlight, lowlight, or normal CSS class."""
        if self.is_development_focus:
            return 'highlight'
        elif self.status == SeriesStatus.OBSOLETE:
            return 'lowlight'
        else:
            # This is normal presentation.
            return ''

    @cachedproperty
    def packagings(self):
        """Convert packagings to list to prevent multiple evaluations."""
        return list(self.series.packagings)


class SeriesWithReleases(DecoratedSeries):
    """A decorated series that includes releases.

    The extra data is included in this class to avoid repeated
    database queries.  Rather than hitting the database, the data is
    cached locally and simply returned.
    """

    # `parent` and `releases` need to be declared as class attributes so that
    # this class will not delegate the actual instance variables to
    # self.series, which would bypass the caching for self.releases and would
    # raise an AttributeError for self.parent.
    parent = None
    releases = None

    def __init__(self, series, parent):
        super(SeriesWithReleases, self).__init__(series)
        self.parent = parent
        self.releases = []

    def addRelease(self, release):
        self.releases.append(release)

    @cachedproperty
    def has_release_files(self):
        for release in self.releases:
            if len(release.files) > 0:
                return True
        return False


@delegate_to(IProductRelease, context='release')
class ReleaseWithFiles:
    """A decorated release that includes product release files.

    The extra data is included in this class to avoid repeated
    database queries.  Rather than hitting the database, the data is
    cached locally and simply returned.
    """

    # `parent` needs to be declared as class attributes so that
    # this class will not delegate the actual instance variables to
    # self.release, which would raise an AttributeError.
    parent = None

    def __init__(self, release, parent):
        self.release = release
        self.parent = parent
        self._files = None

    @property
    def files(self):
        """Cache the release files for all the releases in the product."""
        if self._files is None:
            # Get all of the files for all of the releases.  The query
            # returns all releases sorted properly.
            product = self.parent.parent
            release_delegates = product.release_by_id.values()
            files = getUtility(IProductReleaseSet).getFilesForReleases(
                release_delegates)
            for release_delegate in release_delegates:
                release_delegate._files = []
            for file in files:
                id = file.productrelease.id
                release_delegate = product.release_by_id[id]
                release_delegate._files.append(file)

        # self._files was set above, since self is actually in the
        # release_delegates variable.
        return self._files

    @property
    def name_with_codename(self):
        milestone = self.release.milestone
        if milestone.code_name:
            return "%s (%s)" % (milestone.name, milestone.code_name)
        else:
            return milestone.name

    @cachedproperty
    def total_downloads(self):
        """Total downloads of files associated with this release."""
        return sum(file.libraryfile.hits for file in self.files)


class ProductDownloadFileMixin:
    """Provides methods for managing download files."""

    @cachedproperty
    def product(self):
        """Product with all series, release and file data cached.

        Decorated classes are created, and they contain cached data
        obtained with a few queries rather than many iterated queries.
        """
        return ProductWithSeries(self.context)

    def deleteFiles(self, releases):
        """Delete the selected files from the set of releases.

        :param releases: A set of releases in the view.
        :return: The number of files deleted.
        """
        del_count = 0
        for release in releases:
            for release_file in release.files:
                if release_file.libraryfile.id in self.delete_ids:
                    release_file.destroySelf()
                    self.delete_ids.remove(release_file.libraryfile.id)
                    del_count += 1
        return del_count

    def getReleases(self):
        """Find the releases with download files for view."""
        raise NotImplementedError

    def processDeleteFiles(self):
        """If the 'delete_files' button was pressed, process the deletions."""
        del_count = None
        if 'delete_files' in self.form:
            if self.request.method == 'POST':
                self.delete_ids = [
                    int(value) for key, value in self.form.items()
                    if key.startswith('checkbox')]
                del(self.form['delete_files'])
                releases = self.getReleases()
                del_count = self.deleteFiles(releases)
            else:
                # If there is a form submission and it is not a POST then
                # raise an error.  This is to protect against XSS exploits.
                raise UnsafeFormGetSubmissionError(self.form['delete_files'])
        if del_count is not None:
            if del_count <= 0:
                self.request.response.addNotification(
                    "No files were deleted.")
            elif del_count == 1:
                self.request.response.addNotification(
                    "1 file has been deleted.")
            else:
                self.request.response.addNotification(
                    "%d files have been deleted." %
                    del_count)

    @cachedproperty
    def latest_release_with_download_files(self):
        """Return the latest release with download files."""
        for series in self.sorted_active_series_list:
            for release in series.releases:
                if len(list(release.files)) > 0:
                    return release
        return None

    @cachedproperty
    def has_download_files(self):
        for series in self.context.series:
            if series.status == SeriesStatus.OBSOLETE:
                continue
            for release in series.getCachedReleases():
                if len(list(release.files)) > 0:
                    return True
        return False


@implementer(IProductActionMenu)
class ProductView(PillarViewMixin, HasAnnouncementsView, SortSeriesMixin,
                  FeedsMixin, ProductDownloadFileMixin):

    @property
    def maintainer_widget(self):
        return InlinePersonEditPickerWidget(
            self.context, IProduct['owner'],
            format_link(self.context.owner),
            header='Change maintainer', edit_view='+edit-people',
            step_title='Select a new maintainer', show_create_team=True)

    @property
    def driver_widget(self):
        return InlinePersonEditPickerWidget(
            self.context, IProduct['driver'],
            format_link(self.context.driver, empty_value="Not yet selected"),
            header='Change driver', edit_view='+edit-people',
            step_title='Select a new driver', show_create_team=True,
            null_display_value="Not yet selected",
            help_link="/+help-registry/driver.html")

    def __init__(self, context, request):
        HasAnnouncementsView.__init__(self, context, request)
        self.form = request.form_ng

    def initialize(self):
        super(ProductView, self).initialize()
        self.status_message = None
        product = self.context
        programming_lang = IProduct['programminglang']
        title = 'Edit programming languages'
        additional_arguments = {
            'width': '9em',
            'css_class': 'nowrap'}
        if self.context.programminglang is None:
            additional_arguments.update(dict(
                default_text='Not yet specified',
                initial_value_override='',
                ))
        self.languages_edit_widget = TextLineEditorWidget(
            product, programming_lang, title, 'span', **additional_arguments)
        self.show_programming_languages = bool(
            self.context.programminglang or
            check_permission('launchpad.Edit', self.context))
        expose_structural_subscription_data_to_js(
            self.context, self.request, self.user)

    @property
    def page_title(self):
        return '%s in Launchpad' % self.context.displayname

    @property
    def page_description(self):
        return '\n'.filter(
            None,
            [self.context.summary, self.context.description])

    @property
    def show_license_status(self):
        return self.context.license_status != LicenseStatus.OPEN_SOURCE

    @property
    def sourceforge_url(self):
        if self.context.sourceforgeproject:
            return ("http://sourceforge.net/projects/%s"
                % self.context.sourceforgeproject)
        return None

    @property
    def has_external_links(self):
        return (self.context.homepageurl or
                self.context.sourceforgeproject or
                self.context.wikiurl or
                self.context.screenshotsurl or
                self.context.downloadurl)

    @property
    def external_links(self):
        """The project's external links.

        The home page link is not included because its link must have the
        rel=nofollow attribute.
        """
        from lp.services.webapp.menu import MenuLink
        urls = [
            ('Sourceforge project', self.sourceforge_url),
            ('Wiki', self.context.wikiurl),
            ('Screenshots', self.context.screenshotsurl),
            ('External downloads', self.context.downloadurl),
            ]
        links = []
        for (text, url) in urls:
            if url is not None:
                menu_link = MenuLink(
                    Link(url, text, icon='external-link', enabled=True))
                menu_link.url = url
                links.append(menu_link)
        return links

    @property
    def should_display_homepage(self):
        return (self.context.homepageurl and
                self.context.homepageurl not in
                    [self.sourceforge_url])

    def requestCountry(self):
        return ICountry(self.request, None)

    @property
    def golang_import_spec(self):
        """Meta string for golang remote import path.
        See: https://golang.org/cmd/go/#hdr-Remote_import_paths
        """
        if self.context.vcs == VCSType.GIT:
            repo = getUtility(IGitRepositorySet).getDefaultRepository(
                self.context)
            if check_permission('launchpad.View', repo):
                return "{hostname}/{product} git {git_https_url}".format(
                    hostname=config.vhost.mainsite.hostname,
                    product=self.context.name,
                    git_https_url=repo.git_https_url)
        elif self.context.vcs == VCSType.BZR:
            branch = self.context.development_focus.branch
            if check_permission('launchpad.View', branch):
                return (
                    "{hostname}/{product} bzr "
                    "{root_url}{branch}").format(
                        hostname=config.vhost.mainsite.hostname,
                        root_url=allvhosts.configs['mainsite'].rooturl,
                        product=self.context.name,
                        branch=branch.unique_name)
        return None

    def browserLanguages(self):
        return browser_languages(self.request)

    def getClosedBugsURL(self, series):
        status = [status.title for status in RESOLVED_BUGTASK_STATUSES]
        url = canonical_url(series) + '/+bugs'
        return get_buglisting_search_filter_url(url, status=status)

    @property
    def can_purchase_subscription(self):
        return (check_permission('launchpad.Edit', self.context)
                and not self.context.qualifies_for_free_hosting)

    @cachedproperty
    def effective_driver(self):
        """Return the product driver or the project group driver."""
        if self.context.driver is not None:
            driver = self.context.driver
        elif (self.context.projectgroup is not None and
              self.context.projectgroup.driver is not None):
            driver = self.context.projectgroup.driver
        else:
            driver = None
        return driver

    @cachedproperty
    def show_commercial_subscription_info(self):
        """Should subscription information be shown?

        Subscription information is only shown to the project maintainers,
        Launchpad admins, and members of the Launchpad commercial team.  The
        first two are allowed via the Launchpad.Edit permission.  The latter
        is allowed via Launchpad.Commercial.
        """
        return (check_permission('launchpad.Edit', self.context) or
                check_permission('launchpad.Commercial', self.context))

    @cachedproperty
    def show_license_info(self):
        """Should the view show the extra licence information."""
        return (
            License.OTHER_OPEN_SOURCE in self.context.licenses
            or License.OTHER_PROPRIETARY in self.context.licenses)

    @cachedproperty
    def is_proprietary(self):
        """Is the project proprietary."""
        return License.OTHER_PROPRIETARY in self.context.licenses

    @property
    def active_widget(self):
        return BooleanChoiceWidget(
            self.context, IProduct['active'],
            content_box_id='%s-edit-active' % FormattersAPI(
                self.context.name).css_id(),
            edit_view='+review-license',
            tag='span',
            false_text='Deactivated',
            true_text='Active',
            header='Is this project active and usable by the community?')

    @property
    def project_reviewed_widget(self):
        return BooleanChoiceWidget(
            self.context, IProduct['project_reviewed'],
            content_box_id='%s-edit-project-reviewed' % FormattersAPI(
                self.context.name).css_id(),
            edit_view='+review-license',
            tag='span',
            false_text='Unreviewed',
            true_text='Reviewed',
            header='Have you reviewed the project?')

    @property
    def license_approved_widget(self):
        licenses = list(self.context.licenses)
        if License.OTHER_PROPRIETARY in licenses:
            return 'Commercial subscription required'
        elif [License.DONT_KNOW] == licenses or [] == licenses:
            return 'Licence required'
        return BooleanChoiceWidget(
            self.context, IProduct['license_approved'],
            content_box_id='%s-edit-license-approved' % FormattersAPI(
                self.context.name).css_id(),
            edit_view='+review-license',
            tag='span',
            false_text='Unapproved',
            true_text='Approved',
            header='Does the licence qualifiy the project for free hosting?')


class ProductPackagesView(LaunchpadView):
    """View for displaying product packaging"""

    label = 'Linked packages'
    page_title = label

    @cachedproperty
    def series_batch(self):
        """A batch of series that are active or have packages."""
        decorated_series = DecoratedResultSet(
            self.context.active_or_packaged_series, DecoratedSeries)
        return BatchNavigator(decorated_series, self.request)

    @property
    def distro_packaging(self):
        """This method returns a representation of the product packagings
        for this product, in a special structure used for the
        product-distros.pt page template.

        Specifically, it is a list of "distro" objects, each of which has a
        title, and an attribute "packagings" which is a list of the relevant
        packagings for this distro and product.
        """
        distros = {}
        for packaging in self.context.packagings:
            distribution = packaging.distroseries.distribution
            if distribution.name in distros:
                distro = distros[distribution.name]
            else:
                # Create a dictionary for the distribution.
                distro = dict(
                    distribution=distribution,
                    packagings=[])
                distros[distribution.name] = distro
            distro['packagings'].append(packaging)
        # Now we sort the resulting list of "distro" objects, and return that.
        distro_names = distros.keys()
        distro_names.sort(cmp=_cmp_distros)
        results = [distros[name] for name in distro_names]
        return results


class ProductPackagesPortletView(LaunchpadView):
    """View class for product packaging portlet."""

    schema = Interface

    @cachedproperty
    def sourcepackages(self):
        """The project's latest source packages."""
        current_packages = [
            sp for sp in self.context.sourcepackages
            if sp.currentrelease is not None]
        current_packages.reverse()
        return current_packages[0:5]

    @cachedproperty
    def can_show_portlet(self):
        """Are there packages, or can packages be suggested."""
        if len(self.sourcepackages) > 0:
            return True


class SeriesReleasePair:
    """Class for holding a series and release.

    Replaces the use of a (series, release) tuple so that it can be more
    clearly addressed in the view class.
    """

    def __init__(self, series, release):
        self.series = series
        self.release = release


class ProductDownloadFilesView(LaunchpadView,
                               SortSeriesMixin,
                               ProductDownloadFileMixin):
    """View class for the product's file downloads page."""

    batch_size = config.launchpad.download_batch_size

    @property
    def page_title(self):
        return "%s project files" % self.context.displayname

    def initialize(self):
        """See `LaunchpadFormView`."""
        self.form = self.request.form
        # Manually process action for the 'Delete' button.
        self.processDeleteFiles()

    def getReleases(self):
        """See `ProductDownloadFileMixin`."""
        releases = set()
        for series in self.product.series:
            releases.update(series.releases)
        return releases

    @cachedproperty
    def series_and_releases_batch(self):
        """Get a batch of series and release

        Each entry returned is a tuple of (series, release).
        """
        series_and_releases = []
        for series in self.sorted_series_list:
            for release in series.releases:
                if len(release.files) > 0:
                    pair = SeriesReleasePair(series, release)
                    if pair not in series_and_releases:
                        series_and_releases.append(pair)
        batch = BatchNavigator(series_and_releases, self.request,
                               size=self.batch_size)
        batch.setHeadings("release", "releases")
        return batch

    @cachedproperty
    def has_download_files(self):
        """Across series and releases do any download files exist?"""
        for series in self.product.series:
            if series.has_release_files:
                return True
        return False

    @cachedproperty
    def any_download_files_with_signatures(self):
        """Do any series or release download files have signatures?"""
        for series in self.product.series:
            for release in series.releases:
                for file in release.files:
                    if file.signature:
                        return True
        return False

    @cachedproperty
    def milestones(self):
        """A mapping between series and releases that are milestones."""
        result = dict()
        for series in self.product.series:
            result[series.name] = set()
            milestone_list = [m.name for m in series.milestones]
            for release in series.releases:
                if release.version in milestone_list:
                    result[series.name].add(release.version)
        return result

    def is_milestone(self, series, release):
        """Determine whether a release is milestone for the series."""
        return (series.name in self.milestones and
                release.version in self.milestones[series.name])


@implementer(IProductEditMenu)
class ProductBrandingView(BrandingChangeView):
    """A view to set branding."""

    label = "Change branding"
    schema = IProduct
    field_names = ['icon', 'logo', 'mugshot']

    @property
    def page_title(self):
        """The HTML page title."""
        return "Change %s's branding" % self.context.title

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)


@implementer(IProductEditMenu)
class ProductConfigureBase(ReturnToReferrerMixin, LaunchpadEditFormView):
    schema = IProduct
    usage_fieldname = None

    def setUpFields(self):
        super(ProductConfigureBase, self).setUpFields()
        if self.usage_fieldname is not None:
            # The usage fields are shared among pillars.  But when referring
            # to an individual object in Launchpad it is better to call it by
            # its real name, i.e. 'project' instead of 'pillar'.
            usage_field = self.form_fields.get(self.usage_fieldname)
            if usage_field:
                usage_field.custom_widget = CustomWidgetFactory(
                    LaunchpadRadioWidget, orientation='vertical')
                # Copy the field or else the description in the interface will
                # be modified in-place.
                field = copy_field(usage_field.field)
                field.description = (
                    field.description.replace('pillar', 'project'))
                usage_field.field = field
                if (self.usage_fieldname in
                    ('answers_usage', 'translations_usage') and
                    self.context.information_type in
                    PROPRIETARY_INFORMATION_TYPES):
                    values = usage_field.field.vocabulary.items
                    terms = [SimpleTerm(value, value.name, value.title)
                             for value in values
                             if value != ServiceUsage.LAUNCHPAD]
                    usage_field.field.vocabulary = SimpleVocabulary(terms)

    @property
    def field_names(self):
        return [self.usage_fieldname]

    @property
    def page_title(self):
        return self.label

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class ProductConfigureBlueprintsView(ProductConfigureBase):
    """View class to configure the Launchpad Blueprints for a project."""

    label = "Configure blueprints"
    usage_fieldname = 'blueprints_usage'


class ProductConfigureAnswersView(ProductConfigureBase):
    """View class to configure the Launchpad Answers for a project."""

    label = "Configure answers"
    usage_fieldname = 'answers_usage'


@implementer(IProductEditMenu)
class ProductEditView(ProductLicenseMixin, LaunchpadEditFormView):
    """View class that lets you edit a Product object."""

    label = "Edit details"
    schema = IProduct
    field_names = [
        "displayname",
        "title",
        "summary",
        "description",
        "projectgroup",
        "homepageurl",
        "information_type",
        "sourceforgeproject",
        "wikiurl",
        "screenshotsurl",
        "downloadurl",
        "programminglang",
        "development_focus",
        "licenses",
        "license_info",
        ]
    custom_widget('licenses', LicenseWidget)
    custom_widget('license_info', GhostWidget)
    custom_widget(
        'information_type', LaunchpadRadioWidgetWithDescription,
        vocabulary=InformationTypeVocabulary(types=PILLAR_INFORMATION_TYPES))

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        if self.context.active:
            if len(self.errors) > 0:
                return None
            return canonical_url(self.context)
        else:
            return canonical_url(getUtility(IProductSet))

    cancel_url = next_url

    @property
    def page_title(self):
        """The HTML page title."""
        return "Change %s's details" % self.context.title

    def initialize(self):
        # The JSON cache must be populated before the super call, since
        # the form is rendered during LaunchpadFormView's initialize()
        # when an action is invoked.
        cache = IJSONRequestCache(self.request)
        json_dump_information_types(cache, PILLAR_INFORMATION_TYPES)
        super(ProductEditView, self).initialize()

    def validate(self, data):
        """Validate 'licenses' and 'license_info'.

        'licenses' must not be empty unless the product already
        exists and never has had a licence set.

        'license_info' must not be empty if "Other/Proprietary"
        or "Other/Open Source" is checked.
        """
        super(ProductEditView, self).validate(data)
        information_type = data.get('information_type')
        if information_type:
            errors = [
                str(e) for e in self.context.checkInformationType(
                    information_type)]
            if len(errors) > 0:
                self.setFieldError('information_type', ' '.join(errors))

    def showOptionalMarker(self, field_name):
        """See `LaunchpadFormView`."""
        # This has the effect of suppressing the ": (Optional)" stuff for the
        # license_info widget.  It's the last piece of the puzzle for
        # manipulating the license_info widget into the table for the
        # LicenseWidget instead of the enclosing form.
        if field_name == 'license_info':
            return False
        return super(ProductEditView, self).showOptionalMarker(field_name)

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class ProductValidationMixin:

    def validate_deactivation(self, data):
        """Verify whether a product can be safely deactivated."""
        if data['active'] == False and self.context.active == True:
            if len(self.context.sourcepackages) > 0:
                self.setFieldError('active',
                    structured(
                        'This project cannot be deactivated since it is '
                        'linked to one or more '
                        '<a href="%s">source packages</a>.',
                        canonical_url(self.context, view_name='+packages')))


class ProductAdminView(ProductEditView, ProductValidationMixin):
    """View for $project/+admin"""
    label = "Administer project details"
    default_field_names = [
        "name",
        "owner",
        "active",
        "autoupdate",
        ]

    @property
    def page_title(self):
        """The HTML page title."""
        return 'Administer %s' % self.context.title

    def setUpFields(self):
        """Setup the normal fields from the schema plus adds 'Registrant'.

        The registrant is normally a read-only field and thus does not have a
        proper widget created by default.  Even though it is read-only, admins
        need the ability to change it.
        """
        self.field_names = self.default_field_names[:]
        admin = check_permission('launchpad.Admin', self.context)
        if not admin:
            self.field_names.remove('owner')
            self.field_names.remove('autoupdate')
        super(ProductAdminView, self).setUpFields()
        self.form_fields = self._createAliasesField() + self.form_fields
        if admin:
            self.form_fields = (
                self.form_fields + self._createRegistrantField())

    def _createAliasesField(self):
        """Return a PillarAliases field for IProduct.aliases."""
        return form.Fields(
            PillarAliases(
                __name__='aliases', title=_('Aliases'),
                description=_('Other names (separated by space) under which '
                              'this project is known.'),
                required=False, readonly=False),
            render_context=self.render_context)

    def _createRegistrantField(self):
        """Return a popup widget person selector for the registrant.

        This custom field is necessary because *normally* the registrant is
        read-only but we want the admins to have the ability to correct legacy
        data that was set before the registrant field existed.
        """
        return form.Fields(
            PublicPersonChoice(
                __name__='registrant',
                title=_('Project Registrant'),
                description=_('The person who originally registered the '
                              'product.  Distinct from the current '
                              'owner.  This is historical data and should '
                              'not be changed without good cause.'),
                vocabulary='ValidPersonOrTeam',
                required=True,
                readonly=False,
                ),
            render_context=self.render_context
            )

    def validate(self, data):
        """See `LaunchpadFormView`."""
        super(ProductAdminView, self).validate(data)
        self.validate_deactivation(data)

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)


class ProductReviewLicenseView(ReturnToReferrerMixin, ProductEditView,
                               ProductValidationMixin):
    """A view to review a project and change project privileges."""
    label = "Review project"
    field_names = [
        "project_reviewed",
        "license_approved",
        "active",
        "reviewer_whiteboard",
        ]

    @property
    def page_title(self):
        """The HTML page title."""
        return 'Review %s' % self.context.title

    def validate(self, data):
        """See `LaunchpadFormView`."""

        super(ProductReviewLicenseView, self).validate(data)
        # A project can only be approved if it has OTHER_OPEN_SOURCE as one of
        # its licenses and not OTHER_PROPRIETARY.
        licenses = self.context.licenses
        license_approved = data.get('license_approved', False)
        if license_approved:
            if License.OTHER_PROPRIETARY in licenses:
                self.setFieldError(
                    'license_approved',
                    'Proprietary projects may not be manually '
                    'approved to use Launchpad.  Proprietary projects '
                    'must use the commercial subscription voucher system '
                    'to be allowed to use Launchpad.')
            else:
                # An Other/Open Source licence was specified so it may be
                # approved.
                pass

        self.validate_deactivation(data)


class ProductAddSeriesView(LaunchpadFormView):
    """A form to add new product series"""

    schema = IProductSeries
    field_names = ['name', 'summary', 'branch', 'releasefileglob']
    custom_widget('summary', TextAreaWidget, height=7, width=62)
    custom_widget('releasefileglob', StrippedTextWidget, displayWidth=40)

    series = None

    @property
    def label(self):
        """The form label."""
        return 'Register a new %s release series' % (
            self.context.displayname)

    @property
    def page_title(self):
        """The page title."""
        return self.label

    def validate(self, data):
        """See `LaunchpadFormView`."""
        from lp.registry.browser.productseries import get_series_branch_error
        branch = data.get('branch')
        if branch is not None:
            message = get_series_branch_error(self.context, branch)
            if message:
                self.setFieldError('branch', message)

    @action(_('Register Series'), name='add')
    def add_action(self, action, data):
        self.series = self.context.newSeries(
            owner=self.user,
            name=data['name'],
            summary=data['summary'],
            branch=data['branch'],
            releasefileglob=data['releasefileglob'])

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        assert self.series is not None, 'No series has been created'
        return canonical_url(self.series)

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)


class ProductSeriesSetView(ProductView):
    """A view for showing a product's series."""

    label = 'timeline'
    page_title = label

    @cachedproperty
    def batched_series(self):
        decorated_result = DecoratedResultSet(
            self.context.getVersionSortedSeries(), DecoratedSeries)
        return BatchNavigator(decorated_result, self.request)


LINK_LP_BZR = 'link-lp-bzr'
IMPORT_EXTERNAL = 'import-external'


BRANCH_TYPE_VOCABULARY = SimpleVocabulary((
    SimpleTerm(LINK_LP_BZR, LINK_LP_BZR,
               _("Link to a Bazaar branch already on Launchpad")),
    SimpleTerm(IMPORT_EXTERNAL, IMPORT_EXTERNAL,
               _("Import a branch hosted somewhere else")),
    ))


class SetBranchForm(Interface):
    """The fields presented on the form for setting a branch."""

    use_template(ICodeImport, ['cvs_module'])

    rcs_type = Choice(title=_("Type of RCS"),
        required=False, vocabulary=RevisionControlSystems,
        description=_(
            "The version control system to import from. "))

    repo_url = URIField(
        title=_("Branch URL"), required=True,
        description=_("The URL of the branch."),
        allowed_schemes=["http", "https"],
        allow_userinfo=False, allow_port=True, allow_query=False,
        allow_fragment=False, trailing_slash=False)

    branch_location = copy_field(
        IProductSeries['branch'], __name__='branch_location',
        title=_('Branch'),
        description=_(
            "The Bazaar branch for this series in Launchpad, "
            "if one exists."))

    branch_type = Choice(
        title=_('Import type'), vocabulary=BRANCH_TYPE_VOCABULARY,
        description=_("The type of import"), required=True)

    branch_name = copy_field(
        IBranch['name'], __name__='branch_name', title=_('Branch name'),
        description=_(''), required=True)

    branch_owner = copy_field(
        IBranch['owner'], __name__='branch_owner', title=_('Branch owner'),
        description=_(''), required=True)


def create_git_fields():
    return form.Fields(
        Choice(__name__='default_vcs',
               title=_("Project VCS"),
               required=True, vocabulary=VCSType,
               description=_("The version control system for "
                             "this project.")),
        Choice(__name__='git_repository_location',
               title=_('Git repository'),
               required=False,
               vocabulary='GitRepositoryRestrictedOnProduct',
               description=_(
                   "The Git repository for this project in Launchpad, "
                   "if one exists, in the form: "
                   "~user/project-name/+git/repo-name"))
    )


class ProductSetBranchView(ReturnToReferrerMixin, LaunchpadFormView,
                           ProductView,
                           BranchNameValidationMixin):
    """The view to set a branch default for the Product."""

    label = 'Configure code'
    page_title = label
    schema = SetBranchForm
    # Set for_input to True to ensure fields marked read-only will be editable
    # upon creation.
    for_input = True

    custom_widget('rcs_type', LaunchpadRadioWidget)
    custom_widget('branch_type', LaunchpadRadioWidget)
    custom_widget('default_vcs', LaunchpadRadioWidget)

    errors_in_action = False
    is_series = False

    @property
    def series(self):
        return self.context.development_focus

    @property
    def initial_values(self):
        repository_set = getUtility(IGitRepositorySet)
        return dict(
            rcs_type=RevisionControlSystems.BZR,
            default_vcs=(self.context.pillar.inferred_vcs or VCSType.BZR),
            branch_type=LINK_LP_BZR,
            branch_location=self.series.branch,
            git_repository_location=repository_set.getDefaultRepository(
                self.context.pillar))

    @property
    def next_url(self):
        """Return the next_url.

        Use the value from `ReturnToReferrerMixin` or None if there
        are errors.
        """
        if self.errors_in_action:
            return None
        return super(ProductSetBranchView, self).next_url

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        super(ProductSetBranchView, self).setUpFields()
        if not self.is_series:
            self.form_fields = (self.form_fields + create_git_fields())

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        super(ProductSetBranchView, self).setUpWidgets()
        widget = self.widgets['rcs_type']
        vocab = widget.vocabulary
        current_value = widget._getFormValue()
        self.rcs_type_cvs = render_radio_widget_part(
            widget, vocab.CVS, current_value, 'CVS')
        self.rcs_type_svn = render_radio_widget_part(
            widget, vocab.BZR_SVN, current_value, 'SVN')
        self.rcs_type_git = render_radio_widget_part(
            widget, vocab.GIT, current_value)
        self.rcs_type_bzr = render_radio_widget_part(
            widget, vocab.BZR, current_value)
        self.rcs_type_emptymarker = widget._emptyMarker()

        widget = self.widgets['branch_type']
        current_value = widget._getFormValue()
        vocab = widget.vocabulary

        (self.branch_type_link,
         self.branch_type_import) = [
            render_radio_widget_part(widget, value, current_value)
            for value in (LINK_LP_BZR, IMPORT_EXTERNAL)]

        if not self.is_series:
            widget = self.widgets['default_vcs']
            vocab = widget.vocabulary
            current_value = widget._getFormValue()
            self.default_vcs_git = render_radio_widget_part(
                widget, vocab.GIT, current_value, 'Git')
            self.default_vcs_bzr = render_radio_widget_part(
                widget, vocab.BZR, current_value, 'Bazaar')

    def _validateLinkLpBzr(self, data):
        """Validate data for link-lp-bzr case."""
        if 'branch_location' not in data:
            self.setFieldError(
                'branch_location', 'The branch location must be set.')

    def _validateLinkLpGit(self, data):
        """Validate data for link-lp-git case."""
        if data.get('git_repository_location'):
            repo = data.get('git_repository_location')
            if not repo:
                self.setFieldError(
                    'git_repository_location',
                    'The repository does not exist.')

    def _validateImportExternal(self, data):
        """Validate data for import external case."""
        rcs_type = data.get('rcs_type')
        repo_url = data.get('repo_url')

        # Private teams are forbidden from owning code imports.
        branch_owner = data.get('branch_owner')
        if branch_owner is not None and branch_owner.private:
            self.setFieldError(
                'branch_owner', 'Private teams are forbidden from owning '
                'external imports.')

        if repo_url is None:
            self.setFieldError(
                'repo_url', 'You must set the external repository URL.')
        else:
            reason = validate_import_url(repo_url, rcs_type)
            if reason:
                self.setFieldError('repo_url', reason)

        # RCS type is mandatory.
        # This condition should never happen since an initial value is set.
        if rcs_type is None:
            # The error shows but does not identify the widget.
            self.setFieldError(
                'rcs_type',
                'You must specify the type of RCS for the remote host.')
        elif rcs_type == RevisionControlSystems.CVS:
            if 'cvs_module' not in data:
                self.setFieldError('cvs_module', 'The CVS module must be set.')
        self._validateBranch(data)

    def _validateBranch(self, data):
        """Validate that branch name and owner are set."""
        if 'branch_name' not in data:
            self.setFieldError('branch_name', 'The branch name must be set.')
        if 'branch_owner' not in data:
            self.setFieldError('branch_owner', 'The branch owner must be set.')

    def _setRequired(self, names, value):
        """Mark the widget field as optional."""
        for name in names:
            widget = self.widgets[name]
            # The 'required' property on the widget context is set to False.
            # The widget also has a 'required' property but it isn't used
            # during validation.
            widget.context.required = value

    def _validSchemes(self, rcs_type):
        """Return the valid schemes for the repository URL."""
        schemes = set(['http', 'https'])
        # Extend the allowed schemes for the repository URL based on
        # rcs_type.
        extra_schemes = {
            RevisionControlSystems.BZR_SVN: ['svn'],
            RevisionControlSystems.GIT: ['git'],
            RevisionControlSystems.BZR: ['bzr'],
            }
        schemes.update(extra_schemes.get(rcs_type, []))
        return schemes

    def validate_widgets(self, data, names=None):
        """See `LaunchpadFormView`."""
        names = ['branch_type', 'rcs_type', 'default_vcs']
        super(ProductSetBranchView, self).validate_widgets(data, names)
        branch_type = data.get('branch_type')

        if branch_type == LINK_LP_BZR:
            # Mark other widgets as non-required.
            self._setRequired(['rcs_type', 'repo_url', 'cvs_module',
                               'branch_name', 'branch_owner'], False)
        elif branch_type == IMPORT_EXTERNAL:
            rcs_type = data.get('rcs_type')

            # Set the valid schemes based on rcs_type.
            self.widgets['repo_url'].field.allowed_schemes = (
                self._validSchemes(rcs_type))
            # The branch location is not required for validation.
            self._setRequired(['branch_location'], False)
            # The cvs_module is required if it is a CVS import.
            if rcs_type == RevisionControlSystems.CVS:
                self._setRequired(['cvs_module'], True)
        else:
            raise AssertionError("Unknown branch type %s" % branch_type)
        # Perform full validation now.
        super(ProductSetBranchView, self).validate_widgets(data)

    def validate(self, data):
        """See `LaunchpadFormView`."""
        # If widget validation returned errors then there is no need to
        # continue as we'd likely just override the errors reported there.
        if len(self.errors) > 0:
            return
        branch_type = data.get('branch_type')
        if not self.is_series:
            self._validateLinkLpGit(data)
        if branch_type == IMPORT_EXTERNAL:
            self._validateImportExternal(data)
        elif branch_type == LINK_LP_BZR:
            self._validateLinkLpBzr(data)
        else:
            raise AssertionError("Unknown branch type %s" % branch_type)

    @property
    def target(self):
        """The branch target for the context."""
        return IBranchTarget(self.context)

    def abort_update(self):
        """Abort transaction.

        This is normally handled by LaunchpadFormView, but this can be called
        from the success handler."""

        self.errors_in_action = True
        self._abort()

    def add_update_notification(self):
        self.request.response.addInfoNotification(
            'Project settings updated.')

    @action(_('Update'), name='update')
    def update_action(self, action, data):
        branch_type = data.get('branch_type')

        if not self.is_series:
            default_vcs = data.get('default_vcs')
            if default_vcs:
                self.context.vcs = default_vcs

            repo = data.get('git_repository_location')
            getUtility(IGitRepositorySet).setDefaultRepository(
                self.context, repo)
        if branch_type == LINK_LP_BZR:
            branch_location = data.get('branch_location')
            if branch_location != self.series.branch:
                self.series.branch = branch_location
                # Request an initial upload of translation files.
                getUtility(IRosettaUploadJobSource).create(
                    self.series.branch, NULL_REVISION)
            else:
                self.series.branch = branch_location
            self.add_update_notification()
        else:
            branch_name = data.get('branch_name')
            branch_owner = data.get('branch_owner')

            if branch_type == IMPORT_EXTERNAL:
                rcs_type = data.get('rcs_type')
                if rcs_type == RevisionControlSystems.CVS:
                    cvs_root = data.get('repo_url')
                    cvs_module = data.get('cvs_module')
                    url = None
                else:
                    cvs_root = None
                    cvs_module = None
                    url = data.get('repo_url')
                rcs_item = RevisionControlSystems.items[rcs_type.name]
                try:
                    code_import = getUtility(ICodeImportSet).new(
                        owner=branch_owner,
                        registrant=self.user,
                        target=IBranchTarget(self.target),
                        branch_name=branch_name,
                        rcs_type=rcs_item,
                        url=url,
                        cvs_root=cvs_root,
                        cvs_module=cvs_module)
                except BranchExists as e:
                    self._setBranchExists(e.existing_branch, 'branch_name')
                    self.abort_update()
                    return
                self.series.branch = code_import.branch
                self.request.response.addInfoNotification(
                    'Code import created and branch linked to the series.')
            else:
                raise UnexpectedFormData(branch_type)


class ProductRdfView(BaseRdfView):
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile(
        '../templates/product-rdf.pt')

    @property
    def filename(self):
        return '%s.rdf' % self.context.name


class ProductSetNavigationMenu(RegistryCollectionActionMenuBase):
    """Action menu for products index."""
    usedfor = IProductSet
    links = [
        'register_team',
        'register_project',
        'create_account',
        'review_licenses',
        'view_all_projects',
        ]

    @enabled_with_permission('launchpad.Moderate')
    def review_licenses(self):
        return Link('+review-licenses', 'Review projects', icon='edit')

    def view_all_projects(self):
        return Link('+all', 'Show all projects', icon='list')


@implementer(IRegistryCollectionNavigationMenu)
class ProductSetView(LaunchpadView):
    """View for products index page."""

    page_title = 'Projects registered in Launchpad'

    max_results_to_display = config.launchpad.default_batch_size
    results = None
    search_requested = False

    def initialize(self):
        """See `LaunchpadView`."""
        form = self.request.form_ng
        self.search_string = form.getOne('text')
        if self.search_string is not None:
            self.search_requested = True

    @cachedproperty
    def all_batched(self):
        return BatchNavigator(self.context.get_all_active(self.user),
                              self.request)

    @cachedproperty
    def matches(self):
        if not self.search_requested:
            return None
        pillarset = getUtility(IPillarNameSet)
        return pillarset.count_search_matches(self.search_string)

    @cachedproperty
    def search_results(self):
        search_string = self.search_string.lower()
        limit = self.max_results_to_display
        return getUtility(IPillarNameSet).search(search_string, limit)

    def tooManyResultsFound(self):
        return self.matches > self.max_results_to_display

    def latest(self):
        return self.context.get_all_active(self.user)[:5]


class ProductSetReviewLicensesView(LaunchpadFormView):
    """View for searching products to be reviewed."""

    schema = IProductReviewSearch
    label = 'Review projects'
    page_title = label

    full_row_field_names = [
        'search_text',
        'active',
        'project_reviewed',
        'license_approved',
        'licenses',
        'has_subscription',
        ]

    side_by_side_field_names = [
        ('created_after', 'created_before'),
        ('subscription_expires_after', 'subscription_expires_before'),
        ('subscription_modified_after', 'subscription_modified_before'),
        ]

    custom_widget(
        'licenses', CheckBoxMatrixWidget, column_count=4,
        orientation='vertical')
    custom_widget('active', LaunchpadRadioWidget,
                  _messageNoValue="(do not filter)")
    custom_widget('project_reviewed', LaunchpadRadioWidget,
                  _messageNoValue="(do not filter)")
    custom_widget('license_approved', LaunchpadRadioWidget,
                  _messageNoValue="(do not filter)")
    custom_widget('has_subscription', LaunchpadRadioWidget,
                  _messageNoValue="(do not filter)")
    custom_widget('created_after', DateWidget)
    custom_widget('created_before', DateWidget)
    custom_widget('subscription_expires_after', DateWidget)
    custom_widget('subscription_expires_before', DateWidget)
    custom_widget('subscription_modified_after', DateWidget)
    custom_widget('subscription_modified_before', DateWidget)

    @property
    def left_side_widgets(self):
        """Return the widgets for the left column."""
        return (self.widgets.get(left)
                for left, right in self.side_by_side_field_names)

    @property
    def right_side_widgets(self):
        """Return the widgets for the right column."""
        return (self.widgets.get(right)
                for left, right in self.side_by_side_field_names)

    @property
    def full_row_widgets(self):
        """Return all widgets that span all columns."""
        return (self.widgets[name] for name in self.full_row_field_names)

    @property
    def initial_values(self):
        """See `ILaunchpadFormView`."""
        search_params = {}
        for name in self.schema:
            search_params[name] = self.schema[name].default
        return search_params

    def forReviewBatched(self):
        """Return a `BatchNavigator` to review the matching projects."""
        # Calling _validate populates the data dictionary as a side-effect
        # of validation.
        data = {}
        self._validate(None, data)
        search_params = self.initial_values
        # Override the defaults with the form values if available.
        search_params.update(data)
        result = self.context.forReview(self.user, **search_params)
        return BatchNavigator(result, self.request, size=50)


def create_source_package_fields():
    return form.Fields(
        Choice(__name__='source_package_name',
               vocabulary='SourcePackageName',
               required=False),
        Choice(__name__='distroseries',
               vocabulary='DistroSeries',
               required=False),
        )


class ProjectAddStepOne(StepView):
    """product/+new view class for creating a new project."""

    _field_names = ['displayname', 'name', 'summary']
    label = "Register a project in Launchpad"
    schema = IProduct
    step_name = 'projectaddstep1'
    template = ViewPageTemplateFile('../templates/product-new.pt')
    page_title = "Register a project in Launchpad"

    custom_widget('displayname', TextWidget, displayWidth=50, label='Name')
    custom_widget('name', ProductNameWidget, label='URL')

    step_description = 'Project basics'
    search_results_count = 0

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        super(ProjectAddStepOne, self).setUpFields()
        self.form_fields = (self.form_fields + create_source_package_fields())

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        super(ProjectAddStepOne, self).setUpWidgets()
        self.widgets['source_package_name'].visible = False
        self.widgets['distroseries'].visible = False

    @property
    def _return_url(self):
        """This view is using the hidden _return_url field.

        It is not using the `ReturnToReferrerMixin`, since none
        of its other code is used, because multistep views can't
        have next_url set until the form submission succeeds.
        """
        return self.request.form.get('_return_url')

    @property
    def _next_step(self):
        """Define the next step.

        Subclasses can override this method to avoid having to override the
        more complicated `main_action` method for customization.  The actual
        property `next_step` must not be set before `main_action` is called.
        """
        return ProjectAddStepTwo

    def main_action(self, data):
        """See `MultiStepView`."""
        self.next_step = self._next_step

    # Make this a safe_action, so that the sourcepackage page can skip
    # the first step with a link (GET request) providing form values.
    continue_action = safe_action(StepView.continue_action)


class ProjectAddStepTwo(StepView, ProductLicenseMixin, ReturnToReferrerMixin):
    """Step 2 (of 2) in the +new project add wizard."""

    _field_names = ['displayname', 'name', 'summary', 'description',
                    'homepageurl', 'information_type', 'licenses',
                    'license_info', 'driver', 'bug_supervisor', 'owner']
    schema = IProduct
    step_name = 'projectaddstep2'
    template = ViewPageTemplateFile('../templates/product-new.pt')
    page_title = ProjectAddStepOne.page_title

    product = None

    custom_widget('displayname', TextWidget, displayWidth=50, label='Name')
    custom_widget('name', ProductNameWidget, label='URL')
    custom_widget('homepageurl', TextWidget, displayWidth=30)
    custom_widget('licenses', LicenseWidget)
    custom_widget('license_info', GhostWidget)
    custom_widget(
        'information_type',
        LaunchpadRadioWidgetWithDescription,
        vocabulary=InformationTypeVocabulary(types=PILLAR_INFORMATION_TYPES))

    custom_widget(
        'owner', PersonPickerWidget, header="Select the maintainer",
        show_create_team_link=True)
    custom_widget(
        'bug_supervisor', PersonPickerWidget, header="Set a bug supervisor",
        required=True, show_create_team_link=True)
    custom_widget(
        'driver', PersonPickerWidget, header="Set a driver",
        required=True, show_create_team_link=True)
    custom_widget(
        'disclaim_maintainer', CheckBoxWidget, cssClass="subordinate")

    def initialize(self):
        # The JSON cache must be populated before the super call, since
        # the form is rendered during LaunchpadFormView's initialize()
        # when an action is invoked.
        cache = IJSONRequestCache(self.request)
        json_dump_information_types(cache, PILLAR_INFORMATION_TYPES)
        super(ProjectAddStepTwo, self).initialize()

    @property
    def main_action_label(self):
        if self.source_package_name is None:
            return u'Complete Registration'
        else:
            return u'Complete registration and link to %s package' % (
                self.source_package_name.name)

    @property
    def _return_url(self):
        """This view is using the hidden _return_url field.

        It is not using the `ReturnToReferrerMixin`, since none
        of its other code is used, because multistep views can't
        have next_url set until the form submission succeeds.
        """
        return self.request.form.get('_return_url')

    @property
    def step_description(self):
        """See `MultiStepView`."""
        if self.search_results_count > 0:
            return 'Check for duplicate projects'
        return 'Registration details'

    @property
    def initial_values(self):
        return {
            'driver': self.user.name,
            'bug_supervisor': self.user.name,
            'owner': self.user.name,
            'information_type': InformationType.PUBLIC,
        }

    @property
    def enable_information_type(self):
        return not self.source_package_name

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        super(ProjectAddStepTwo, self).setUpFields()
        hidden_names = ['__visited_steps__', 'license_info']
        hidden_fields = self.form_fields.select(*hidden_names)

        if not self.enable_information_type:
            hidden_names.extend(
                ['information_type', 'bug_supervisor', 'driver'])

        visible_fields = self.form_fields.omit(*hidden_names)
        self.form_fields = (
            visible_fields + self._createDisclaimMaintainerField() +
            create_source_package_fields() + hidden_fields)

    def _createDisclaimMaintainerField(self):
        """Return a Bool field for disclaiming maintainer.

        If the registrant does not want to maintain the project she can select
        this checkbox and the ownership will be transfered to the registry
        admins team.
        """
        return form.Fields(
            Bool(__name__='disclaim_maintainer',
                 title=_("I do not want to maintain this project"),
                 description=_(
                     "Select if you are registering this project "
                     "for the purpose of taking an action (such as "
                     "reporting a bug) but you don't want to actually "
                     "maintain the project in Launchpad.  "
                     "The Registry Administrators team will become "
                     "the maintainers until a community maintainer "
                     "can be found.")),
            render_context=self.render_context)

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        super(ProjectAddStepTwo, self).setUpWidgets()
        self.widgets['name'].read_only = True
        # The "hint" is really more of an explanation at this point, but the
        # phrasing is different.
        self.widgets['name'].hint = (
            "When published, this will be the project's URL.")
        self.widgets['displayname'].visible = False
        self.widgets['source_package_name'].visible = False
        self.widgets['distroseries'].visible = False

        if (self.enable_information_type and
            IProductSet.providedBy(self.context)):
            self.widgets['information_type'].value = InformationType.PUBLIC

        # Set the source_package_release attribute on the licenses
        # widget, so that the source package's copyright info can be
        # displayed.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        if self.source_package_name is not None:
            release_list = ubuntu.getCurrentSourceReleases(
                [self.source_package_name])
            if len(release_list) != 0:
                self.widgets['licenses'].source_package_release = (
                    release_list.items()[0][1])

    @property
    def source_package_name(self):
        # setUpWidgets() doesn't have access to the data dictionary,
        # so the source package name needs to be converted from a string
        # into an object here.
        package_name_string = self.request.form.get(
            'field.source_package_name')
        if package_name_string is None:
            return None
        else:
            return getUtility(ISourcePackageNameSet).queryByName(
                package_name_string)

    @cachedproperty
    def _search_string(self):
        """Return the ORed terms to match."""
        search_text = SPACE.join((self.request.form['field.name'],
                                  self.request.form['field.displayname'],
                                  self.request.form['field.summary']))
        # OR all the terms together.
        return OR.join(search_text.split())

    @cachedproperty
    def search_results(self):
        """The full text search results.

        Search the pillars for any match on the name, display name, or
        summary.
        """
        # XXX BarryWarsaw 16-Apr-2009 do we need batching and should we return
        # more than 7 hits?
        return getUtility(IPillarNameSet).search(self._search_string, 7)

    @cachedproperty
    def search_results_count(self):
        """Return the count of matching `IPillar`s."""
        return getUtility(IPillarNameSet).count_search_matches(
            self._search_string)

    # StepView requires that its validate() method not be overridden, so make
    # sure this calls the right method.  validateStep() will call the licence
    # validation code.
    def validate(self, data):
        """See `MultiStepView`."""
        StepView.validate(self, data)

    def validateStep(self, data):
        """See `MultiStepView`."""
        ProductLicenseMixin.validate(self, data)
        if data.get('disclaim_maintainer') and self.errors:
            # The checkbox supersedes the owner text input.
            errors = [error for error in self.errors if error[0] == 'owner']
            for error in errors:
                self.errors.remove(error)

        if self.enable_information_type:
            if data.get('information_type') != InformationType.PUBLIC:
                for required_field in ('bug_supervisor', 'driver'):
                    if data.get(required_field) is None:
                        self.setFieldError(
                            required_field, 'Select a user or team.')

    @property
    def label(self):
        """See `LaunchpadFormView`."""
        return 'Register %s (%s) in Launchpad' % (
                self.request.form['field.displayname'],
                self.request.form['field.name'])

    def create_product(self, data):
        """Create the product from the user data."""
        # Get optional data.
        projectgroup = data.get('projectgroup')
        description = data.get('description')
        disclaim_maintainer = data.get('disclaim_maintainer', False)
        if disclaim_maintainer:
            owner = getUtility(ILaunchpadCelebrities).registry_experts
        else:
            owner = data.get('owner')

        return getUtility(IProductSet).createProduct(
            registrant=self.user,
            bug_supervisor=data.get('bug_supervisor', None),
            driver=data.get('driver', None),
            owner=owner,
            name=data['name'],
            displayname=data['displayname'],
            title=data['displayname'],
            summary=data['summary'],
            description=description,
            homepageurl=data.get('homepageurl'),
            licenses=data['licenses'],
            license_info=data['license_info'],
            information_type=data.get('information_type'),
            projectgroup=projectgroup)

    def link_source_package(self, product, data):
        if (data.get('distroseries') is not None
            and self.source_package_name is not None):
            source_package = data['distroseries'].getSourcePackage(
                self.source_package_name)
            source_package.setPackaging(
                product.development_focus, self.user)
            self.request.response.addInfoNotification(
                'Linked %s project to %s source package.' % (
                    product.displayname, self.source_package_name.name))

    def main_action(self, data):
        """See `MultiStepView`."""
        self.product = self.create_product(data)
        notify(ObjectCreatedEvent(self.product))
        self.link_source_package(self.product, data)

        if self._return_url is None:
            self.next_url = canonical_url(self.product)
        else:
            self.next_url = self._return_url


class ProductAddView(PillarViewMixin, MultiStepView):
    """The controlling view for product/+new."""

    page_title = ProjectAddStepOne.page_title
    total_steps = 2

    @property
    def first_step(self):
        """See `MultiStepView`."""
        return ProjectAddStepOne


class IProductEditPeopleSchema(Interface):
    """Defines the fields for the edit form.

    Specifically adds a new checkbox for transferring the maintainer role to
    Registry Administrators and makes the owner optional.
    """
    owner = copy_field(IProduct['owner'])
    owner.required = False

    driver = copy_field(IProduct['driver'])

    transfer_to_registry = Bool(
        title=_("I do not want to maintain this project"),
        required=False,
        description=_(
            "Select this if you no longer want to maintain this project in "
            "Launchpad.  Launchpad's Registry Administrators team will "
            "become the project's new maintainers."))


@implementer(IProductEditMenu)
class ProductEditPeopleView(LaunchpadEditFormView):
    """Enable editing of important people on the project."""

    label = "Change the roles of people"
    schema = IProductEditPeopleSchema
    field_names = [
        'owner',
        'transfer_to_registry',
        'driver',
        ]

    for_input = True

    # Initial value must be provided for the 'transfer_to_registry' field to
    # avoid having the non-existent attribute queried on the context and
    # failing.
    initial_values = {'transfer_to_registry': False}

    custom_widget('owner', PersonPickerWidget, header="Select the maintainer",
                  show_create_team_link=True)
    custom_widget('transfer_to_registry', CheckBoxWidget,
                  widget_class='field subordinate')
    custom_widget('driver', PersonPickerWidget, header="Select the driver",
                  show_create_team_link=True)

    @property
    def page_title(self):
        """The HTML page title."""
        return "Change the roles of %s's people" % self.context.title

    def validate(self, data):
        """Validate owner and transfer_to_registry are consistent.

        At most one may be specified.
        """
        xfer = data.get('transfer_to_registry', False)
        owner = data.get('owner')
        error = None
        if xfer:
            if owner:
                error = (
                    'You may not specify a new owner if you select the '
                    'checkbox.')
            else:
                celebrities = getUtility(ILaunchpadCelebrities)
                data['owner'] = celebrities.registry_experts
        else:
            if not owner:
                if self.errors and isinstance(
                    self.errors[0], WidgetInputError):
                    del self.errors[0]
                    error = (
                        'You must choose a valid person or team to be the '
                        'owner for %s.' % self.context.displayname)
                else:
                    error = (
                        'You must specify a maintainer or select the '
                        'checkbox.')
        if error:
            self.setFieldError('owner', error)

    @action(_('Save changes'), name='save')
    def save_action(self, action, data):
        """Save the changes to the associated people."""
        # Since 'transfer_to_registry' is not a real attribute on a Product,
        # it must be removed from data before the context is updated.
        if 'transfer_to_registry' in data:
            del data['transfer_to_registry']
        self.updateContextFromData(data)

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    @property
    def adapters(self):
        """See `LaunchpadFormView`"""
        return {IProductEditPeopleSchema: self.context}
