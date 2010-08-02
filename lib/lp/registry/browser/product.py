# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for products."""

__metaclass__ = type

__all__ = [
    'ProductAddSeriesView',
    'ProductAddView',
    'ProductAddViewBase',
    'ProductAdminView',
    'ProductBrandingView',
    'ProductBugsMenu',
    'ProductConfigureBase',
    'ProductConfigureAnswersView',
    'ProductConfigureBlueprintsView',
    'ProductConfigureTranslationsView',
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
    'ProductSeriesView',
    'ProductSetBreadcrumb',
    'ProductSetFacets',
    'ProductSetNavigation',
    'ProductSetReviewLicensesView',
    'ProductSetView',
    'ProductSpecificationsMenu',
    'ProductView',
    'SortSeriesMixin',
    'ProjectAddStepOne',
    'ProjectAddStepTwo',
    ]


from cgi import escape
from datetime import datetime, timedelta
from operator import attrgetter

import pytz

from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser import CheckBoxWidget, TextAreaWidget, TextWidget
from zope.lifecycleevent import ObjectCreatedEvent
from zope.interface import implements, Interface
from zope.formlib import form
from zope.schema import Bool, Choice
from zope.schema.vocabulary import (
    SimpleVocabulary, SimpleTerm)
from zope.security.proxy import removeSecurityProxy

from z3c.ptcompat import ViewPageTemplateFile

from canonical.cachedproperty import cachedproperty

from canonical.config import config
from lazr.delegates import delegates
from lazr.restful.interface import copy_field
from canonical.launchpad import _
from canonical.launchpad.fields import PillarAliases, PublicPersonChoice
from lp.app.interfaces.headings import IEditableContextTitle
from lp.blueprints.browser.specificationtarget import (
    HasSpecificationsMenuMixin)
from lp.bugs.interfaces.bugtask import RESOLVED_BUGTASK_STATUSES
from lp.code.browser.sourcepackagerecipelisting import HasRecipesMenuMixin
from lp.services.worlddata.interfaces.country import ICountry
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.webapp.interfaces import (
    ILaunchBag, NotFoundError, UnsafeFormGetSubmissionError)
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.registry.interfaces.product import IProductReviewSearch, License
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.product import (
    IProduct, IProductSet, LicenseStatus)
from lp.registry.interfaces.productrelease import (
    IProductRelease, IProductReleaseSet)
from lp.registry.interfaces.productseries import IProductSeries
from canonical.launchpad import helpers
from lp.registry.browser.announcement import HasAnnouncementsView
from lp.registry.browser.branding import BrandingChangeView
from lp.code.browser.branchref import BranchRef
from lp.bugs.browser.bugtask import (
    BugTargetTraversalMixin, get_buglisting_search_filter_url)
from lp.registry.browser.distribution import UsesLaunchpadMixin
from lp.registry.browser.menu import (
    IRegistryCollectionNavigationMenu, RegistryCollectionActionMenuBase)
from lp.registry.browser.pillar import PillarBugsMenu
from lp.answers.browser.faqtarget import FAQTargetNavigationMixin
from canonical.launchpad.browser.feeds import FeedsMixin
from lp.registry.browser.pillar import PillarView
from lp.registry.browser.productseries import get_series_branch_error
from lp.translations.browser.customlanguagecode import (
    HasCustomLanguageCodesTraversalMixin)
from canonical.launchpad.browser.multistep import MultiStepView, StepView
from lp.answers.browser.questiontarget import (
    QuestionTargetFacetMixin, QuestionTargetTraversalMixin)
from lp.registry.browser.structuralsubscription import (
    StructuralSubscriptionMenuMixin,
    StructuralSubscriptionTargetTraversalMixin)
from canonical.launchpad.mail import format_address, simple_sendmail
from canonical.launchpad.webapp import (
    ApplicationMenu, canonical_url, enabled_with_permission, LaunchpadView,
    Link, Navigation, sorted_version_numbers, StandardLaunchpadFacets,
    stepthrough, stepto, structured)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.launchpadform import (
    action, custom_widget, LaunchpadEditFormView, LaunchpadFormView,
    ReturnToReferrerMixin)
from canonical.launchpad.webapp.menu import NavigationMenu
from canonical.launchpad.webapp.tales import MenuAPI
from canonical.widgets.popup import PersonPickerWidget
from canonical.widgets.date import DateWidget
from canonical.widgets.itemswidgets import (
    CheckBoxMatrixWidget, LaunchpadRadioWidget)
