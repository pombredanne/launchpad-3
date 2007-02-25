# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['ProductSeriesNavigation',
           'ProductSeriesSOP',
           'ProductSeriesFacets',
           'ProductSeriesOverviewMenu',
           'ProductSeriesSpecificationsMenu',
           'ProductSeriesTranslationMenu',
           'ProductSeriesView',
           'ProductSeriesEditView',
           'ProductSeriesSourceView',
           'ProductSeriesRdfView',
           'ProductSeriesSourceSetView',
           'ProductSeriesReviewView',
           'ProductSeriesShortLink',
           'get_series_branch_error']

import cgi

from BeautifulSoup import BeautifulSoup

from zope.component import getUtility
from zope.app.form.browser import TextAreaWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import FileUpload

from canonical.lp.dbschema import ImportStatus, RevisionControlSystems

from canonical.launchpad.helpers import (
    browserLanguages, is_tar_filename, request_languages)
from canonical.launchpad.interfaces import (
    ICountry, IPOTemplateSet, ILaunchpadCelebrities,
    ISourcePackageNameSet, IProductSeries,
    ITranslationImportQueue, IProductSeriesSet, NotFoundError)
from canonical.launchpad.browser.branchref import BranchRef
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation, DefaultShortLink
from canonical.launchpad.webapp import (
    Link, enabled_with_permission, Navigation, ApplicationMenu, stepto,
    canonical_url, LaunchpadView, StandardLaunchpadFacets,
    LaunchpadEditFormView, action, custom_widget
    )
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.authorization import check_permission

from canonical.widgets.itemswidgets import LaunchpadRadioWidget
from canonical.widgets.textwidgets import StrippedTextWidget

from canonical.launchpad import _


class ProductSeriesNavigation(Navigation, BugTargetTraversalMixin):

    usedfor = IProductSeries

    def breadcrumb(self):
        return 'Series ' + self.context.name

    @stepto('.bzr')
    def dotbzr(self):
        if self.context.series_branch:
            return BranchRef(self.context.series_branch)
        else:
            return None

    @stepto('+pots')
    def pots(self):
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(productseries=self.context)

    def traverse(self, name):
        return self.context.getRelease(name)


class ProductSeriesSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return self.context.product.displayname + ' series:'

    def getMainHeading(self):
        return self.context.name

    def listChildren(self, num):
        # XXX mpt 20061004: Releases, most recent first
        return []

    def countChildren(self):
        return 0

    def listAltChildren(self, num):
        return None

    def countAltChildren(self):
        raise NotImplementedError


class ProductSeriesFacets(StandardLaunchpadFacets):

    usedfor = IProductSeries
    enable_only = ['overview', 'bugs', 'specifications', 'translations']


