# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'get_series_branch_error',
    'ProductSeriesBreadcrumbBuilder',
    'ProductSeriesBugsMenu',
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
    'ProductSeriesTranslationsBzrImportView',
    'ProductSeriesTranslationsExportView',
    'ProductSeriesTranslationsMenu',
    'ProductSeriesTranslationsSettingsView',
    'ProductSeriesView',
    ]

import cgi
import os.path

from bzrlib.revision import NULL_REVISION
from zope.component import getUtility
from zope.app.form.browser import TextAreaWidget, TextWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import FileUpload

from canonical.launchpad import _
from lp.code.browser.branchref import BranchRef
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.poexportrequest import BaseExportView
from canonical.launchpad.browser.translations import TranslationsMixin
from canonical.launchpad.helpers import browserLanguages, is_tar_filename
from lp.code.interfaces.codeimport import (
    ICodeImportSet)
from lp.code.interfaces.branchjob import IRosettaUploadJobSource
from canonical.launchpad.interfaces.country import ICountry
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.potemplate import IPOTemplateSet
from canonical.launchpad.interfaces.translations import (
    TranslationsBranchImportMode)
from canonical.launchpad.interfaces.translationimporter import (
    ITranslationImporter)
from canonical.launchpad.interfaces.translationimportqueue import (
    ITranslationImportQueue)
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, custom_widget,
    enabled_with_permission, LaunchpadEditFormView, LaunchpadFormView,
    LaunchpadView, Link, Navigation, NavigationMenu, StandardLaunchpadFacets,
    stepto)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.launchpad.webapp.menu import structured
from canonical.widgets.itemswidgets import (
    LaunchpadRadioWidgetWithDescription)
from canonical.widgets.textwidgets import StrippedTextWidget
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageNameSet)


def quote(text):
    return cgi.escape(text, quote=True)


class ProductSeriesNavigation(Navigation, BugTargetTraversalMixin):

    usedfor = IProductSeries

    @stepto('.bzr')
    def dotbzr(self):
        if self.context.branch:
            return BranchRef(self.context.branch)
        else:
            return None

    @stepto('+pots')
    def pots(self):
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(productseries=self.context)

    def traverse(self, name):
        return self.context.getRelease(name)


class ProductSeriesBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IProductSeries`."""
    @property
    def text(self):
        return 'Series ' + self.context.name


class ProductSeriesFacets(StandardLaunchpadFacets):

    usedfor = IProductSeries
    enable_only = [
        'overview', 'branches', 'bugs', 'specifications', 'translations']

    def branches(self):
        # Override to go to the branches for the product.
        text = 'Code'
        summary = 'View related branches of code'
        link = canonical_url(self.context.product, rootsite='code')
        return Link(link, text, summary=summary)


class ProductSeriesOverviewMenu(ApplicationMenu):

    usedfor = IProductSeries
    facet = 'overview'
    links = [
        'edit', 'driver', 'link_branch', 'ubuntupkg',
        'add_package', 'create_milestone', 'create_release',
        'rdf', 'subscribe'
        ]

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals this series'
        return Link('+driver', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def link_branch(self):
        text = 'Link to branch'
        return Link('+linkbranch', text, icon='edit')

    def ubuntupkg(self):
        text = 'Link to Ubuntu package'
        return Link('+ubuntupkg', text, icon='edit')

    def add_package(self):
        text = 'Link to other package'
        return Link('+addpackage', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def create_milestone(self):
        text = 'Create milestone'
        summary = 'Register a new milestone for this series'
        return Link('+addmilestone', text, summary, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def create_release(self):
        text = 'Create release'
        return Link('+addrelease', text, icon='add')

    def rdf(self):
        text = 'Download RDF metadata'
        return Link('+rdf', text, icon='download')

    def subscribe(self):
        text = 'Subscribe to bug mail'
        return Link('+subscribe', text, icon='edit')

class ProductSeriesBugsMenu(ApplicationMenu):

    usedfor = IProductSeries
    facet = 'bugs'
    links = (
        'new',
        'nominations',
        'subscribe',
        )

    def new(self):
        return Link('+filebug', 'Report a bug', icon='add')

    def nominations(self):
        return Link('+nominations', 'Review nominations', icon='bug')

    def subscribe(self):
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
        text = 'List all blueprints'
        return Link('+specs?show=all', text, icon='info')

    def listaccepted(self):
        text = 'List approved blueprints'
        return Link('+specs?acceptance=accepted', text, icon='info')

    def listproposed(self):
        text = 'List proposed blueprints'
        return Link('+specs?acceptance=proposed', text, icon='info')

    def listdeclined(self):
        text = 'List declined blueprints'
        summary = 'Show the goals which have been declined'
        return Link('+specs?acceptance=declined', text, summary, icon='info')

    def setgoals(self):
        text = 'Set series goals'
        summary = 'Approve or decline feature goals that have been proposed'
        return Link('+setgoals', text, summary, icon='edit')

    def table(self):
        text = 'Assignments'
        summary = 'Show the assignee, drafter and approver of these specs'
        return Link('+assignments', text, summary, icon='info')

    def new(self):
        text = 'Register a blueprint'
        summary = 'Register a new blueprint for %s' % self.context.title
        return Link('+addspec', text, summary, icon='add')


class ProductSeriesTranslationsMenuMixIn:
    """Translation menu for ProductSeries.
    """
    def overview(self):
        text = 'Overview'
        return Link('', text)

    @enabled_with_permission('launchpad.Edit')
    def settings(self):
        text = 'Settings'
        return Link('+translations-settings', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def requestbzrimport(self):
        text = 'Request Bazaar import'
        return Link('+request-bzr-import', text)

    @enabled_with_permission('launchpad.Edit')
    def translationupload(self):
        text = 'Upload'
        return Link('+translations-upload', text, icon='add')

    def translationdownload(self):
        text = 'Download'
        return Link('+export', text, icon='download')

    def imports(self):
        text = 'Import queue'
        return Link('+imports', text)


class ProductSeriesOverviewNavigationMenu(NavigationMenu):
    """Overview navigation menus for `IProductSeries` objects."""
    # Suppress the ProductOverviewNavigationMenu from showing on series,
    # release, and milestone pages.
    usedfor = IProductSeries
    facet = 'overview'
    links = ()


class ProductSeriesTranslationsMenu(NavigationMenu,
                                    ProductSeriesTranslationsMenuMixIn):
    """Translations navigation menus for `IProductSeries` objects."""
    usedfor = IProductSeries
    facet = 'translations'
    links = ('overview', 'settings', 'requestbzrimport',
             'translationupload', 'translationdownload',
             'imports')


class ProductSeriesTranslationsExportView(BaseExportView):
    """Request tarball export of productseries' complete translations.

    Only complete downloads are supported for now; there is no option to
    select languages, and templates are always included.
    """

    def processForm(self):
        """Process form submission requesting translations export."""
        pofiles = []
        translation_templates = self.context.getCurrentTranslationTemplates()
        for translation_template in translation_templates:
            pofiles += list(translation_template.pofiles)
        return (translation_templates, pofiles)

    def getDefaultFormat(self):
        templates = self.context.getCurrentTranslationTemplates()
        if len(templates) == 0:
            return None
        return templates[0].source_file_format


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
class ProductSeriesView(LaunchpadView, TranslationsMixin):

    def initialize(self):
        self.form = self.request.form
        self.has_errors = False

        # Whether there is more than one PO template.
        self.has_multiple_templates = len(
            self.context.getCurrentTranslationTemplates()) > 1

        # let's find out what source package is associated with this
        # productseries in the current release of ubuntu
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

        dispatch_table = {
            'set_ubuntu_pkg': self.setCurrentUbuntuPackage,
            'translations_upload': self.translationsUpload,
        }
        dispatch_to = [(key, method)
                        for key,method in dispatch_table.items()
                        if key in self.form
                      ]
        if len(dispatch_to) == 0:
            # None of the know forms have been submitted.
            # XXX CarlosPerelloMarin 2005-11-29 bug=5244:
            # This 'if' should be removed.
            return
        if len(dispatch_to) != 1:
            raise AssertionError(
                "There should be only one command in the form",
                dispatch_to)
        key, method = dispatch_to[0]
        method()

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
        return ICountry(self.request, None)

    def browserLanguages(self):
        return browserLanguages(self.request)

    def translationsUpload(self):
        """Upload new translatable resources related to this IProductSeries.

        Uploads may fail if there are already entries with the same path name
        and uploader (importer) in the queue and the new upload cannot be
        safely matched to any of them.  The user will be informed about the
        failure with a warning message."""
        # XXX henninge 20008-12-03 bug=192925: This code is duplicated for
        # potemplate and pofile and should be unified.

        file = self.request.form['file']
        if not isinstance(file, FileUpload):
            if file == '':
                self.request.response.addErrorNotification(
                    "Ignored your upload because you didn't select a file to"
                    " upload.")
            else:
                # XXX: Carlos Perello Marin 2004-12-30 bug=116:
                # Epiphany seems to have an unpredictable bug with upload
                # forms (or perhaps it's launchpad because I never had
                # problems with bugzilla). The fact is that some uploads don't
                # work and we get a unicode object instead of a file-like
                # object in "file". We show an error if we see that behaviour.
                self.request.response.addErrorNotification(
                    "The upload failed because there was a problem receiving"
                    " the data.")
            return

        filename = file.filename
        content = file.read()

        if len(content) == 0:
            self.request.response.addWarningNotification(
                "Ignored your upload because the uploaded file is empty.")
            return

        translation_import_queue_set = getUtility(ITranslationImportQueue)

        root, ext = os.path.splitext(filename)
        translation_importer = getUtility(ITranslationImporter)
        if ext in translation_importer.supported_file_extensions:
            # Add it to the queue.
            entry = translation_import_queue_set.addOrUpdateEntry(
                filename, content, True, self.user,
                productseries=self.context)
            if entry is None:
                self.request.response.addWarningNotification(
                    "Upload failed.  The name of the file you "
                    "uploaded matched multiple existing "
                    "uploads, for different templates.  This makes it "
                    "impossible to determine which template the new "
                    "upload was for.  Try uploading to a specific "
                    "template: visit the page for the template that you "
                    "want to upload to, and select the upload option "
                    "from there.")
            else:
                self.request.response.addInfoNotification(
                    structured(
                    'Thank you for your upload.  It will be automatically '
                    'reviewed in the next few hours.  If that is not '
                    'enough to determine whether and where your file '
                    'should be imported, it will be reviewed manually by an '
                    'administrator in the coming few days.  You can track '
                    'your upload\'s status in the '
                    '<a href="%s/+imports">Translation Import Queue</a>' %(
                        canonical_url(self.context))))

        elif is_tar_filename(filename):
            # Add the whole tarball to the import queue.
            (num, conflicts) = (
                translation_import_queue_set.addOrUpdateEntriesFromTarball(
                    content, True, self.user,
                    productseries=self.context))

            if num > 0:
                if num == 1:
                    plural_s = ''
                    itthey = 'it'
                else:
                    plural_s = 's'
                    itthey = 'they'
                self.request.response.addInfoNotification(
                    structured(
                    'Thank you for your upload. %d file%s from the tarball '
                    'will be automatically '
                    'reviewed in the next few hours.  If that is not enough '
                    'to determine whether and where your file%s should '
                    'be imported, %s will be reviewed manually by an '
                    'administrator in the coming few days.  You can track '
                    'your upload\'s status in the '
                    '<a href="%s/+imports">Translation Import Queue</a>' %(
                        num, plural_s, plural_s, itthey,
                        canonical_url(self.context))))
                if len(conflicts) > 0:
                    if len(conflicts) == 1:
                        warning = (
                            "A file could not be uploaded because its "
                            "name matched multiple existing uploads, for "
                            "different templates." )
                        ul_conflicts = (
                            "The conflicting file name was:<br /> "
                            "<ul><li>%s</li></ul>" % cgi.escape(conflicts[0]))
                    else:
                        warning = (
                            "%d files could not be uploaded because their "
                            "names matched multiple existing uploads, for "
                            "different templates." % len(conflicts))
                        ul_conflicts = (
                            "The conflicting file names were:<br /> "
                            "<ul><li>%s</li></ul>" % (
                            "</li><li>".join(map(cgi.escape, conflicts))))
                    self.request.response.addWarningNotification(
                        structured(
                        warning + "  This makes it "
                        "impossible to determine which template the new "
                        "upload was for.  Try uploading to a specific "
                        "template: visit the page for the template that you "
                        "want to upload to, and select the upload option "
                        "from there.<br />"+ ul_conflicts))
            else:
                if len(conflicts) == 0:
                    self.request.response.addWarningNotification(
                        "Upload ignored.  The tarball you uploaded did not "
                        "contain any files that the system recognized as "
                        "translation files.")
                else:
                    self.request.response.addWarningNotification(
                        "Upload failed.  One or more of the files you "
                        "uploaded had names that matched multiple existing "
                        "uploads, for different templates.  This makes it "
                        "impossible to determine which template the new "
                        "upload was for.  Try uploading to a specific "
                        "template: visit the page for the template that you "
                        "want to upload to, and select the upload option "
                        "from there.")
        else:
            self.request.response.addWarningNotification(
                "Upload failed because the file you uploaded was not"
                " recognised as a file that can be imported.")

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


class ProductSeriesEditView(LaunchpadEditFormView):

    schema = IProductSeries
    field_names = [
        'name', 'summary', 'status', 'branch', 'releasefileglob']
    custom_widget('summary', TextAreaWidget, height=7, width=62)
    custom_widget('releasefileglob', StrippedTextWidget, displayWidth=40)

    def validate(self, data):
        branch = data.get('branch')
        if branch is not None:
            message = get_series_branch_error(self.context.product, branch)
            if message:
                self.setFieldError('branch', message)

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(self.context)


class ProductSeriesLinkBranchView(LaunchpadEditFormView):
    """View to set the bazaar branch for a product series."""

    schema = IProductSeries
    field_names = ['branch']

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action(_('Update'), name='update')
    def update_action(self, action, data):
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

    schema = IProductSeries
    field_names = ['product', 'name']
    label = 'Review product series details'
    custom_widget('name', TextWidget, width=20)

    @action(_('Change'), name='change')
    def change_action(self, action, data):
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
        self.text = self.request.get('text')
        results = getUtility(ICodeImportSet).getActiveImports(text=self.text)

        self.batchnav = BatchNavigator(results, self.request)


class ProductSeriesFileBugRedirect(LaunchpadView):
    """Redirect to the product's +filebug page."""

    def initialize(self):
        filebug_url = "%s/+filebug" % canonical_url(self.context.product)
        self.request.response.redirect(filebug_url)


class ProductSeriesTranslationsMixin(object):
    """Common properties for all ProductSeriesTranslations*View classes."""

    @property
    def series_title(self):
        return self.context.title.replace(' ', '&nbsp;')

    @property
    def has_imports_enabled(self):
        return (self.context.translations_autoimport_mode !=
                TranslationsBranchImportMode.NO_IMPORT)

    @property
    def request_bzr_import_url(self):
        return canonical_url(self.context,
                             view_name="+request-bzr-import")

    @property
    def link_branch_url(self):
        return canonical_url(self.context, rootsite="mainsite",
                             view_name="+linkbranch")

    @property
    def translations_settings_url(self):
        return canonical_url(self.context,
                             view_name="+translations-settings")

    @property
    def product_edit_url(self):
        return canonical_url(self.context.product, rootsite="mainsite",
                             view_name="+edit")


class SettingsRadioWidget(LaunchpadRadioWidgetWithDescription):
    """Remove the confusing hint under the widget."""

    def __init__(self, field, vocabulary, request):
        super(SettingsRadioWidget, self).__init__(field, vocabulary, request)
        self.hint = None


class ProductSeriesTranslationsSettingsView(LaunchpadEditFormView,
                                            ProductSeriesTranslationsMixin):
    """Edit settings for translations import and export."""

    schema = IProductSeries
    field_names = ['translations_autoimport_mode']
    settings_widget = custom_widget('translations_autoimport_mode',
                  SettingsRadioWidget)

    def __init__(self, context, request):
        super(ProductSeriesTranslationsSettingsView, self).__init__(
            context, request)
        self.cancel_url = canonical_url(self.context)

    @action(u"Save settings", name="save_settings")
    def change_settings_action(self, action, data):
        if (self.context.translations_autoimport_mode !=
            data['translations_autoimport_mode']
            ):
            self.updateContextFromData(data)
            # Request an initial upload of translation files.
            getUtility(IRosettaUploadJobSource).create(
                self.context.branch, NULL_REVISION)
        else:
            self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            _("The settings have been updated."))


class ProductSeriesTranslationsBzrImportView(LaunchpadFormView,
                                             ProductSeriesTranslationsMixin):
    """Edit settings for translations import and export."""

    schema = IProductSeries
    field_names = []

    def __init__(self, context, request):
        super(ProductSeriesTranslationsBzrImportView, self).__init__(
            context, request)
        self.cancel_url = canonical_url(self.context)

    def validate(self, action):
        if self.context.branch is None:
            self.addError(
                "Please set the official Bazaar branch first.")

    @action(u"Request one-time import", name="request_import")
    def request_import_action(self, action, data):
        """ Request an upload of translation files. """
        job = getUtility(IRosettaUploadJobSource).create(
            self.context.branch, NULL_REVISION, True)
        if job is None:
            self.addError(
                _("Your request could not be filed."))
        else:
            self.request.response.addInfoNotification(
                _("The import has been requested."))