from canonical.widgets.lazrjs import TextLineEditorWidget
from canonical.widgets.product import (
    LicenseWidget, GhostWidget, ProductNameWidget)
from canonical.widgets.textwidgets import StrippedTextWidget


OR = '|'
SPACE = ' '


class ProductNavigation(
    Navigation, BugTargetTraversalMixin,
    FAQTargetNavigationMixin, HasCustomLanguageCodesTraversalMixin,
    QuestionTargetTraversalMixin, StructuralSubscriptionTargetTraversalMixin):

    usedfor = IProduct

    @stepto('.bzr')
    def dotbzr(self):
        if self.context.development_focus.branch:
            return BranchRef(self.context.development_focus.branch)
        else:
            return None

    @stepthrough('+spec')
    def traverse_spec(self, name):
        return self.context.getSpecification(name)

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
    """Adds license validation and requests reviews of licenses.

    Subclasses must inherit from Launchpad[Edit]FormView as well.

    Requires the "product" attribute be set in the child
    classes' action handler.
    """

    def validate(self, data):
        """Validate 'licenses' and 'license_info'.

        'licenses' must not be empty unless the product already
        exists and never has had a license set.

        'license_info' must not be empty if "Other/Proprietary"
        or "Other/Open Source" is checked.
        """
        licenses = data.get('licenses', [])
        license_widget = self.widgets.get('licenses')
        if (len(licenses) == 0 and
            license_widget is not None and
            not license_widget.allow_pending_license):
            # License is optional on +edit page if not already set.
            self.setFieldError(
                'licenses',
                'You must select at least one license.  If you select '
                'Other/Proprietary or Other/OpenSource you must include a '
                'description of the license.')
        elif License.OTHER_PROPRIETARY in licenses:
            if not data.get('license_info'):
                self.setFieldError(
                    'license_info',
                    'A description of the "Other/Proprietary" '
                    'license you checked is required.')
        elif License.OTHER_OPEN_SOURCE in licenses:
            if not data.get('license_info'):
                self.setFieldError(
                    'license_info',
                    'A description of the "Other/Open Source" '
                    'license you checked is required.')
        else:
            # Launchpad is ok with all licenses used in this project.
            pass

    def notifyCommercialMailingList(self):
        """Email feedback@canonical.com to review product license."""
        if (License.OTHER_PROPRIETARY in self.product.licenses
            or License.OTHER_OPEN_SOURCE in self.product.licenses):
            review_needed = True
        elif (len(self.product.licenses) == 1
            and License.DONT_KNOW in self.product.licenses):
            review_needed = False
        else:
            # The project has a recognized license.
            return

        def indent(text):
            if text is None:
                return None
            text = '\n    '.join(line for line in text.split('\n'))
            text = '    ' + text
            return text

        user = getUtility(ILaunchBag).user
        user_address = format_address(
            user.displayname, user.preferredemail.email)
        from_address = format_address(
            "Launchpad", config.canonical.noreply_from_address)
        commercial_address = format_address(
            'Commercial', 'commercial@launchpad.net')
        license_titles = '\n'.join(
            license.title for license in self.product.licenses)
        substitutions = dict(
            user_browsername=user.displayname,
            user_name=user.name,
            product_name=self.product.name,
            product_url=canonical_url(self.product),
            product_summary=indent(self.product.summary),
            license_titles=indent(license_titles),
            license_info=indent(self.product.license_info))
        if review_needed:
            # Email the Commercial team that a project needs review.
            subject = (
                "Project License Submitted for %(product_name)s "
                "by %(user_name)s" % substitutions)
            template = helpers.get_email_template('product-license.txt')
            message = template % substitutions
            simple_sendmail(
                from_address, commercial_address,
                subject, message, headers={'Reply-To': user_address})
        # Email the user about license policy.
        subject = (
            "License information for %(product_name)s "
            "in Launchpad" % substitutions)
        template = helpers.get_email_template('product-other-license.txt')
        message = template % substitutions
        simple_sendmail(
            from_address, user_address,
            subject, message, headers={'Reply-To': commercial_address})
        # Inform that Launchpad recognized the license change.
        self._addLicenseChangeToReviewWhiteboard()
        self.request.response.addInfoNotification(_(
            "Launchpad is free to use for software under approved "
            "licenses. The Launchpad team will be in contact with "
            "you soon."))

    def _addLicenseChangeToReviewWhiteboard(self):
        """Update the whiteboard for the reviewer's benefit."""
        now = self._formatDate()
        whiteboard = 'User notified of license policy on %s.' % now
        naked_product = removeSecurityProxy(self.product)
        if naked_product.reviewer_whiteboard is None:
            naked_product.reviewer_whiteboard = whiteboard
        else:
            naked_product.reviewer_whiteboard += '\n' + whiteboard

    def _formatDate(self, now=None):
        """Return the date formatted for messages."""
        if now is None:
            now = datetime.now(tz=pytz.UTC)
        return now.strftime('%Y-%m-%d')