class ProductSeriesOverviewMenu(ApplicationMenu):

    usedfor = IProductSeries
    facet = 'overview'
    links = ['edit', 'driver', 'editsource', 'ubuntupkg',
             'add_package', 'add_milestone', 'add_release',
             'add_potemplate', 'rdf', 'review']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals this series'
        return Link('+driver', text, summary, icon='edit')

    @enabled_with_permission('launchpad.EditSource')
    def editsource(self):
        text = 'Edit source'
        return Link('+source', text, icon='edit')

    def ubuntupkg(self):
        text = 'Link to Ubuntu package'
        return Link('+ubuntupkg', text, icon='edit')

    def add_package(self):
        text = 'Link to other package'
        return Link('+addpackage', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def add_milestone(self):
        text = 'Add milestone'
        summary = 'Register a new milestone for this series'
        return Link('+addmilestone', text, summary, icon='add')

    def add_release(self):
        text = 'Register a release'
        return Link('+addrelease', text, icon='add')

    def rdf(self):
        text = 'Download RDF metadata'
        return Link('+rdf', text, icon='download')

    @enabled_with_permission('launchpad.Admin')
    def add_potemplate(self):
        text = 'Add translation template'
        return Link('+addpotemplate', text, icon='add')

    @enabled_with_permission('launchpad.Admin')
    def review(self):
        text = 'Review details'
        return Link('+review', text, icon='edit')


class ProductSeriesSpecificationsMenu(ApplicationMenu):
    """Specs menu for ProductSeries.

    This menu needs to keep track of whether we are showing all the
    specs, or just those that are approved/declined/proposed. It should
    allow you to change the set your are showing while keeping the basic
    view intact.
    """

    usedfor = IProductSeries
    facet = 'specifications'
    links = ['roadmap', 'table', 'setgoals', 'listdeclined']

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

    def roadmap(self):
        text = 'Roadmap'
        summary = 'Show the sequence in which specs should be implemented'
        return Link('+roadmap', text, summary, icon='info')


class ProductSeriesTranslationMenu(ApplicationMenu):
    """Translation menu for ProductSeries.
    """

    usedfor = IProductSeries
    facet = 'translations'
    links = ['translationupload', ]

    def translationupload(self):
        text = 'Upload translations'
        return Link('+translations-upload', text, icon='add')


def get_series_branch_error(product, branch):
    """Check if the given branch is suitable for the given product.

    Returns an HTML error message on error, and None otherwise.
    """
    if branch.product != product:
        return ('<a href="%s">%s</a> is not a branch of <a href="%s">%s</a>.'
                % (canonical_url(branch), cgi.escape(branch.unique_name),
                   canonical_url(product), cgi.escape(product.displayname)))
    return None


# A View Class for ProductSeries
#
# XXX: We should be using autogenerated add forms and edit forms so that
# this becomes maintainable and form validation handled for us.
# Currently, the pages just return 'System Error' as they trigger database
# constraints. -- StuartBishop 20050502
class ProductSeriesView(LaunchpadView):

    def initialize(self):
        self.form = self.request.form
        self.has_errors = False

        # Whether there is more than one PO template.
        self.has_multiple_templates = len(self.context.currentpotemplates) > 1

        # let's find out what source package is associated with this
        # productseries in the current release of ubuntu
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.curr_ubuntu_release = ubuntu.currentrelease
        self.setUpPackaging()

        # Check the form submission.
        self.processForm()

    @property
    def languages(self):
        return request_languages(self.request)

    def processForm(self):
        """Process a form if it was submitted."""
        if not self.request.method == "POST":
            # The form was not posted, we don't do anything.
            return

        dispatch_table = {
            'set_ubuntu_pkg': self.setCurrentUbuntuPackage,
            'translations_upload': self.translationsUpload
        }
        dispatch_to = [(key, method)
                        for key,method in dispatch_table.items()
                        if key in self.form
                      ]
        if len(dispatch_to) == 0:
            # None of the know forms have been submitted.
            # XXX 20051129  CarlosPerelloMarin: This 'if' should be removed.
            # For more details look at
            # https://launchpad.net/products/launchpad/+bug/5244
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
            cr = self.curr_ubuntu_release
            self.curr_ubuntu_package = self.context.getPackage(cr)
            cp = self.curr_ubuntu_package
            self.curr_ubuntu_pkgname = cp.sourcepackagename.name
        except NotFoundError:
            pass
        ubuntu = self.curr_ubuntu_release.distribution
        self.ubuntu_history = self.context.getPackagingInDistribution(ubuntu)

    def setCurrentUbuntuPackage(self):
        """Set the Packaging record for this product series in the current
        Ubuntu distrorelease to be for the source package name that is given
        in the form.
        """
        form = self.form
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
        # ubuntu release. if none exists, one will be created
        self.context.setPackaging(self.curr_ubuntu_release, spn, self.user)
        self.setUpPackaging()

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return browserLanguages(self.request)

    def translationsUpload(self):
        """Upload new translatable resources related to this IProductSeries.
        """
        form = self.form

        file = self.request.form['file']
        if not isinstance(file, FileUpload):
            if file == '':
                self.request.response.addErrorNotification(
                    "Ignored your upload because you didn't select a file to"
                    " upload.")
            else:
                # XXX: Carlos Perello Marin 2004/12/30
                # Epiphany seems to have an unpredictable bug with upload
                # forms (or perhaps it's launchpad because I never had
                # problems with bugzilla). The fact is that some uploads don't
                # work and we get a unicode object instead of a file-like
                # object in "file". We show an error if we see that behaviour.
                # For more info, look at bug #116.
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

        if filename.endswith('.pot') or filename.endswith('.po'):
            # Add it to the queue.
            translation_import_queue_set.addOrUpdateEntry(
                filename, content, True, self.user,
                productseries=self.context)

            self.request.response.addInfoNotification(
                'Thank you for your upload. The file content will be'
                ' reviewed soon by an admin and then imported into Rosetta.'
                ' You can track its status from the <a href="%s">Translation'
                ' Import Queue</a>' %
                    canonical_url(translation_import_queue_set))

        elif is_tar_filename(filename):
            # Add the whole tarball to the import queue.
            num = translation_import_queue_set.addOrUpdateEntriesFromTarball(
                content, True, self.user,
                productseries=self.context)

            if num > 0:
                self.request.response.addInfoNotification(
                    'Thank you for your upload. %d files from the tarball'
                    ' will be reviewed soon by an admin and then imported'
                    ' into Rosetta. You can track its status from the'
                    ' <a href="%s">Translation Import Queue</a>' % (
                        num,
                        canonical_url(translation_import_queue_set)))
            else:
                self.request.response.addWarningNotification(
                    "Nothing has happened. The tarball you uploaded does not"
                    " contain any file that the system can understand.")
        else:
            self.request.response.addWarningNotification(
                "Ignored your upload because the file you uploaded was not"
                " recognised as a file that can be imported.")


class ProductSeriesEditView(LaunchpadEditFormView):

    schema = IProductSeries
    field_names = ['name', 'summary', 'user_branch', 'releasefileglob']
    custom_widget('summary', TextAreaWidget, height=7, width=62)
    custom_widget('releasefileglob', StrippedTextWidget, displayWidth=40)

    def validate(self, data):
        branch = data.get('user_branch')
        if branch is not None:
            message = get_series_branch_error(self.context.product, branch)
            if message:
                self.setFieldError('user_branch', message)

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(self.context)


class ProductSeriesSourceView(LaunchpadEditFormView):
    """View for editing upstream RCS details for the product series.

    This form is protected by the launchpad.EditSource permission,
    which basically allows anyone to edit the details until the import
    has been certified (at which point only vcs-imports team members
    can edit it).

    In addition, users with launchpad.Admin (i.e. vcs-imports team
    members or administrators) permission are provided with a few
    extra buttons to certify the import or reset failed test imports.
    """
    schema = IProductSeries
    field_names = ['rcstype', 'user_branch', 'cvsroot', 'cvsmodule',
                   'cvsbranch', 'svnrepository']

    custom_widget('rcstype', LaunchpadRadioWidget)
    custom_widget('cvsroot', StrippedTextWidget, displayWidth=50)
    custom_widget('cvsmodule', StrippedTextWidget, displayWidth=20)
    custom_widget('cvsbranch', StrippedTextWidget, displayWidth=20)
    custom_widget('svnrepository', StrippedTextWidget, displayWidth=50)

    def setUpWidgets(self):
        LaunchpadEditFormView.setUpWidgets(self)

        # Extract the radio buttons from the rcstype widget, so we can
        # display them separately in the form.
        soup = BeautifulSoup(self.widgets['rcstype']())
        [norcs_button, cvs_button,
         svn_button, empty_marker] = soup.findAll('input')
        norcs_button['onclick'] = 'updateWidgets()'
        cvs_button['onclick'] = 'updateWidgets()'
        svn_button['onclick'] = 'updateWidgets()'
        self.rcstype_none = str(norcs_button)
        self.rcstype_cvs = str(cvs_button)
        self.rcstype_svn = str(svn_button)
        self.rcstype_emptymarker = str(empty_marker)

    def validate(self, data):
        rcstype = data.get('rcstype')
        if 'rcstype' in data:
            # Make sure fields for unselected revision control systems
            # are blanked out:
            if rcstype != RevisionControlSystems.CVS:
                data['cvsroot'] = None
                data['cvsmodule'] = None
                data['cvsbranch'] = None
            if rcstype != RevisionControlSystems.SVN:
                data['svnrepository'] = None

        if rcstype == RevisionControlSystems.CVS:
            cvsroot = data.get('cvsroot')
            cvsmodule = data.get('cvsmodule')
            cvsbranch = data.get('cvsbranch')
            # Make sure there is an error set for these fields if they
            # are unset.
            if not (cvsroot or self.getWidgetError('cvsroot')):
                self.setFieldError('cvsroot',
                                   'Please enter a CVS root.')
            if not (cvsmodule or self.getWidgetError('cvsmodule')):
                self.setFieldError('cvsmodule',
                                   'Please enter a CVS module.')
            if not (cvsbranch or self.getWidgetError('cvsbranch')):
                self.setFieldError('cvsbranch',
                                   'Please enter a CVS branch.')
            if cvsroot and cvsmodule and cvsbranch:
                series = getUtility(IProductSeriesSet).getByCVSDetails(
                    cvsroot, cvsmodule, cvsbranch)
                if self.context != series and series is not None:
                    self.addError('CVS repository details already in use '
                                  'by another product.')

        elif rcstype == RevisionControlSystems.SVN:
            svnrepository = data.get('svnrepository')
            if not (svnrepository or self.getWidgetError('svnrepository')):
                self.setFieldError('svnrepository',
                                   'Please give valid Subversion server '
                                   'details.')
            if svnrepository:
                series = getUtility(IProductSeriesSet).getBySVNDetails(
                    svnrepository)
                if self.context != series and series is not None:
                    self.setFieldError('svnrepository',
                                       'Subversion repository details '
                                       'already in use by another product.')

        if self.resettoautotest_action.submitted():
            if rcstype is None:
                self.addError('Can not rerun import without CVS or '
                              'Subversion details.')
        elif self.certify_action.submitted():
            if rcstype is None:
                self.addError('Can not certify import without CVS or '
                              'Subversion details.')
            if self.context.syncCertified():
                self.addError('Import has already been approved.')

    def isAdmin(self):
        return check_permission('launchpad.Admin', self.context)

    @action(_('Update RCS Details'), name='update')
    def update_action(self, action, data):
        old_rcstype = self.context.rcstype
        self.updateContextFromData(data)
        if self.context.rcstype is None:
            self.context.importstatus = None
        else:
            if not self.isAdmin() or (old_rcstype is None and
                                      self.context.rcstype is not None):
                self.context.importstatus = ImportStatus.TESTING
        self.request.response.addInfoNotification(
            'Upstream RCS details updated.')

    def allowResetToAutotest(self, action):
        return self.isAdmin() and self.context.autoTestFailed()

    @action(_('Rerun import in the Autotester'), name='resettoautotest',
            condition=allowResetToAutotest)
    def resettoautotest_action(self, action, data):
        self.updateContextFromData(data)
        self.context.importstatus = ImportStatus.TESTING
        self.request.response.addInfoNotification(
            'Source import reset to TESTING')

    def allowCertify(self, action):
        return self.isAdmin() and not self.context.syncCertified()

    @action(_('Approve import for production and publication'), name='certify',
            condition=allowCertify)
    def certify_action(self, action, data):
        self.updateContextFromData(data)
        self.context.certifyForSync()
        self.request.response.addInfoNotification(
            'Source import certified for publication')

    @property
    def next_url(self):
        return canonical_url(self.context)


class ProductSeriesReviewView(SQLObjectEditView):

    def changed(self):
        """Redirect to the productseries page.

        We need this because people can now change productseries'
        product and name, and this will make the canonical_url change too.
        """
        self.request.response.addInfoNotification(
            _('This Series has been changed'))
        self.request.response.redirect(canonical_url(self.context))


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


class ProductSeriesSourceSetView:
    """This is a view class that supports a page listing all the
    productseries upstream code imports. This used to be the SourceSource
    table but the functionality was largely merged into ProductSeries, hence
    the need for this View class.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.ready = request.form.get('ready', None)
        self.text = request.form.get('text', None)
        try:
            self.importstatus = int(request.form.get('state', None))
        except (ValueError, TypeError):
            self.importstatus = None
        # setup the initial values if there was no form submitted
        if request.form.get('search', None) is None:
            self.ready = 'on'
            self.importstatus = ImportStatus.TESTING.value

        self.batchnav = BatchNavigator(self.search(), request)

    def search(self):
        return self.context.search(ready=self.ready, text=self.text,
                                   forimport=True,
                                   importstatus=self.importstatus)

    def sourcestateselector(self):
        html = '<select name="state">\n'
        html += '  <option value="ANY"'
        if self.importstatus == None:
            html += ' selected'
        html += '>Any</option>\n'
        for enum in ImportStatus.items:
            html += '<option value="'+str(enum.value)+'"'
            if self.importstatus == enum.value:
                html += ' selected'
            html += '>' + str(enum.title) + '</option>\n'
        html += '</select>\n'
        return html
        html += '  <option value="DONTSYNC"'
        if self.importstatus == 'DONTSYNC':
            html += ' selected'
        html += '>Do Not Sync</option>\n'
        html += '  <option value="TESTING"'
        if self.importstatus == 'TESTING':
            html += ' selected'
        html += '>Testing</option>\n'
        html += '  <option value="AUTOTESTED"'
        if self.importstatus == 'AUTOTESTED':
            html += ' selected'
        html += '>Auto-Tested</option>\n'
        html += '  <option value="PROCESSING"'
        if self.importstatus == 'PROCESSING':
            html += ' selected'
        html += '>Processing</option>\n'
        html += '  <option value="SYNCING"'
        if self.importstatus == 'SYNCING':
            html += ' selected'
        html += '>Syncing</option>\n'
        html += '  <option value="STOPPED"'
        if self.importstatus == 'STOPPED':
            html += ' selected'
        html += '>Stopped</option>\n'


class ProductSeriesShortLink(DefaultShortLink):

    def getLinkText(self):
        return self.context.displayname
