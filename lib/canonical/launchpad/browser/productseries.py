#
# Copyright (c) 2004-2005 Canonical Ltd
#

import re

from zope.interface import implements
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from CVS.protocol import CVSRoot

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.lp.dbschema import ImportStatus, RevisionControlSystems

from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.browser.productrelease import newProductRelease

__all__ = ['traverseProductSeries', 'ProductSeriesView',
           'ProductSeriesSourceSetView']

def traverseProductSeries(series, request, name):
    return series.getRelease(name)

def validate_cvs_root(cvsroot, cvsmodule):
    try:
        root = CVSRoot(cvsroot + '/' + cvsmodule)
    except ValueError, e:
        return False
    valid_module = re.compile('^[a-zA-Z][a-zA-Z0-9_-]*$')
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

def validate_svn_repo(repo):
    if not repo:
        return False
    import urllib
    scheme, host = urllib.splittype(repo)
    if not scheme in ["http", "https", "svn", "svn+ssh"]:
        return False
    host,path = urllib.splithost(host)
    if not len(host):
        return False
    return True




#
# A View Class for ProductSeries
#
class ProductSeriesView(object):

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-productseries-actions.pt')

    def __init__(self, context, request):
        self.context = context
        self.product = context.product
        self.request = request
        self.form = request.form
        self.errormsgs = []
        self.displayname = self.context.displayname
        self.shortdesc = self.context.shortdesc
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
        if self.context.product.project:
            self.default_targetarcharchive = self.context.product.project.name
            self.default_targetarcharchive += '@projects.ubuntu.com'
        else:
            self.default_targetarcharchive = self.context.product.name
            self.default_targetarcharchive += '@products.ubuntu.com'
        self.default_targetarchcategory = self.context.product.name
        if self.cvsbranch:
            self.default_targetarchbranch = self.cvsbranch
        else:
            self.default_targetarchbranch = self.context.name
        self.default_targetarchversion = '0'

    def namesReviewed(self):
        if not (self.product.active and self.product.reviewed):
            return False
        if not self.product.project:
            return True
        return self.product.project.active and self.product.project.reviewed

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

    def edit(self):
        """
        Update the contents of the ProductSeries. This method is called by a
        tal:dummy element in a page template. It checks to see if a form has
        been submitted that has a specific element, and if so it continues
        to process the form, updating the fields of the database as it goes.
        """
        # check that we are processing the correct form, and that
        # it has been POST'ed
        form = self.form
        if not form.get("Update", None)=="Update Series":
            return
        if not self.request.method == "POST":
            return
        # Extract details from the form and update the Product
        # we don't let people edit the name because it's part of the url
        # XXX sabdfl 14/04/05 we need to do some validation here
        self.context.displayname = form.get('displayname', self.displayname)
        self.context.shortdesc = form.get('shortdesc', self.shortdesc)
        self.context.releaseroot = form.get("releaseroot", self.releaseroot)
        self.context.releasefileglob = form.get("releasefileglob", self.releasefileglob)
        # now redirect to view the product
        self.request.response.redirect(self.request.URL[-1])

    def editSource(self, fromAdmin=None):
        """This method processes the results of an attempt to edit the
        upstream revision control details for this series."""
        # see if anything was posted
        if self.request.method != "POST":
            return
        form = self.form
        if form.get("Update RCS Details", None) is None:
            return
        if self.context.syncCertified() and not fromAdmin:
            self.errormsgs.append('This Source is has been certified and is now unmodifiable.')
            return
        # get the form content, defaulting to what was there
        rcstype=form.get("rcstype", None)
        if rcstype == 'cvs':
            self.rcstype = RevisionControlSystems.CVS
        elif rcstype == 'svn':
            self.rcstype = RevisionControlSystems.SVN
        else:
            raise NotImplementedError, 'Unknown RCS %s' % rcstype
        self.cvsroot = form.get("cvsroot", self.cvsroot)
        self.cvsmodule = form.get("cvsmodule", self.cvsmodule)
        self.cvsbranch = form.get("cvsbranch", self.cvsbranch)
        self.svnrepository = form.get("svnrepository", self.svnrepository)
        # make sure we at least got something for the relevant rcs
        if rcstype == 'cvs':
            if not (self.cvsroot and self.cvsmodule and self.cvsbranch):
                self.errormsgs.append('Please give valid CVS details')
                return
            if not validate_cvs_branch(self.cvsbranch):
                self.errormsgs.append('Your CVS branch name is invalid.')
                return
            if not validate_cvs_root(self.cvsroot, self.cvsmodule):
                self.errormsgs.append('Your CVS root and module are invalid.')
                return
        elif rcstype == 'svn':
            if not validate_svn_repo(self.svnrepository):
                self.errormsgs.append('Please give valid SVN server details')
                return
        self.context.rcstype = self.rcstype
        self.context.cvsroot = self.cvsroot
        self.context.cvsmodule = self.cvsmodule
        self.context.cvsbranch = self.cvsbranch
        self.context.svnrepository = self.svnrepository
        if not fromAdmin:
            self.context.importstatus = ImportStatus.TESTING
        self.request.response.redirect('.')

    def adminSource(self):
        """Make administrative changes to the source details of the
        upstream. Since this is a superset of the editing function we can
        call the edit method of the view class to get any editing changes,
        then continue parsing the form here, looking for admin-type
        changes."""
        # see if anything was posted
        if self.request.method != "POST":
            return
        form = self.form
        if form.get("Update RCS Details", None) is None:
            return
        # look for admin changes and retrieve those
        self.targetarcharchive = form.get('targetarcharchive', self.targetarcharchive)
        self.targetarchcategory = form.get('targetarchcategory', self.targetarchcategory)
        self.targetarchbranch = form.get('targetarchbranch', self.targetarchbranch)
        self.targetarchversion = form.get('targetarchversion', self.targetarchversion)
        # lifeless 29/04/05 need validation
        self.context.targetarcharchive = self.targetarcharchive
        self.context.targetarchcategory = self.targetarchcategory
        self.context.targetarchbranch = self.targetarchbranch
        self.context.targetarchversion = self.targetarchversion
        # find and handle editing changes
        self.editSource()

    def newProductRelease(self):
        """
        Process a submission to create a new ProductRelease
        for this series.
        """
        # figure out who is calling
        owner = IPerson(self.request.principal)
        # XXX sabdfl 09/04/05 we should not be passing the form to the
        # content object, violating the separation between content and
        # presentation. I think this is my old code, but it needs to be
        # fixed nonetheless.
        pr = newProductRelease(self.form, self.context.product, owner,
                               series=self.context.id)
        if pr:
            self.request.response.redirect(pr.version)


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
        self.batch = Batch(self.search(), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

    def search(self):
        return list(self.context.search(ready=self.ready,
                                        text=self.text,
                                        forimport=True,
                                        importstatus=self.importstatus))

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