class ProductFacets(QuestionTargetFacetMixin, StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IProduct."""

    usedfor = IProduct

    enable_only = ['overview', 'bugs', 'answers', 'specifications',
                   'translations', 'branches']

    links = StandardLaunchpadFacets.links

    def overview(self):
        text = 'Overview'
        summary = 'General information about %s' % self.context.displayname
        return Link('', text, summary)

    def bugs(self):
        text = 'Bugs'
        summary = 'Bugs reported about %s' % self.context.displayname
        return Link('', text, summary)

    def branches(self):
        text = 'Code'
        summary = 'Branches for %s' % self.context.displayname
        return Link('', text, summary)

    def specifications(self):
        text = 'Blueprints'
        summary = 'Feature specifications for %s' % self.context.displayname
        return Link('', text, summary)

    def translations(self):
        text = 'Translations'
        summary = 'Translations of %s in Launchpad' % self.context.displayname
        return Link('', text, summary)


class ProductInvolvementView(PillarView):
    """Encourage configuration of involvement links for projects."""

    has_involvement = True
    show_progress = True

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
            self.official_malone or self.context.bugtracker is not None)
        states['configure_answers'] = self.official_answers
        states['configure_translations'] = self.official_rosetta
        states['configure_codehosting'] = (
            self.context.development_focus.branch is not None)
        return states

    @property
    def configuration_links(self):
        """The enabled involvement links.

        Returns a list of dicts keyed by:
        'link' -- the menu link, and
        'configured' -- a boolean representing the configuration status.
        """
        overview_menu = MenuAPI(self.context).overview
        series_menu = MenuAPI(self.context.development_focus).overview
        configuration_names = [
            'configure_bugtracker',
            'configure_answers',
            'configure_translations',
            #'configure_blueprints',
            ]
        config_list = []
        config_statuses = self.configuration_states
        for key in configuration_names:
            config_list.append(dict(link=overview_menu[key],
                                    configured=config_statuses[key]))

        # Add the branch configuration in separately.
        set_branch = series_menu['set_branch']
        set_branch.text = 'Configure project branch'
        set_branch.configured = (
            )
        config_list.append(
            dict(link=set_branch,
                 configured=config_statuses['configure_codehosting']))
        return config_list

    @property
    def registration_completeness(self):
        """The percent complete for registration."""
        configured = 0
        config_statuses = self.configuration_states
        for key, value in config_statuses.items():
            if value:
                configured += 1
        scale = 100
        done = int(float(configured) / len(config_statuses) * scale)
        undone = scale - done
        return dict(done=done, undone=undone)


class ProductNavigationMenu(NavigationMenu):

    usedfor = IProduct
    facet = 'overview'
    links = [
        'details',
        'announcements',
        'branchvisibility',
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

    @enabled_with_permission('launchpad.Admin')
    def branchvisibility(self):
        text = 'Branch Visibility Policy'
        return Link('+branchvisibility', text)


class ProductEditLinksMixin(StructuralSubscriptionMenuMixin):
    """A mixin class for menus that need Product edit links."""

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def configure_bugtracker(self):
        text = 'Configure bug tracker'
        summary = 'Specify where bugs are tracked for this project'
        return Link('+configure-bugtracker', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def configure_translations(self):
        text = 'Configure translations'
        summary = 'Allow users to submit translations for this project'
        return Link('+configure-translations', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def configure_answers(self):
        text = 'Configure support tracker'
        summary = 'Allow users to ask questions on this project'
        return Link('+configure-answers', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def configure_blueprints(self):
        text = 'Configure blueprints'
        summary = 'Enable tracking of specifications and meetings'
        return Link('+configure-blueprints', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def branding(self):
        text = 'Change branding'
        return Link('+branding', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change people'
        return Link('+edit-people', text, icon='edit')

    @enabled_with_permission('launchpad.ProjectReview')
    def review_license(self):
        text = 'Review project'
        return Link('+review-license', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')


class IProductEditMenu(Interface):
    """A marker interface for the 'Change details' navigation menu."""


class IProductActionMenu(Interface):
    """A marker interface for the global action navigation menu."""


class ProductActionNavigationMenu(NavigationMenu, ProductEditLinksMixin):
    """A sub-menu for acting upon a Product."""

    usedfor = IProductActionMenu
    facet = 'overview'
    title = 'Actions'
    links = ('edit', 'review_license', 'administer', 'subscribe')


class ProductOverviewMenu(ApplicationMenu, ProductEditLinksMixin,
                          HasRecipesMenuMixin):

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
        'milestones',
        'downloads',
        'announce',
        'announcements',
        'administer',
        'review_license',
        'branch_add',
        'branchvisibility',
        'rdf',
        'branding',
        'view_recipes',
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

    def downloads(self):
        text = 'Downloads'
        return Link('+download', text, icon='info')

    @enabled_with_permission('launchpad.Admin')
    def branchvisibility(self):
        text = 'Branch Visibility Policy'
        return Link('+branchvisibility', text, icon='edit')

    def branch_add(self):
        text = 'Register a branch'
        summary = "Register a new Bazaar branch for this project"
        return Link('+addbranch', text, summary, icon='add')


class ProductBugsMenu(PillarBugsMenu,
                      ProductEditLinksMixin):

    usedfor = IProduct
    facet = 'bugs'
    links = (
        'filebug',
        'bugsupervisor',
        'securitycontact',
        'cve',
        'subscribe',
        'configure_bugtracker',
        )
    configurable_bugtracker = True


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


class ProductSetFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for the IProductSet."""

    usedfor = IProductSet

    enable_only = ['overview', 'branches']


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
    delegates(IProduct, 'product')

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


class SeriesWithReleases:
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
    delegates(IProductSeries, 'series')

    def __init__(self, series, parent):
        self.series = series
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

    @property
    def css_class(self):
        """The highlighted, unhighlighted, or dimmed CSS class."""
        if self.is_development_focus:
            return 'highlighted'
        elif self.status == SeriesStatus.OBSOLETE:
            return 'dimmed'
        else:
            return 'unhighlighted'


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
    delegates(IProductRelease, 'release')

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


class ProductView(HasAnnouncementsView, SortSeriesMixin, FeedsMixin,
                  ProductDownloadFileMixin, UsesLaunchpadMixin):

    __used_for__ = IProduct
    implements(IProductActionMenu, IEditableContextTitle)

    def __init__(self, context, request):
        HasAnnouncementsView.__init__(self, context, request)
        self.form = request.form_ng

    def initialize(self):
        self.status_message = None
        self.title_edit_widget = TextLineEditorWidget(
            self.context, 'title',
            canonical_url(self.context, view_name='+edit'),
            id="product-title", title="Edit this title")
        if self.context.programminglang is None:
            additional_arguments = dict(
                default_text='Not yet specified',
                initial_value_override='',
                )
        else:
            additional_arguments = {}
        self.languages_edit_widget = TextLineEditorWidget(
            self.context, 'programminglang',
            canonical_url(self.context, view_name='+edit'),
            id='programminglang', title='Edit programming languages',
            tag='span', public_attribute='programming_language',
            accept_empty=True,
            width='9em',
            **additional_arguments)
        self.show_programming_languages = bool(
            self.context.programminglang or
            check_permission('launchpad.Edit', self.context))

    @property
    def show_license_status(self):
        return self.context.license_status != LicenseStatus.OPEN_SOURCE

    @property
    def freshmeat_url(self):
        if self.context.freshmeatproject:
            return ("http://freshmeat.net/projects/%s"
                % self.context.freshmeatproject)
        return None

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
                self.context.freshmeatproject or
                self.context.wikiurl or
                self.context.screenshotsurl or
                self.context.downloadurl)

    @property
    def external_links(self):
        """The project's external links.

        The home page link is not included because its link must have the
        rel=nofollow attribute.
        """
        from canonical.launchpad.webapp.menu import MenuLink
        urls = [
            ('Sourceforge project', self.sourceforge_url),
            ('Freshmeat record', self.freshmeat_url),
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
                    [self.freshmeat_url, self.sourceforge_url])

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def projproducts(self):
        """Return a list of other products from the same project as this
        product, excluding this product"""
        if self.context.project is None:
            return []
        return [product for product in self.context.project.products
                        if product.id != self.context.id]

    def getClosedBugsURL(self, series):
        status = [status.title for status in RESOLVED_BUGTASK_STATUSES]
        url = canonical_url(series) + '/+bugs'
        return get_buglisting_search_filter_url(url, status=status)

    @property
    def requires_commercial_subscription(self):
        """Whether to display notice to purchase a commercial subscription."""
        return (len(self.context.licenses) > 0
                and self.context.commercial_subscription_is_due)

    @property
    def can_purchase_subscription(self):
        return (check_permission('launchpad.Edit', self.context)
                and not self.context.qualifies_for_free_hosting)

    @cachedproperty
    def effective_driver(self):
        """Return the product driver or the project driver."""
        if self.context.driver is not None:
            driver = self.context.driver
        elif (self.context.project is not None and
              self.context.project.driver is not None):
            driver = self.context.project.driver
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


