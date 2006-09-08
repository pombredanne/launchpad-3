# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['ProductSeriesNavigation',
           'ProductSeriesOverviewMenu',
           'ProductSeriesFacets',
           'ProductSeriesSpecificationsMenu',
           'ProductSeriesTranslationMenu',
           'ProductSeriesView',
           'ProductSeriesEditView',
           'ProductSeriesAppointDriverView',
           'ProductSeriesRdfView',
           'ProductSeriesSourceSetView',
           'ProductSeriesReviewView',
           'get_series_branch_error']

import cgi
import re

from zope.component import getUtility
from zope.app.form.browser import TextAreaWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import FileUpload

from CVS.protocol import CVSRoot
import pybaz

from canonical.lp.dbschema import ImportStatus, RevisionControlSystems

from canonical.launchpad.helpers import (
    request_languages, browserLanguages, is_tar_filename)
from canonical.launchpad.interfaces import (
    ICountry, IPOTemplateSet, ILaunchpadCelebrities,
    ISourcePackageNameSet, validate_url, IProductSeries,
    ITranslationImportQueue, IProductSeriesSourceSet, NotFoundError)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.webapp import (
    Link, enabled_with_permission, Navigation, ApplicationMenu, stepto,
    canonical_url, LaunchpadView, StandardLaunchpadFacets,
    LaunchpadEditFormView, action, custom_widget
    )
from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.launchpad import _


class ProductSeriesNavigation(Navigation):

    usedfor = IProductSeries

    def breadcrumb(self):
        return 'Series ' + self.context.name

    @stepto('+pots')
    def pots(self):
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(productseries=self.context)

    def traverse(self, name):
        return self.context.getRelease(name)


class ProductSeriesFacets(StandardLaunchpadFacets):

    usedfor = IProductSeries
    enable_only = ['overview', 'specifications', 'translations']


