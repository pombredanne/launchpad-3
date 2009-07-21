# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes for `IProductSeries`."""

__metaclass__ = type

__all__ = [
    'get_series_branch_error',
    'ProductSeriesBreadcrumbBuilder',
    'ProductSeriesBugsMenu',
    'ProductSeriesDeleteView',
    'ProductSeriesEditView',
    'ProductSeriesFacets',
    'ProductSeriesFileBugRedirect',
    'ProductSeriesLinkBranchView',
    'ProductSeriesLinkBranchFromCodeView',
    'ProductSeriesNavigation',
    'ProductSeriesOverviewMenu',
    'ProductSeriesOverviewNavigationMenu',
    'ProductSeriesRdfView',
    'ProductSeriesReviewView',
    'ProductSeriesSourceListView',
    'ProductSeriesSpecificationsMenu',
    'ProductSeriesView',
    ]

import cgi
from operator import attrgetter

from bzrlib.revision import NULL_REVISION

from zope.component import getUtility
from zope.app.form.browser import TextAreaWidget, TextWidget

from z3c.ptcompat import ViewPageTemplateFile

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from lp.code.browser.branchref import BranchRef
from lp.blueprints.interfaces.specification import (
    ISpecificationSet, SpecificationImplementationStatus)
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.helpers import browserLanguages
from lp.code.interfaces.branchjob import IRosettaUploadJobSource
from lp.code.interfaces.codeimport import (
    ICodeImportSet)
from lp.services.worlddata.interfaces.country import ICountry
from lp.bugs.interfaces.bugtask import IBugTaskSet
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.browser import StatusCount
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.interfaces.productserieslanguage import (
    IProductSeriesLanguageSet)
from lp.services.worlddata.interfaces.language import ILanguageSet
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, custom_widget,
    enabled_with_permission, LaunchpadEditFormView,
    LaunchpadView, Link, Navigation, NavigationMenu, StandardLaunchpadFacets,
    stepthrough, stepto)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.launchpad.webapp.menu import structured
from canonical.widgets.textwidgets import StrippedTextWidget

from lp.registry.browser import (
    MilestoneOverlayMixin, RegistryDeleteViewMixin)
from lp.registry.interfaces.distroseries import DistroSeriesStatus
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageNameSet)

def quote(text):
    """Escape and quite text."""
    return cgi.escape(text, quote=True)


class ProductSeriesNavigation(Navigation, BugTargetTraversalMixin):
    """A class to navigate `IProductSeries` URLs."""
    usedfor = IProductSeries

    @stepto('.bzr')
    def dotbzr(self):
        """Return the series branch."""
        if self.context.branch:
            return BranchRef(self.context.branch)
        else:
            return None

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


class ProductSeriesBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IProductSeries`."""
    @property
    def text(self):
        """See `IBreadcrumbBuilder`."""
        return 'Series ' + self.context.name


class ProductSeriesFacets(StandardLaunchpadFacets):
    """A class that provides the series facets."""
    usedfor = IProductSeries
    enable_only = [
        'overview', 'branches', 'bugs', 'specifications', 'translations']

    def branches(self):
        """Return a link to view the branches related to this series."""
        # Override to go to the branches for the product.
        text = 'Code'
        summary = 'View related branches of code'
        link = canonical_url(self.context.product, rootsite='code')
        return Link(link, text, summary=summary)


class ProductSeriesOverviewMenu(ApplicationMenu):
    """The overview menu."""
    usedfor = IProductSeries
    facet = 'overview'
    links = [
        'edit', 'delete', 'driver', 'link_branch', 'ubuntupkg',
        'add_package', 'create_milestone', 'create_release',
        'rdf', 'subscribe'
        ]

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
    def link_branch(self):
        """Return a link to set the bazaar branch for this series."""
        if self.context.branch is None:
            text = 'Link to branch'
            icon = 'add'
        else:
            text = "Change branch"
            icon = 'edit'
        summary = 'The code branch that for this series.'
        return Link('+linkbranch', text, summary, icon=icon)

    def ubuntupkg(self):
        """Return a link to link this series to an ubuntu sourcepackage."""
        text = 'Link to Ubuntu package'
        return Link('+ubuntupkg', text, icon='add')

    def add_package(self):
        """Return a link to link this series to a sourcepackage."""
        text = 'Link to other package'
        return Link('+addpackage', text, icon='add')

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

    def subscribe(self):
        """Return a link to subscribe to bug mail."""
        text = 'Subscribe to bug mail'
        return Link('+subscribe', text, icon='edit')


class ProductSeriesBugsMenu(ApplicationMenu):
    """The bugs menu."""
    usedfor = IProductSeries
    facet = 'bugs'
    links = (
        'new',
        'nominations',
        'subscribe',
        )

    def new(self):
        """Return a link to report a bug in this series."""
        return Link('+filebug', 'Report a bug', icon='add')

    def nominations(self):
        """Return a link to review bugs nominated for this series."""
        return Link('+nominations', 'Review nominations', icon='bug')

    def subscribe(self):
        """Return a link to subscribe to bug mail."""
        return Link('+subscribe', 'Subscribe to bug mail')


class ProductSeriesSpecificationsMenu(ApplicationMenu):
    """Specs menu for ProductSeries.

    This menu needs to keep track of whether we are showing all the
    specs, or just those that are approved/declined/proposed. It should
    allow you to change the set your are showing while keeping the basic
    view intact.
    """

    usedfor = IProductSeries
    facet = 'specifications'
    links = ['listall', 'table', 'setgoals', 'listdeclined', 'new']

    def listall(self):
        """Return a link to show all blueprints."""
        text = 'List all blueprints'
        return Link('+specs?show=all', text, icon='info')

    def listaccepted(self):
        """Return a link to show the approved goals."""
        text = 'List approved blueprints'
        return Link('+specs?acceptance=accepted', text, icon='info')

    def listproposed(self):
        """Return a link to show the proposed goals."""
        text = 'List proposed blueprints'
        return Link('+specs?acceptance=proposed', text, icon='info')

    def listdeclined(self):
        """Return a link to show the declined goals."""
        text = 'List declined blueprints'
        summary = 'Show the goals which have been declined'
        return Link('+specs?acceptance=declined', text, summary, icon='info')

    def setgoals(self):
        """Return a link to set the series goals."""
        text = 'Set series goals'
        summary = 'Approve or decline feature goals that have been proposed'
        return Link('+setgoals', text, summary, icon='edit')

    def table(self):
        """Return a link to show the people assigned to the blueprint."""
        text = 'Assignments'
        summary = 'Show the assignee, drafter and approver of these specs'
        return Link('+assignments', text, summary, icon='info')

    def new(self):
        """Return a link to register a blueprint."""
        text = 'Register a blueprint'
        summary = 'Register a new blueprint for %s' % self.context.title
        return Link('+addspec', text, summary, icon='add')


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
            canonical_url(branch),
            branch.unique_name,
            canonical_url(product),
            product.displayname)
    return None


# A View Class for ProductSeries
#
# XXX: StuartBishop 2005-05-02:
# We should be using autogenerated add forms and edit forms so that
# this becomes maintainable and form validation handled for us.
# Currently, the pages just return 'System Error' as they trigger database
# constraints.
class ProductSeriesView(LaunchpadView, MilestoneOverlayMixin):
    """A view to show a series with translations."""
    def initialize(self):
        """See `LaunchpadFormView`."""
        self.form = self.request.form
        self.has_errors = False

        # Let's find out what source package is associated with this
        # productseries in the current release of ubuntu.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.curr_ubuntu_series = ubuntu.currentseries
        self.setUpPackaging()

        # Check the form submission.
        self.processForm()

    def processForm(self):
        """Process a form if it was submitted."""
        if not self.request.method == "POST":
            # The form was not posted, we don't do anything.
            return
        assert 'set_ubuntu_pkg' in self.form, (
            "This can handle POST requests only for 'set_ubuntu_pkg' form.")
        self.setCurrentUbuntuPackage()

    def setUpPackaging(self):
        """Ensure that the View class correctly reflects the packaging of
        its product series context."""
        self.curr_ubuntu_package = None
        self.curr_ubuntu_pkgname = ''
        try:
            cr = self.curr_ubuntu_series
            self.curr_ubuntu_package = self.context.getPackage(cr)
            cp = self.curr_ubuntu_package
            self.curr_ubuntu_pkgname = cp.sourcepackagename.name
        except NotFoundError:
            pass
        ubuntu = self.curr_ubuntu_series.distribution
        self.ubuntu_history = self.context.getPackagingInDistribution(ubuntu)

    def setCurrentUbuntuPackage(self):
        """Set the Packaging record for this product series in the current
        Ubuntu distroseries to be for the source package name that is given
        in the form.
        """
        ubuntupkg = self.form.get('ubuntupkg', '')
        if ubuntupkg == '':
            # No package was selected.
            self.request.response.addWarningNotification(
                'Request ignored. You need to select a source package.')
            return
        # make sure we have a person to work with
        if self.user is None:
            self.request.response.addErrorNotification('Please log in first!')
            self.has_errors = True
            return
        # see if the name that is given is a real source package name
        spns = getUtility(ISourcePackageNameSet)
        try:
            spn = spns[ubuntupkg]
        except NotFoundError:
            self.request.response.addErrorNotification(
                'Invalid source package name %s' % ubuntupkg)
            self.has_errors = True
            return
        # set the packaging record for this productseries in the current
        # ubuntu series. if none exists, one will be created
        self.context.setPackaging(self.curr_ubuntu_series, spn, self.user)
        self.setUpPackaging()

    def requestCountry(self):
        """The country associated with the IP of the request."""
        return ICountry(self.request, None)

    def browserLanguages(self):
        """The languages the user's browser requested."""
        return browserLanguages(self.request)

    @property
    def request_import_link(self):
        """A link to the page for requesting a new code import."""
        return canonical_url(getUtility(ICodeImportSet), view_name='+new')

    @property
    def user_branch_visible(self):
        """Can the logged in user see the user branch."""
        branch = self.context.branch
        return (branch is not None and
                check_permission('launchpad.View', branch))

    @property
    def is_obsolete(self):
        """Return True if the series is OBSOLETE"

        Obsolete series do not need to display as much information of other
        series. Accessing private bugs is an expensive operation and showing
        them for obsolete series can be a problem if many series are being
        displayed.
        """
        return self.context.status == DistroSeriesStatus.OBSOLETE

    @cachedproperty
    def bugtask_status_counts(self):
        """A list StatusCounts summarising the targeted bugtasks."""
        bugtaskset = getUtility(IBugTaskSet)
        status_id_counts = bugtaskset.getStatusCountsForProductSeries(
            self.user, self.context)
        status_counts = dict([(BugTaskStatus.items[status_id], count)
                              for status_id, count in status_id_counts])
        return [StatusCount(status, status_counts[status])
                for status in sorted(status_counts,
                                     key=attrgetter('sortkey'))]

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

    @property
    def milestone_table_class(self):
        """The milestone table will be unseen if there are no milestones."""
        if len(self.context.all_milestones) > 0:
            return 'listing'
        else:
            # The page can remove the 'unseen' class to make the table
            # visible.
            return 'listing unseen'

    @property
    def milestone_row_uri_template(self):
        return (
            '%s/+milestone/{name}/+productseries-table-row' %
            canonical_url(self.context.product, path_only_if_possible=True))


class ProductSeriesEditView(LaunchpadEditFormView):
    """A View to edit the attributes of a series."""
    schema = IProductSeries
    field_names = [
        'name', 'summary', 'status', 'branch', 'releasefileglob']
    custom_widget('summary', TextAreaWidget, height=7, width=62)
    custom_widget('releasefileglob', StrippedTextWidget, displayWidth=40)

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


class ProductSeriesDeleteView(RegistryDeleteViewMixin, LaunchpadEditFormView):
    """A view to remove a productseries from a product."""
    schema = IProductSeries
    field_names = []

    @property
    def label(self):
        """The form label."""
        return 'Delete %s series %s' % (
            self.context.product.displayname, self.context.name)

    @cachedproperty
    def milestones(self):
        """A list of all the series `IMilestone`s."""
        return self.context.all_milestones

    @cachedproperty
    def bugtasks(self):
        """A list of all `IBugTask`s targeted to this series."""
        all_bugtasks = []
        for milestone in self.milestones:
            all_bugtasks.extend(self._getBugtasks(milestone))
        return all_bugtasks

    @cachedproperty
    def specifications(self):
        """A list of all `ISpecification`s targeted to this series."""
        all_specifications = []
        for milestone in self.milestones:
            all_specifications.extend(self._getSpecifications(milestone))
        return all_specifications

    @cachedproperty
    def has_bugtasks_and_specifications(self):
        """Does the series have any targeted bugtasks or specifications."""
        return len(self.bugtasks) > 0 or len(self.specifications) > 0

    @cachedproperty
    def product_release_files(self):
        """A list of all `IProductReleaseFile`s that belong to this series."""
        all_files = []
        for milestone in self.milestones:
            all_files.extend(self._getProductReleaseFiles(milestone))
        return all_files

    @cachedproperty
    def can_delete(self):
        """Can this series be delete."""
        return not self.context.is_development_focus

    def canDeleteAction(self, action):
        """Is the delete action available."""
        if not self.can_delete:
            self.addError(
                "You cannot delete a series that is the focus of "
                "development. Make another series the focus of development "
                "before deleting this one.")
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


class ProductSeriesLinkBranchView(LaunchpadEditFormView):
    """View to set the bazaar branch for a product series."""

    schema = IProductSeries
    field_names = ['branch']

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    @action(_('Update'), name='update')
    def update_action(self, action, data):
        """Update the branch attribute."""
        if data['branch'] != self.context.branch:
            self.updateContextFromData(data)
            # Request an initial upload of translation files.
            getUtility(IRosettaUploadJobSource).create(
                self.context.branch, NULL_REVISION)
        else:
            self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            'Series code location updated.')

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the product series page."""


class ProductSeriesLinkBranchFromCodeView(ProductSeriesLinkBranchView):
    """Set the branch link from the code overview page."""

    @property
    def next_url(self):
        """Take the user back to the code overview page."""
        return canonical_url(self.context.product, rootsite="code")


class ProductSeriesReviewView(LaunchpadEditFormView):
    """A view to review and change the series `IProduct` and name."""
    schema = IProductSeries
    field_names = ['product', 'name']
    label = 'Review product series details'
    custom_widget('name', TextWidget, width=20)

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        """Update the series."""
        self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            _('This Series has been changed'))
        self.next_url = canonical_url(self.context)


class ProductSeriesRdfView(object):
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile(
        '../templates/productseries-rdf.pt')

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
                                        'attachment; filename=%s-%s.rdf' % (
                                            self.context.product.name,
                                            self.context.name))
        unicodedata = self.template()
        encodeddata = unicodedata.encode('utf-8')
        return encodeddata


class ProductSeriesSourceListView(LaunchpadView):
    """A listing of all the running imports.

    See `ICodeImportSet.getActiveImports` for our definition of running.
    """

    def initialize(self):
        """See `LaunchpadFormView`."""
        self.text = self.request.get('text')
        results = getUtility(ICodeImportSet).getActiveImports(text=self.text)

        self.batchnav = BatchNavigator(results, self.request)


class ProductSeriesFileBugRedirect(LaunchpadView):
    """Redirect to the product's +filebug page."""

    def initialize(self):
        """See `LaunchpadFormView`."""
        filebug_url = "%s/+filebug" % canonical_url(self.context.product)
        self.request.response.redirect(filebug_url)