class ProductPackagesView(LaunchpadView):
    """View for displaying product packaging"""

    label = 'Linked packages'
    page_title = label

    @cachedproperty
    def series_packages(self):
        """A hierarchy of product series, packaging and field data.

        A dict of series and packagings. Each packaging is a dict of the
        packaging and a hidden HTML field for forms:
           [{series: <hoary>,
             packagings: {
                packaging: <packaging>,
                field: '<input type=''hidden' ...>},
                }]
        """
        packaged_series = []
        for series in self.context.series:
            packagings = []
            for packaging in series.packagings:
                packagings.append(packaging)
            packaged_series.append(dict(
                series=series, packagings=packagings))
        return packaged_series

    @property
    def distro_packaging(self):
        """This method returns a representation of the product packagings
        for this product, in a special structure used for the
        product-distros.pt page template.

        Specifically, it is a list of "distro" objects, each of which has a
        title, and an attribute "packagings" which is a list of the relevant
        packagings for this distro and product.
        """
        # First get a list of all relevant packagings.
        all_packagings = []
        for series in self.context.series:
            for packaging in series.packagings:
                all_packagings.append(packaging)
        # We sort it so that the packagings will always be displayed in the
        # distroseries version, then productseries name order.
        all_packagings.sort(key=lambda a: (a.distroseries.version,
            a.productseries.name, a.id))

        distros = {}
        for packaging in all_packagings:
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