class ProductSeriesOverviewMenu(ApplicationMenu):

    usedfor = IProductSeries
    facet = 'overview'
    links = ['edit', 'driver', 'editsource', 'ubuntupkg',
             'add_package', 'add_milestone', 'add_release',
             'add_potemplate', 'rdf', 'review']

    def edit(self):
        text = 'Change Series Details'
        return Link('+edit', text, icon='edit')

    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals this series'
        return Link('+driver', text, summary, icon='edit')

    def editsource(self):
        text = 'Edit Source'
        return Link('+source', text, icon='edit')

    def ubuntupkg(self):
        text = 'Link to Ubuntu Package'
        return Link('+ubuntupkg', text, icon='edit')

    def add_package(self):
        text = 'Link to Any Package'
        return Link('+addpackage', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def add_milestone(self):
        text = 'Add Milestone'
        summary = 'Register a new milestone for this series'
        return Link('+addmilestone', text, summary, icon='add')

    def add_release(self):
        text = 'Register a Release'
        return Link('+addrelease', text, icon='add')

    def rdf(self):
        text = 'Download RDF Metadata'
        return Link('+rdf', text, icon='download')

    @enabled_with_permission('launchpad.Admin')
    def add_potemplate(self):
        text = 'Add Translation Template'
        return Link('+addpotemplate', text, icon='add')

    @enabled_with_permission('launchpad.Admin')
    def review(self):
        text = 'Review Series Details'
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
        text = 'Show All'
        return Link('+specs?show=all', text, icon='info')

    def listaccepted(self):
        text = 'Show Approved'
        return Link('+specs?acceptance=accepted', text, icon='info')

    def listproposed(self):
        text = 'Show Proposed'
        return Link('+specs?acceptance=proposed', text, icon='info')

    def listdeclined(self):
        text = 'Show Declined'
        summary = 'Show the goals which have been declined'
        return Link('+specs?acceptance=declined', text, summary, icon='info')

    def setgoals(self):
        text = 'Set Goals'
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
        text = 'Upload Translations'
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

def validate_cvs_root(cvsroot, cvsmodule):
    try:
        root = CVSRoot(cvsroot + '/' + cvsmodule)
    except ValueError:
        return False
    valid_module = re.compile('^[a-zA-Z][a-zA-Z0-9_/.+-]*$')
    if not valid_module.match(cvsmodule):
        return False
    # 'CVS' is illegal as a module name
    if cvsmodule == 'CVS':
        return False
    if root.method == 'local' or root.hostname.count('.') == 0:
        return False
    return True

def validate_cvs_branch(branch):
    if not len(branch):
        return False
    valid_branch = re.compile('^[a-zA-Z][a-zA-Z0-9_-]*$')
    if valid_branch.match(branch):
        return True
    return False

def validate_release_root(repo):
    return validate_url(repo, ["http", "https", "ftp"])

def validate_svn_repo(repo):
    return validate_url(repo, ["http", "https", "svn", "svn+ssh"])


# A View Class for ProductSeries
#
# XXX: We should be using autogenerated add forms and edit forms so that
# this becomes maintainable and form validation handled for us.
# Currently, the pages just return 'System Error' as they trigger database
# constraints. -- StuartBishop 20050502
class ProductSeriesView(LaunchpadView):

    def initialize(self):
        self.product = self.context.product
        self.form = self.request.form
        self.displayname = self.context.displayname
        self.summary = self.context.summary
        self.rcstype = self.context.rcstype
        self.cvsroot = self.context.cvsroot
        self.cvsmodule = self.context.cvsmodule
        self.cvsbranch = self.context.cvsbranch
        self.svnrepository = self.context.svnrepository
        self.releaseroot = self.context.releaseroot
        self.releasefileglob = self.context.releasefileglob
        self.targetarcharchive = self.context.targetarcharchive
        self.targetarchcategory = self.context.targetarchcategory
        self.targetarchbranch = self.context.targetarchbranch
        self.targetarchversion = self.context.targetarchversion
        self.name = self.context.name
        self.has_errors = False
        if self.context.product.project:
            self.default_targetarcharchive = self.context.product.project.name
            self.default_targetarcharchive += '@bazaar.ubuntu.com'
        else:
            self.default_targetarcharchive = self.context.product.name
            self.default_targetarcharchive += '@bazaar.ubuntu.com'
        self.default_targetarchcategory = self.context.product.name
        if self.cvsbranch:
            self.default_targetarchbranch = self.cvsbranch
        else:
            self.default_targetarchbranch = self.context.name
        self.default_targetarchversion = '0'
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
            'edit_productseries_source': self.editSource,
            'admin_productseries_source': self.adminSource,
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

    def rcs_selector(self):
        html = '<select name="rcstype">\n'
        html += '  <option value="cvs" onClick="morf(\'cvs\')"'
        if self.rcstype == RevisionControlSystems.CVS:
            html += ' selected'
        html += '>CVS</option>\n'
        html += '  <option value="svn" onClick="morf(\'svn\')"'
        if self.rcstype == RevisionControlSystems.SVN:
            html += ' selected'
        html += '>Subversion</option>\n'
        html += '</select>\n'
        return html

    def cvs_details_already_in_use(self, cvsroot, cvsmodule, cvsbranch):
        """Check if the CVS details are in use by another ProductSeries.

        Return True if the CVS details don't exist in the database or 
        if it's already set in this ProductSeries, otherwise return False.
        """
        productseries = getUtility(IProductSeriesSourceSet).getByCVSDetails(
            cvsroot, cvsmodule, cvsbranch) 
        if productseries is None or productseries == self.context:
            return True
        else: 
            return False 

    def svn_details_already_in_use(self, svnrepository): 
        """Check if the SVN details are in use by another ProductSeries.

        Return True if the SVN details don't exist in the database or
        if it's already set in this ProductSeries, otherwise return False.
        """
        productseries = getUtility(IProductSeriesSourceSet).getBySVNDetails(
            svnrepository)
        if productseries is None or productseries == self.context:
            return True
        else: 
            return False 

    def editSource(self, fromAdmin=False):
        """Edit the upstream revision control details for this series."""
        form = self.form
        if self.context.syncCertified() and not fromAdmin:
            self.request.response.addErrorNotification(
                    'This Source has been certified and is now '
                    'unmodifiable.'
                    )
            self.has_errors = True
            return
        # get the form content, defaulting to what was there
        rcstype = form.get("rcstype")
        if rcstype == 'cvs':
            self.rcstype = RevisionControlSystems.CVS
            self.cvsroot = form.get("cvsroot").strip()
            self.cvsmodule = form.get("cvsmodule").strip()
            self.cvsbranch = form.get("cvsbranch").strip()
            self.svnrepository = None
        elif rcstype == 'svn':
            self.rcstype = RevisionControlSystems.SVN
            self.cvsroot = None 
            self.cvsmodule = None 
            self.cvsbranch = None 
            self.svnrepository = form.get("svnrepository").strip()
        else:
            raise NotImplementedError, 'Unknown RCS %s' % rcstype
        # FTP release details
        self.releaseroot = form.get("releaseroot")
        self.releasefileglob = form.get("releasefileglob") 
        if self.releaseroot:
            if not validate_release_root(self.releaseroot):
                self.request.response.addErrorNotification(
                    'Invalid release root URL')
                self.has_errors = True
                return
        # make sure we at least got something for the relevant rcs
        if rcstype == 'cvs':
            if not (self.cvsroot and self.cvsmodule and self.cvsbranch):
                if not fromAdmin:
                    self.request.response.addErrorNotification(
                        'Please give valid CVS details')
                    self.has_errors = True
                return
            if not validate_cvs_branch(self.cvsbranch):
                self.request.response.addErrorNotification(
                    'Your CVS branch name is invalid.')
                self.has_errors = True
                return
            if not validate_cvs_root(self.cvsroot, self.cvsmodule):
                self.request.response.addErrorNotification(
                    'Your CVS root and module are invalid.')
                self.has_errors = True
                return
            if self.svnrepository:
                self.request.response.addErrorNotification(
                    'Please remove the SVN repository.')
                self.has_errors = True
                return
            if not self.cvs_details_already_in_use(self.cvsroot, self.cvsmodule,
                    self.cvsbranch):
                self.request.response.addErrorNotification(
                    'CVS repository details already in use by another product.')
                self.has_errors = True
                return
        elif rcstype == 'svn':
            if not validate_svn_repo(self.svnrepository):
                self.request.response.addErrorNotification(
                    'Please give valid SVN server details.')
                self.has_errors = True
                return
            if (self.cvsroot or self.cvsmodule or self.cvsbranch):
                self.request.response.addErrorNotification(
                    'Please remove the CVS repository details.')
                self.has_errors = True
                return
            if not self.svn_details_already_in_use(self.svnrepository):
                self.request.response.addErrorNotification(
                    'SVN repository details already in use by another product.')
                self.has_errors = True
                return
        oldrcstype = self.context.rcstype
        self.context.rcstype = self.rcstype
        self.context.cvsroot = self.cvsroot
        self.context.cvsmodule = self.cvsmodule
        self.context.cvsbranch = self.cvsbranch
        self.context.svnrepository = self.svnrepository
        self.context.releaseroot = self.releaseroot
        self.context.releasefileglob = self.releasefileglob
        if not fromAdmin:
            self.context.importstatus = ImportStatus.TESTING
        elif (oldrcstype is None and self.rcstype is not None):
            self.context.importstatus = ImportStatus.TESTING
        # make sure we also update the ubuntu packaging if it has been
        # modified
        self.setCurrentUbuntuPackage()
        if not self.has_errors:
            self.request.response.redirect(canonical_url(self.context))

    def adminSource(self):
        """Make administrative changes to the source details of the
        upstream.

        Since this is a superset of the editing function we can
        call the edit method of the view class to get any editing changes,
        then continue parsing the form here, looking for admin-type
        changes.
        """
        form = self.form
        # FTP release details
        self.releaseroot = form.get("releaseroot", self.releaseroot) or None
        self.releasefileglob = form.get("releasefileglob",
                self.releasefileglob) or None
        if self.releaseroot:
            if not validate_release_root(self.releaseroot):
                self.request.response.addErrorNotification(
                    'Invalid release root URL')
                self.has_errors = True
                return
        # look for admin changes and retrieve those
        self.cvsroot = form.get('cvsroot', self.cvsroot) or None
        self.cvsmodule = form.get('cvsmodule', self.cvsmodule) or None
        self.cvsbranch = form.get('cvsbranch', self.cvsbranch) or None
        self.svnrepository = form.get(
            'svnrepository', self.svnrepository) or None
        self.targetarcharchive = form.get(
            'targetarcharchive', self.targetarcharchive).strip() or None
        self.targetarchcategory = form.get(
            'targetarchcategory', self.targetarchcategory).strip() or None
        self.targetarchbranch = form.get(
            'targetarchbranch', self.targetarchbranch).strip() or None
        self.targetarchversion = form.get(
            'targetarchversion', self.targetarchversion).strip() or None
        # validate arch target details
        arch_name_was_set = bool(
            self.targetarcharchive or self.targetarchcategory
            or self.targetarchbranch or self.targetarchversion)
        if arch_name_was_set:
            parser = pybaz.NameParser
            for is_valid_check, value, description in [
                (parser.is_archive_name, self.targetarcharchive, 'archive name'),
                (parser.is_category_name, self.targetarchcategory, 'category'),
                (parser.is_branch_name, self.targetarchbranch, 'branch name'),
                (parser.is_version_id, self.targetarchversion, 'version id')]:
                if not is_valid_check(value):
                    self.request.response.addErrorNotification(
                        'Invalid target Arch %s.' % description)
                    self.has_errors = True

        # possibly resubmit for testing
        if self.context.autoTestFailed() and form.get('resetToAutotest', False):
            self.context.importstatus = ImportStatus.TESTING

        # Return if there were any errors, so as not to update anything.
        if self.has_errors:
            return
        # update the database
        self.context.targetarcharchive = self.targetarcharchive
        self.context.targetarchcategory = self.targetarchcategory
        self.context.targetarchbranch = self.targetarchbranch
        self.context.targetarchversion = self.targetarchversion
        self.context.releaseroot = self.releaseroot
        self.context.releasefileglob = self.releasefileglob
        # find and handle editing changes
        self.editSource(fromAdmin=True)
        if self.form.get('syncCertified', None):
            if not self.context.syncCertified():
                self.context.certifyForSync()
        if self.form.get('autoSyncEnabled', None):
            if not self.context.autoSyncEnabled():
                self.context.enableAutoSync()

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
    field_names = ['name', 'summary', 'user_branch']
    custom_widget('summary', TextAreaWidget, height=7, width=62)

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


class ProductSeriesAppointDriverView(SQLObjectEditView):
    """View class that lets you appoint a driver for a ProductSeries object."""

    def changed(self):
        # If the name changed then the URL changed, so redirect
        self.request.response.redirect(canonical_url(self.context))


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

