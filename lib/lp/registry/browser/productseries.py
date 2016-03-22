# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes for `IProductSeries`."""

__metaclass__ = type

__all__ = [
    'get_series_branch_error',
    'ProductSeriesBreadcrumb',
    'ProductSeriesBugsMenu',
    'ProductSeriesDeleteView',
    'ProductSeriesDetailedDisplayView',
    'ProductSeriesEditView',
    'ProductSeriesFileBugRedirect',
    'ProductSeriesInvolvedMenu',
    'ProductSeriesInvolvementView',
    'ProductSeriesNavigation',
    'ProductSeriesOverviewMenu',
    'ProductSeriesOverviewNavigationMenu',
    'ProductSeriesRdfView',
    'ProductSeriesReviewView',
    'ProductSeriesSetBranchView',
    'ProductSeriesSpecificationsMenu',
    'ProductSeriesUbuntuPackagingView',
    'ProductSeriesView',
    ]

from operator import attrgetter

from z3c.ptcompat import ViewPageTemplateFile
from zope.component import getUtility
from zope.formlib import form
from zope.formlib.widgets import (
    TextAreaWidget,
    TextWidget,
    )
from zope.interface import (
    implementer,
    Interface,
    )
from zope.schema import Choice
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from lp import _
from lp.app.browser.informationtype import InformationTypePortletMixin
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.app.browser.tales import MenuAPI
from lp.app.enums import ServiceUsage
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.widgets.textwidgets import StrippedTextWidget
from lp.blueprints.browser.specificationtarget import (
    HasSpecificationsMenuMixin,
    )
from lp.blueprints.enums import SpecificationImplementationStatus
from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.bugs.browser.bugtask import BugTargetTraversalMixin
from lp.bugs.browser.structuralsubscription import (
    expose_structural_subscription_data_to_js,
    StructuralSubscriptionMenuMixin,
    StructuralSubscriptionTargetTraversalMixin,
    )
from lp.bugs.interfaces.bugtask import IBugTaskSet
from lp.code.browser.branchref import BranchRef
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.registry.browser import (
    add_subscribe_link,
    BaseRdfView,
    MilestoneOverlayMixin,
    RegistryDeleteViewMixin,
    StatusCount,
    )
from lp.registry.browser.pillar import (
    InvolvedMenu,
    PillarInvolvementView,
    )
from lp.registry.browser.product import ProductSetBranchView
from lp.registry.enums import VCSType
from lp.registry.errors import CannotPackageProprietaryProduct
from lp.registry.interfaces.packaging import (
    IPackaging,
    IPackagingUtil,
    )
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.series import SeriesStatus
from lp.services.config import config
from lp.services.propertycache import cachedproperty
from lp.services.webapp import (
    ApplicationMenu,
    canonical_url,
    enabled_with_permission,
    LaunchpadView,
    Link,
    Navigation,
    NavigationMenu,
    stepthrough,
    stepto,
    )
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.batching import BatchNavigator
from lp.services.webapp.breadcrumb import Breadcrumb
from lp.services.webapp.escaping import structured
from lp.services.webapp.vhosts import allvhosts
from lp.services.worlddata.helpers import browser_languages
from lp.services.worlddata.interfaces.country import ICountry
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.interfaces.productserieslanguage import (
    IProductSeriesLanguageSet,
    )


class ProductSeriesNavigation(Navigation, BugTargetTraversalMixin,
    StructuralSubscriptionTargetTraversalMixin):
    """A class to navigate `IProductSeries` URLs."""
    usedfor = IProductSeries

    @stepto('.bzr')
    def dotbzr(self):
        """Return the series branch."""
        if self.context.branch:
            return BranchRef(self.context.branch)

    @stepto('+pots')
    def pots(self):
        """Return the series templates."""
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(productseries=self.context)

    @stepthrough('+lang')
    def traverse_lang(self, langcode):
        """Retrieve the ProductSeriesLanguage or a dummy if it is None."""
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
        psl_set = getUtility(IProductSeriesLanguageSet)
        psl = psl_set.getProductSeriesLanguage(self.context, lang)

        return psl

    def traverse(self, name):
        """See `INavigation`."""
        return self.context.getRelease(name)


class ProductSeriesBreadcrumb(Breadcrumb):
    """Builds a breadcrumb for an `IProductSeries`."""

    @property
    def text(self):
        """See `IBreadcrumb`."""
        return 'Series ' + self.context.name


class IProductSeriesInvolved(Interface):
    """A marker interface for getting involved."""