class ProductPackagesPortletView(LaunchpadFormView):
    """View class for product packaging portlet."""

    schema = Interface
    package_field_name = 'distributionsourcepackage'
    custom_widget(
        package_field_name, LaunchpadRadioWidget, orientation='vertical')
    suggestions = None
    max_suggestions = 8
    other_package = object()
    not_packaged = object()
    initial_focus_widget = None

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
        if self.user is None:
            return False
        date_next_suggest_packaging = self.context.date_next_suggest_packaging
        return (
            date_next_suggest_packaging is None
            or date_next_suggest_packaging <= datetime.now(tz=pytz.UTC))

    @property
    def initial_values(self):
        """See `LaunchpadFormView`."""
        return {self.package_field_name: self.other_package}

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        super(ProductPackagesPortletView, self).setUpFields()
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        distro_source_packages = ubuntu.searchSourcePackages(
            self.context.name, has_packaging=False,
            publishing_distroseries=ubuntu.currentseries)
        # Based upon the matches, create a new vocabulary with
        # term descriptions that include a link to the source package.
        self.suggestions = []
        vocab_terms = []
        for package in distro_source_packages[:self.max_suggestions]:
            if package.development_version.currentrelease is not None:
                self.suggestions.append(package)
                item_url = canonical_url(package)
                description = """<a href="%s">%s</a>""" % (
                    item_url, escape(package.name))
                vocab_terms.append(
                    SimpleTerm(package, package.name, description))
        # Add an option to represent the user's decision to choose a
        # different package. Note that source packages cannot have uppercase
        # names with underscores, so the name is safe to use.
        description = 'Choose another Ubuntu package'
        vocab_terms.append(
            SimpleTerm(self.other_package, 'OTHER_PACKAGE', description))
        vocabulary = SimpleVocabulary(vocab_terms)
        # Add an option to represent that the project is not packaged in
        # Ubuntu.
        description = 'This project is not packaged in Ubuntu'
        vocab_terms.append(
            SimpleTerm(self.not_packaged, 'NOT_PACKAGED', description))
        vocabulary = SimpleVocabulary(vocab_terms)
        series_display_name = ubuntu.currentseries.displayname
        self.form_fields = form.Fields(
            Choice(__name__=self.package_field_name,
                   title=_('Ubuntu %s packages') % series_display_name,
                   default=None,
                   vocabulary=vocabulary,
                   required=True))

    @action(_('Set Ubuntu Package Information'), name='link')
    def link(self, action, data):
        product = self.context
        dsp = data.get(self.package_field_name)
        product_series = product.development_focus
        if dsp is self.other_package:
            # The user wants to link an alternate package to this project.
            self.next_url = canonical_url(
                product_series, view_name="+ubuntupkg")
            return
        if dsp is self.not_packaged:
            year_from_now = datetime.now(tz=pytz.UTC) + timedelta(days=365)
            self.context.date_next_suggest_packaging = year_from_now
            self.next_url = self.request.getURL()
            return
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        product_series.setPackaging(ubuntu.currentseries,
                                    dsp.sourcepackagename,
                                    self.user)
        self.request.response.addInfoNotification(
            'This project was linked to the source package "%s"' %
            dsp.displayname)
        self.next_url = self.request.getURL()


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
    __used_for__ = IProduct

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


class ProductBrandingView(BrandingChangeView):
    """A view to set branding."""
    implements(IProductEditMenu)

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


class ProductConfigureBase(ReturnToReferrerMixin, LaunchpadEditFormView):
    implements(IProductEditMenu)
    schema = IProduct

    @property
    def page_title(self):
        return self.label

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class ProductConfigureBlueprintsView(ProductConfigureBase):
    """View class to configure the Launchpad Blueprints for a project."""

    label = "Configure Blueprints"
    field_names = [
        "official_blueprints",
        ]


class ProductConfigureTranslationsView(ProductConfigureBase):
    """View class to configure the Launchpad Translations for a project."""

    label = "Configure Translations"
    field_names = [
        "official_rosetta",
        ]


class ProductConfigureAnswersView(ProductConfigureBase):
    """View class to configure the Launchpad Answers for a project."""

    label = "Configure Answers"
    field_names = [
        "official_answers",
        ]


class ProductEditView(ProductLicenseMixin, LaunchpadEditFormView):
    """View class that lets you edit a Product object."""

    implements(IProductEditMenu)

    label = "Edit details"
    schema = IProduct
    field_names = [
        "displayname",
        "title",
        "summary",
        "description",
        "project",
        "homepageurl",
        "sourceforgeproject",
        "freshmeatproject",
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

    @property
    def page_title(self):
        """The HTML page title."""
        return "Change %s's details" % self.context.title

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        super(ProductEditView, self).setUpWidgets()
        # Licenses are optional on +edit page if they have not already
        # been set. Subclasses may not have 'licenses' widget.
        # ('licenses' in self.widgets) is broken.
        if (len(self.context.licenses) == 0 and
            self.widgets.get('licenses') is not None):
            self.widgets['licenses'].allow_pending_license = True

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
        previous_licenses = self.context.licenses
        self.updateContextFromData(data)
        # only send email the first time licenses are set
        if len(previous_licenses) == 0:
            # self.product is expected by notifyCommercialMailingList
            self.product = self.context
            self.notifyCommercialMailingList()

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        if self.context.active:
            return canonical_url(self.context)
        else:
            return canonical_url(getUtility(IProductSet))

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return self.next_url


class ProductValidationMixin:

    def validate_private_bugs(self, data):
        """Perform validation for the private bugs setting."""
        if data.get('private_bugs') and self.context.bug_supervisor is None:
            self.setFieldError('private_bugs',
                structured(
                    'Set a <a href="%s/+bugsupervisor">bug supervisor</a> '
                    'for this project first.',
                    canonical_url(self.context, rootsite="bugs")))

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
    field_names = ["name", "owner", "active", "autoupdate", "private_bugs"]

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
        super(ProductAdminView, self).setUpFields()
        self.form_fields = (self._createAliasesField() + self.form_fields
                            + self._createRegistrantField())

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
        self.validate_private_bugs(data)
        self.validate_deactivation(data)

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)


class ProductReviewLicenseView(ReturnToReferrerMixin,
                               ProductEditView, ProductValidationMixin):
    """A view to review a project and change project privileges."""
    label = "Review project"
    field_names = [
        "license_reviewed",
        "license_approved",
        "active",
        "private_bugs",
        "reviewer_whiteboard",
        ]

    @property
    def page_title(self):
        """The HTML page title."""
        return 'Review %s' % self.context.title

    def validate(self, data):
        """See `LaunchpadFormView`."""

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
                # An Other/Open Source license was specified so it may be
                # approved.
                pass

        # Private bugs can only be enabled if the product has a bug
        # supervisor.
        self.validate_private_bugs(data)
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