class ProductSeriesInvolvedMenu(InvolvedMenu):
    """The get involved menu."""
    usedfor = IProductSeriesInvolved
    links = [
        'report_bug', 'help_translate', 'register_blueprint']

    @property
    def view(self):
        return self.context

    @property
    def pillar(self):
        return self.view.context.product


@implementer(IProductSeriesInvolved)
class ProductSeriesInvolvementView(PillarInvolvementView):
    """Encourage configuration of involvement links for project series."""
    has_involvement = True

    def __init__(self, context, request):
        super(ProductSeriesInvolvementView, self).__init__(context, request)
        self.answers_usage = ServiceUsage.NOT_APPLICABLE
        if self.context.branch is not None:
            self.codehosting_usage = ServiceUsage.LAUNCHPAD
        else:
            self.codehosting_usage = ServiceUsage.UNKNOWN

    @property
    def configuration_links(self):
        """The enabled involvement links."""
        series_menu = MenuAPI(self.context).overview
        set_branch = series_menu['set_branch']
        set_branch.text = 'Configure series branch'
        if self.codehosting_usage == ServiceUsage.LAUNCHPAD:
            configured = True
        else:
            configured = False
        return [dict(link=set_branch, configured=configured)]


class ProductSeriesOverviewMenu(
    ApplicationMenu, StructuralSubscriptionMenuMixin):
    """The overview menu."""
    usedfor = IProductSeries
    facet = 'overview'

    @cachedproperty
    def links(self):
        links = [
            'configure_bugtracker',
            'create_milestone',
            'create_release',
            'delete',
            'driver',
            'edit',
            'rdf',
            'set_branch',
            ]
        add_subscribe_link(links)
        links.append('ubuntupkg')
        return links

    @enabled_with_permission('launchpad.Edit')
    def configure_bugtracker(self):
        text = 'Configure bug tracker'
        summary = 'Specify where bugs are tracked for this project'
        return Link(
            canonical_url(
                self.context.product, view_name='+configure-bugtracker'),
            text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        """Return a link to edit this series."""
        text = 'Change details'
        summary = 'Edit this series'
        return Link('+edit', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def delete(self):
        """Return a link to delete this series."""
        text = 'Delete series'
        summary = "Delete this series and all it's dependent items."
        return Link('+delete', text, summary, icon='trash-icon')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        """Return a link to set the release manager."""
        text = 'Appoint release manager'
        summary = 'Someone with permission to set goals this series'
        return Link('+driver', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def set_branch(self):
        """Return a link to set the bazaar branch for this series."""
        if self.context.branch is None:
            text = 'Link to branch'
            icon = 'add'
            summary = 'Set the branch for this series'
        else:
            text = "Change branch"
            icon = 'edit'
            summary = 'Change the branch for this series'
        return Link('+setbranch', text, summary, icon=icon)

    @enabled_with_permission('launchpad.AnyPerson')
    def ubuntupkg(self):
        """Return a link to link this series to an ubuntu sourcepackage."""
        text = 'Link to Ubuntu package'
        return Link('+ubuntupkg', text, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def create_milestone(self):
        """Return a link to create a milestone."""
        text = 'Create milestone'
        summary = 'Register a new milestone for this series'
        return Link('+addmilestone', text, summary, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def create_release(self):
        """Return a link to create a release."""
        text = 'Create release'
        return Link('+addrelease', text, icon='add')

    def rdf(self):
        """Return a link to download the series RDF data."""
        text = 'Download RDF metadata'
        return Link('+rdf', text, icon='download')


class ProductSeriesBugsMenu(ApplicationMenu, StructuralSubscriptionMenuMixin):
    """The bugs menu."""
    usedfor = IProductSeries
    facet = 'bugs'

    @cachedproperty
    def links(self):
        links = ['new', 'nominations']
        add_subscribe_link(links)
        return links

    def new(self):
        """Return a link to report a bug in this series."""
        return Link('+filebug', 'Report a bug', icon='add')

    def nominations(self):
        """Return a link to review bugs nominated for this series."""
        return Link('+nominations', 'Review nominations', icon='bug')


class ProductSeriesSpecificationsMenu(NavigationMenu,
                                      HasSpecificationsMenuMixin):
    """Specs menu for ProductSeries.

    This menu needs to keep track of whether we are showing all the
    specs, or just those that are approved/declined/proposed. It should
    allow you to change the set your are showing while keeping the basic
    view intact.
    """

    usedfor = IProductSeries
    facet = 'specifications'
    links = [
        'listall', 'assignments', 'setgoals', 'listdeclined',
        'new', 'register_sprint']


class ProductSeriesOverviewNavigationMenu(NavigationMenu):
    """Overview navigation menus for `IProductSeries` objects."""
    # Suppress the ProductOverviewNavigationMenu from showing on series,
    # release, and milestone pages.
    usedfor = IProductSeries
    facet = 'overview'
    links = ()


def get_series_branch_error(product, branch):
    """Check if the given branch is suitable for the given product.

    Returns an HTML error message on error, and None otherwise.
    """
    if branch.product != product:
        return structured(
            '<a href="%s">%s</a> is not a branch of <a href="%s">%s</a>.',
            canonical_url(branch), branch.unique_name, canonical_url(product),
            product.displayname)


class ProductSeriesView(
    LaunchpadView, MilestoneOverlayMixin, InformationTypePortletMixin):
    """A view to show a series with translations."""

    def initialize(self):
        super(ProductSeriesView, self).initialize()
        expose_structural_subscription_data_to_js(
            self.context, self.request, self.user)

    @property
    def page_title(self):
        """Return the HTML page title."""
        return self.context.title

    def requestCountry(self):
        """The country associated with the IP of the request."""
        return ICountry(self.request, None)

    @property
    def golang_import_spec(self):
        """Meta string for golang remote import path.
        See: https://golang.org/cmd/go/#hdr-Remote_import_paths
        """
        if (self.context.product.vcs == VCSType.BZR and
            self.user_branch_visible):
            return (
                "{hostname}/{product}/{series} bzr {root_url}{branch}").format(
                    hostname=config.vhost.mainsite.hostname,
                    product=self.context.product.name,
                    series=self.context.name,
                    branch=self.context.branch.unique_name,
                    root_url=allvhosts.configs['mainsite'].rooturl)
        else:
            return None

    def browserLanguages(self):
        """The languages the user's browser requested."""
        return browser_languages(self.request)

    @property
    def request_import_link(self):
        """A link to the page for requesting a new code import."""
        return canonical_url(
            self.context.product, view_name='+new-import', rootsite='code')

    @property
    def user_branch_visible(self):
        """Can the logged in user see the user branch."""
        branch = self.context.branch
        return (branch is not None and
                check_permission('launchpad.View', branch))

    @property
    def long_bzr_identity(self):
        """The bzr identity of the branch including the unique_name."""
        lp_prefix = config.codehosting.bzr_lp_prefix
        return lp_prefix + self.context.branch.getBranchIdentities()[-1][0]

    @property
    def is_obsolete(self):
        """Return True if the series is OBSOLETE.

        Obsolete series do not need to display as much information as other
        series. Accessing private bugs is an expensive operation and showing
        them for obsolete series can be a problem if many series are being
        displayed.
        """
        return self.context.status == SeriesStatus.OBSOLETE

    @cachedproperty
    def bugtask_status_counts(self):
        """A list StatusCounts summarising the targeted bugtasks."""
        bugtaskset = getUtility(IBugTaskSet)
        status_counts = bugtaskset.getStatusCountsForProductSeries(
            self.user, self.context)
        # We sort by value before sortkey because the statuses returned can be
        # from different (though related) enums.
        statuses = sorted(status_counts, key=attrgetter('value', 'sortkey'))
        return [
            StatusCount(status, status_counts[status])
            for status in statuses]

    @cachedproperty
    def specification_status_counts(self):
        """A list StatusCounts summarising the targeted specification."""
        specification_set = getUtility(ISpecificationSet)
        status_id_counts = specification_set.getStatusCountsForProductSeries(
            self.context)
        SpecStatus = SpecificationImplementationStatus
        status_counts = dict([(SpecStatus.items[status_id], count)
                              for status_id, count in status_id_counts])
        return [StatusCount(status, status_counts[status])
                for status in sorted(status_counts,
                                     key=attrgetter('sortkey'))]

    @cachedproperty
    def latest_release_with_download_files(self):
        for release in self.context.releases:
            if len(list(release.files)) > 0:
                return release
        return None

    @cachedproperty
    def milestone_batch_navigator(self):
        return BatchNavigator(self.context.all_milestones, self.request)


class ProductSeriesDetailedDisplayView(ProductSeriesView):

    @cachedproperty
    def latest_milestones(self):
        # Convert to list to avoid the query being run multiple times.
        return list(self.context.milestones[:12])

    @cachedproperty
    def latest_releases(self):
        # Convert to list to avoid the query being run multiple times.
        return list(self.context.releases[:12])


class ProductSeriesUbuntuPackagingView(LaunchpadFormView):

    schema = IPackaging
    field_names = ['sourcepackagename', 'distroseries']
    page_title = 'Ubuntu source packaging'
    label = page_title

    def __init__(self, context, request):
        """Set the static packaging information for this series."""
        super(ProductSeriesUbuntuPackagingView, self).__init__(
            context, request)
        self._ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self._ubuntu_series = self._ubuntu.currentseries
        try:
            package = self.context.getPackage(self._ubuntu_series)
            self.default_sourcepackagename = package.sourcepackagename
        except NotFoundError:
            # The package has never been set.
            self.default_sourcepackagename = None

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    cancel_url = next_url

    def setUpFields(self):
        """See `LaunchpadFormView`.

        The packaging is restricted to ubuntu series and the default value
        is the current development series.
        """
        super(ProductSeriesUbuntuPackagingView, self).setUpFields()
        series_vocabulary = SimpleVocabulary(
            [SimpleTerm(series, series.name, series.named_version)
             for series in self._ubuntu.series])
        choice = Choice(__name__='distroseries',
            title=_('Series'),
            default=self._ubuntu_series,
            vocabulary=series_vocabulary,
            description=_(
                "Series where this package is published. The current series "
                "is most important to the Ubuntu community."),
            required=True)
        field = form.Fields(choice, render_context=self.render_context)
        self.form_fields = self.form_fields.omit(choice.__name__) + field

    @property
    def initial_values(self):
        """See `LaunchpadFormView`."""
        if self.default_sourcepackagename is not None:
            return {'sourcepackagename': self.default_sourcepackagename}
        else:
            return {}

    @property
    def default_distroseries(self):
        """The current Ubuntu distroseries"""
        return self._ubuntu_series

    @property
    def ubuntu_history(self):
        return self.context.getPackagingInDistribution(
            self.default_distroseries.distribution)

    def _getSubmittedSeries(self, data):
        """Return the submitted or default series."""
        return data.get('distroseries', self.default_distroseries)

    def validate(self, data):
        productseries = self.context
        sourcepackagename = data.get('sourcepackagename', None)
        distroseries = self._getSubmittedSeries(data)

        packaging_util = getUtility(IPackagingUtil)
        if packaging_util.packagingEntryExists(
            productseries=productseries,
            sourcepackagename=sourcepackagename,
            distroseries=distroseries):
            # The package already exists. Don't display an error. The
            # action method will let this go by.
            return

        # Do not allow users to create links to unpublished Ubuntu packages.
        if (sourcepackagename is not None
                and distroseries.distribution.official_packages):
            source_package = distroseries.getSourcePackage(sourcepackagename)
            if source_package.currentrelease is None:
                message = ("The source package is not published in %s." %
                    distroseries.displayname)
                self.setFieldError('sourcepackagename', message)

        if packaging_util.packagingEntryExists(
            sourcepackagename=sourcepackagename,
            distroseries=distroseries):
            # The series package conflicts with another series.
            sourcepackage = distroseries.getSourcePackage(
                sourcepackagename.name)
            message = structured(
                'The <a href="%s">%s</a> package in %s is already linked to '
                'another series.' %
                (canonical_url(sourcepackage),
                 sourcepackagename.name,
                 distroseries.displayname))
            self.setFieldError('sourcepackagename', message)

    @action('Update', name='continue')
    def continue_action(self, action, data):
        # set the packaging record for this productseries in the current
        # ubuntu series. if none exists, one will be created
        distroseries = self._getSubmittedSeries(data)
        sourcepackagename = data['sourcepackagename']
        if getUtility(IPackagingUtil).packagingEntryExists(
            sourcepackagename, distroseries, productseries=self.context):
            # There is no change.
            return
        try:
            self.context.setPackaging(
                distroseries, sourcepackagename, self.user)
        except CannotPackageProprietaryProduct, e:
            self.request.response.addErrorNotification(str(e))


class ProductSeriesEditView(LaunchpadEditFormView):
    """A View to edit the attributes of a series."""
    schema = IProductSeries
    field_names = [
        'name', 'summary', 'status', 'branch', 'releasefileglob']
    custom_widget('summary', TextAreaWidget, height=7, width=62)
    custom_widget('releasefileglob', StrippedTextWidget, displayWidth=40)

    @property
    def label(self):
        """The form label."""
        return 'Edit %s %s series' % (
            self.context.product.displayname, self.context.name)

    page_title = label

    def validate(self, data):
        """See `LaunchpadFormView`."""
        branch = data.get('branch')
        if branch is not None:
            message = get_series_branch_error(self.context.product, branch)
            if message:
                self.setFieldError('branch', message)

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        """Update the series."""
        self.updateContextFromData(data)

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    cancel_url = next_url


class ProductSeriesDeleteView(RegistryDeleteViewMixin, LaunchpadEditFormView):
    """A view to remove a productseries from a product."""
    schema = IProductSeries
    field_names = []

    @property
    def label(self):
        """The form label."""
        return 'Delete %s %s series' % (
            self.context.product.displayname, self.context.name)

    page_title = label

    @cachedproperty
    def milestones(self):
        """A list of all the series `IMilestone`s."""
        return self.context.all_milestones

    @cachedproperty
    def bugtasks(self):
        """A list of all `IBugTask`s targeted to this series."""
        all_bugtasks = self._getBugtasks(self.context)
        for milestone in self.milestones:
            all_bugtasks.extend(self._getBugtasks(milestone))
        return all_bugtasks

    @cachedproperty
    def specifications(self):
        """A list of all `ISpecification`s targeted to this series."""
        all_specifications = list(self.context.visible_specifications)
        for milestone in self.milestones:
            all_specifications.extend(milestone.getSpecifications(self.user))
        return all_specifications

    @cachedproperty
    def has_bugtasks_and_specifications(self):
        """Does the series have any targeted bugtasks or specifications."""
        return len(self.bugtasks) > 0 or len(self.specifications) > 0

    @property
    def has_linked_branch(self):
        """Is the series linked to a branch."""
        return self.context.branch is not None

    @cachedproperty
    def product_release_files(self):
        """A list of all `IProductReleaseFile`s that belong to this series."""
        all_files = []
        for milestone in self.milestones:
            all_files.extend(self._getProductReleaseFiles(milestone))
        return all_files

    @cachedproperty
    def has_linked_packages(self):
        """Is the series linked to source packages."""
        return not self.context.packagings.is_empty()

    @cachedproperty
    def linked_packages_message(self):
        url = canonical_url(self.context.product, view_name="+packages")
        return (
            "You cannot delete a series that is linked to packages in "
            "distributions. You can remove the links from the "
            '<a href="%s">project packaging</a> page.' % url)

    development_focus_message = _(
        "You cannot delete a series that is the focus of "
        "development. Make another series the focus of development "
        "before deleting this one.")

    @cachedproperty
    def has_translations(self):
        """Does the series have translations?"""
        return self.context.potemplate_count > 0

    translations_message = (
        "This series cannot be deleted because it has translations.")

    @cachedproperty
    def can_delete(self):
        """Can this series be delete."""
        return not (
            self.context.is_development_focus
            or self.has_linked_packages or self.has_translations)

    def canDeleteAction(self, action):
        """Is the delete action available."""
        if self.context.is_development_focus:
            self.addError(self.development_focus_message)
        if self.has_linked_packages:
            self.addError(structured(self.linked_packages_message))
        if self.has_translations:
            self.addError(self.translations_message)
        return self.can_delete

    @action('Delete this Series', name='delete', condition=canDeleteAction)
    def delete_action(self, action, data):
        """Detach and delete associated objects and remove the series."""
        product = self.context.product
        name = self.context.name
        self._deleteProductSeries(self.context)
        self.request.response.addInfoNotification(
            "Series %s deleted." % name)
        self.next_url = canonical_url(product)


class ProductSeriesSetBranchView(ProductSetBranchView, ProductSeriesView):
    """The view to set a branch for the ProductSeries."""

    is_series = True

    @property
    def series(self):
        return self.context

    @property
    def target(self):
        """The branch target for the context."""
        return IBranchTarget(self.context.product)

    def add_update_notification(self):
        self.request.response.addInfoNotification(
            'Series code location updated.')


class ProductSeriesReviewView(LaunchpadEditFormView):
    """A view to review and change the series `IProduct` and name."""
    schema = IProductSeries
    field_names = ['product', 'name']
    custom_widget('name', TextWidget, displayWidth=20)

    @property
    def label(self):
        """The form label."""
        return 'Administer %s %s series' % (
            self.context.product.displayname, self.context.name)

    page_title = label

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        """Update the series."""
        self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            _('This Series has been changed'))
        self.next_url = canonical_url(self.context)


class ProductSeriesRdfView(BaseRdfView):
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile('../templates/productseries-rdf.pt')

    @property
    def filename(self):
        return '%s-%s.rdf' % (self.context.product.name, self.context.name)


class ProductSeriesFileBugRedirect(LaunchpadView):
    """Redirect to the product's +filebug page."""

    def initialize(self):
        """See `LaunchpadFormView`."""
        filebug_url = "%s/+filebug" % canonical_url(self.context.product)
        self.request.response.redirect(filebug_url)