class ProductSeriesView(ProductView):
    """A view for showing a product's series."""

    label = 'timeline'
    page_title = label


class ProductRdfView:
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile(
        '../templates/product-rdf.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Render RDF output, and return it as a string encoded in UTF-8.

        Render the page template to produce RDF output.
        The return value is string data encoded in UTF-8.

        As a side-effect, HTTP headers are set for the mime type
        and filename for download."""
        self.request.response.setHeader('Content-Type', 'application/rdf+xml')
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename=%s.rdf' %
                                        self.context.name)
        unicodedata = self.template()
        encodeddata = unicodedata.encode('utf-8')
        return encodeddata


class Icon:
    """An icon for use with image:icon."""

    def __init__(self, library_id):
        self.library_alias = getUtility(ILibraryFileAliasSet)[library_id]

    def getURL(self):
        return self.library_alias.getURL()


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

    @enabled_with_permission('launchpad.ProjectReview')
    def review_licenses(self):
        return Link('+review-licenses', 'Review projects', icon='edit')

    def view_all_projects(self):
        return Link('+all', 'Show all projects', icon='list')


class ProductSetView(LaunchpadView):
    """View for products index page."""

    implements(IRegistryCollectionNavigationMenu)

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
        return BatchNavigator(self.context.all_active, self.request)

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


class ProductSetReviewLicensesView(LaunchpadFormView):
    """View for searching products to be reviewed."""

    schema = IProductReviewSearch
    label = 'Review projects'

    full_row_field_names = [
        'search_text',
        'active',
        'license_reviewed',
        'license_approved',
        'license_info_is_empty',
        'licenses',
        'has_zero_licenses',
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
    custom_widget('license_reviewed', LaunchpadRadioWidget,
                  _messageNoValue="(do not filter)")
    custom_widget('license_approved', LaunchpadRadioWidget,
                  _messageNoValue="(do not filter)")
    custom_widget('license_info_is_empty', LaunchpadRadioWidget,
                  _messageNoValue="(do not filter)")
    custom_widget('has_zero_licenses', LaunchpadRadioWidget,
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

    def forReviewBatched(self):
        """Return a `BatchNavigator` to review the matching projects."""
        # Calling _validate populates the data dictionary as a side-effect
        # of validation.
        data = {}
        self._validate(None, data)
        # Get default values from the schema since the form defaults
        # aren't available until the search button is pressed.
        search_params = {}
        for name in self.schema:
            search_params[name] = self.schema[name].default
        # Override the defaults with the form values if available.
        search_params.update(data)
        return BatchNavigator(self.context.forReview(**search_params),
                              self.request, size=100)


class ProductAddViewBase(ProductLicenseMixin, LaunchpadFormView):
    """Abstract class for adding a new product.

    ProductLicenseMixin requires the "product" attribute be set in the
    child classes' action handler.
    """

    schema = IProduct
    product = None
    field_names = ['name', 'displayname', 'title', 'summary',
                   'description', 'homepageurl', 'sourceforgeproject',
                   'freshmeatproject', 'wikiurl', 'screenshotsurl',
                   'downloadurl', 'programminglang',
                   'licenses', 'license_info']
    custom_widget(
        'licenses', LicenseWidget, column_count=3, orientation='vertical')
    custom_widget('homepageurl', TextWidget, displayWidth=30)
    custom_widget('screenshotsurl', TextWidget, displayWidth=30)
    custom_widget('wikiurl', TextWidget, displayWidth=30)
    custom_widget('downloadurl', TextWidget, displayWidth=30)

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        assert self.product is not None, 'No product has been created'
        return canonical_url(self.product)


class ProjectAddStepOne(StepView):
    """product/+new view class for creating a new project."""

    _field_names = ['displayname', 'name', 'title', 'summary']
    label = "Register a project in Launchpad"
    schema = IProduct
    step_name = 'projectaddstep1'
    template = ViewPageTemplateFile('../templates/product-new.pt')
    page_title = "Register a project in Launchpad"

    custom_widget('displayname', TextWidget, displayWidth=50, label='Name')
    custom_widget('name', ProductNameWidget, label='URL')

    step_description = 'Project basics'
    search_results_count = 0

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
        self.request.form['displayname'] = data['displayname']
        self.request.form['name'] = data['name'].lower()
        self.request.form['summary'] = data['summary']


class ProjectAddStepTwo(StepView, ProductLicenseMixin, ReturnToReferrerMixin):
    """Step 2 (of 2) in the +new project add wizard."""

    _field_names = ['displayname', 'name', 'title', 'summary',
                    'description', 'licenses', 'license_info',
                    ]
    main_action_label = u'Complete Registration'
    schema = IProduct
    step_name = 'projectaddstep2'
    template = ViewPageTemplateFile('../templates/product-new.pt')
    page_title = ProjectAddStepOne.page_title

    product = None

    custom_widget('displayname', TextWidget, displayWidth=50, label='Name')
    custom_widget('name', ProductNameWidget, label='URL')
    custom_widget('licenses', LicenseWidget)
    custom_widget('license_info', GhostWidget)

    @property
    def step_description(self):
        """See `MultiStepView`."""
        if self.search_results_count > 0:
            return 'Check for duplicate projects'
        return 'Registration details'

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        super(ProjectAddStepTwo, self).setUpFields()
        self.form_fields = (self.form_fields +
                            self._createDisclaimMaintainerField())

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
        self.widgets['name'].hint = ('When published, '
                                     "this will be the project's URL.")
        self.widgets['displayname'].visible = False

    @cachedproperty
    def _search_string(self):
        """Return the ORed terms to match."""
        search_text = SPACE.join((self.request.form['name'],
                                  self.request.form['displayname'],
                                  self.request.form['summary']))
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
        pillar_set = getUtility(IPillarNameSet)
        return pillar_set.search(self._search_string, 7)

    @cachedproperty
    def search_results_count(self):
        """Return the count of matching `IPillar`s."""
        pillar_set = getUtility(IPillarNameSet)
        return pillar_set.count_search_matches(self._search_string)

    # StepView requires that its validate() method not be overridden, so make
    # sure this calls the right method.  validateStep() will call the license
    # validation code.
    def validate(self, data):
        """See `MultiStepView`."""
        StepView.validate(self, data)

    def validateStep(self, data):
        """See `MultiStepView`."""
        ProductLicenseMixin.validate(self, data)

    @property
    def label(self):
        """See `LaunchpadFormView`."""
        return 'Register %s (%s) in Launchpad' % (
                self.request.form['displayname'], self.request.form['name'])

    def create_product(self, data):
        """Create the product from the user data."""
        # Get optional data.
        project = data.get('project')
        description = data.get('description')
        disclaim_maintainer = data.get('disclaim_maintainer', False)
        if disclaim_maintainer:
            owner = getUtility(ILaunchpadCelebrities).registry_experts
        else:
            owner = self.user
        return getUtility(IProductSet).createProduct(
            registrant=self.user,
            owner=owner,
            name=data['name'],
            displayname=data['displayname'],
            title=data['title'],
            summary=data['summary'],
            description=description,
            licenses=data['licenses'],
            license_info=data['license_info'],
            project=project)

    def main_action(self, data):
        """See `MultiStepView`."""
        self.product = self.create_product(data)
        self.notifyCommercialMailingList()
        notify(ObjectCreatedEvent(self.product))
        self.next_url = canonical_url(self.product)


class ProductAddView(MultiStepView):
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

    transfer_to_registry =  Bool(
        title=_("I do not want to maintain this project"),
        required=False,
        description=_(
            "Select this if you no longer want to maintain this project in "
            "Launchpad.  Launchpad's Registry Administrators team will "
            "become the project's new maintainers."))


class ProductEditPeopleView(LaunchpadEditFormView):
    """Enable editing of important people on the project."""

    implements(IProductEditMenu)

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
                  include_create_team_link=True)
    custom_widget('transfer_to_registry', CheckBoxWidget,
                  widget_class='field subordinate')
    custom_widget('driver', PersonPickerWidget, header="Select the driver",
                  include_create_team_link=True)

    @property
    def page_title(self):
        """The HTML page title."""
        return "Change the roles of %s's people" % self.context.title

    def validate(self, data):
        """Validate owner and transfer_to_registry are consistent.

        At most one may be specified.
        """
        # If errors have already been found we can skip validation.
        if len(self.errors) > 0:
            return
        xfer = data.get('transfer_to_registry', False)
        owner = data.get('owner')
        if owner is not None and xfer:
            self.setFieldError(
                'owner',
                'You may not specify a new owner if you '
                'select the checkbox.')
        elif xfer:
            data['owner'] = getUtility(ILaunchpadCelebrities).registry_experts
        elif owner is None:
            self.setFieldError(
                'owner',
                'You must specify a maintainer or select '
                'the checkbox.')

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
