"""Soyuz

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# sqlobject/sqlos
from sqlobject import LIKE, LIKE, AND
from canonical.database.sqlbase import quote

# lp imports
from canonical.lp import dbschema
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

# database imports
from canonical.launchpad.database import WikiName
from canonical.launchpad.database import JabberID 
from canonical.launchpad.database import TeamParticipation, Membership
from canonical.launchpad.database import EmailAddress, IrcID
from canonical.launchpad.database import GPGKey, ArchUserID 
from canonical.launchpad.database import createPerson
from canonical.launchpad.database import createTeam
from canonical.launchpad.database import getPermission

# interface import
from canonical.launchpad.database import IPerson

# zope imports
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# app components
from canonical.launchpad.database import Distribution, DistroRelease, Person
from canonical.soyuz.importd import ProjectMapper, ProductMapper

# Stock View 
from canonical.rosetta.browser import ViewProduct

##XXX: (batch_size+global) cprov 20041003
## really crap constant definition for BatchPages 
BATCH_SIZE = 40

class DistrosSearchView(object):
    """
    DistroSearchView:
    This Views able the user to search on all distributions hosted on
    Soyuz by Name Distribution Title (Dispalyed name),  
    """
    ##TODO: (class+doc) cprov 20041003
    ## This is the EpyDoc Class Document Format,
    ## Does it fits our expectations ? (except the poor content)
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def search_action(self):
        enable_results = False
        name = self.request.get("name", "")
        title = self.request.get("title", "")
        description = self.request.get("description", "")

        if name or title or description:
            name = name.replace('%', '%%')
            title = title.replace('%', '%%')
            description = description.replace('%', '%%')

            name_like = LIKE(Distribution.q.name,
                             "%%" + name + "%%")
            title_like = LIKE(Distribution.q.title,
                              "%%" + title + "%%")
            description_like = LIKE(Distribution.q.\
                                    description,
                                    "%%" + description + "%%")

##XXX: (case+insensitive) cprov 20041003
## Performe case insensitive queries using ILIKE doesn't work
## properly, since we don't have ILIKE method on SQLObject
## ===============================================================            
#            name_like = ("name ILIKE %s" % "%%" + name + "%%")
#            title_like = ("title ILIKE %s" % "%%" + title + "%%")
#            description_like = ("description ILIKE %s" % "%%"\
#                                + description + "%%")
#=================================================================

            query = AND(name_like, title_like, description_like) 

            self.results = Distribution.select(query)
            self.entries = self.results.count()
            enable_results = True                

        return enable_results

class DistrosAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []


    def add_action(self):
        enable_added = False
        
        name = self.request.get("name", "")
        title = self.request.get("title", "")
        description = self.request.get("description", "")

        if name or title or description:
            ##XXX: (uniques) cprov 20041003

            ##XXX: (authserver) cprov 20041003
            ## The owner is hardcoded to Mark.
            ## Authserver Security/Authentication Issues ?!?!
            self.results = Distribution(name=name, title=title, \
                                             description=description,\
                                             domainname='domain', owner=1)
            ##XXX: (results) cprov 20041003
            enable_added = True

        return enable_added

class DistrosEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.permission = False
        self.person = IPerson(self.request.principal, None)

        if self.person:
            
            if self.person.id == self.context.distribution.owner.id:
                self.permission = True

    def edit_action(self):
        enable_edited = False
        if not self.permission:
            return False
        
        name = self.request.get("name", "")
        title = self.request.get("title", "")
        description = self.request.get("description", "")

        if (name or title or description):
            ##XXX: (uniques) cprov 20041003
            ## again :)
            self.context.distribution.name = name
            self.context.distribution.title = title
            self.context.distribution.description = description
            enable_edited = True

        return enable_edited

class ReleasesAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def add_action(self):
        enable_added = False

        name = self.request.get("name", "")
        title = self.request.get("title", "")
        shortdesc = self.request.get("shortdesc", "")
        description = self.request.get("description", "")
        version = self.request.get("version", "")

        if name or title or description or version:
            ##XXX: (uniques) cprov 20041003
            ## again

            ##XXX: (utc) cprov 20041003
            ## Get current UTC as timestamp 

            ##XXX: (components/section) cprov 20041003
            ## What about figure out finally what to do with
            ##   components, sections ans so on ...

            ##XXX: (parentrelease) cprov 20041003
            ## Parentrelease is hardcoded to "warty", should the users
            ## be able to select then now ??
            
            self.results = DistroRelease(distribution=self.context.distribution.id,
                                         name=name, title=title,
                                         shortdesc=shortdesc,
                                         description=description,version=version,
                                         components=1, releasestate=1,sections=1,
                                         datereleased='2004-08-15 10:00', owner=1,
                                         parentrelease=1, lucilleconfig='')
            ##XXX: (results) cprov 20041003
            ## again
            enable_added = True
        return enable_added

##XXX: (batch+duplicated) cprov 20041006
## The two following classes are almost like a duplicated piece
## of code. We should look for a better way for use Batching Pages
class DistroReleaseSourcesView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sourcePackagesBatchNavigator(self):
        source_packages = list(self.context)
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = source_packages, start = start,
                      size = batch_size)

        return BatchNavigator(batch = batch, request = self.request)

class DistroReleaseView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def bugSourcePackagesBatchNavigator(self):
        source_packages = list(self.context.bugSourcePackages())
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = source_packages, start = start,
                      size = batch_size)

        return BatchNavigator(batch = batch, request = self.request)

class DistroReleaseBinariesView(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def binaryPackagesBatchNavigator(self):
        binary_packages = list(self.context)
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = binary_packages, start = start,
                      size = batch_size)

        return BatchNavigator(batch = batch, request = self.request)

class ReleaseEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.permission = False
        self.person = IPerson(self.request.principal, None)
        
        if self.person:

            if self.person.id == self.context.release.owner.id:
                self.permission = True
                

    def edit_action(self):
        enable_edited = False
        if not self.permission:
            return False
        
        name = self.request.get("name", "")
        title = self.request.get("title", "")
        shortdesc = self.request.get("shortdesc", "")
        description = self.request.get("description", "")
        version = self.request.get("version", "")

        if name or title or description or version:
            ##XXX: (uniques) cprov 20041003
            self.context.release.name = name
            self.context.release.title = title
            self.context.release.shortdesc = shortdesc
            self.context.release.description = description
            self.context.release.version = version
            ##XXX: (results) cprov 20041003
            enble_edited = True

        return enable_edited

class ReleaseSearchView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.sources = []
        self.binaries = []


    def search_action(self):
        enable_result = False        
        name = self.request.get("name", "")

        if name:
            self.sources = list(self.context.findSourcesByName(name))
            self.binaries = list(self.context.findBinariesByName(name))
            enable_result = True
        else:
            self.sources = []
            self.binaries = []

        return enable_result

##XXX: (batch+duplicated) cprov 20041003
## AGAIN !!!

class DistrosReleaseSourcesSearchView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def searchSourcesBatchNavigator(self):        

        name = self.request.get("name", "")

        if name:
            source_packages = list(self.context.findPackagesByName(name))
            start = int(self.request.get('batch_start', 0))
            end = int(self.request.get('batch_end', BATCH_SIZE))
            batch_size = BATCH_SIZE
            batch = Batch(list = source_packages, start = start,
                          size = batch_size)
            return BatchNavigator(batch = batch,
                                  request = self.request)
        else:
            return None

class DistrosReleaseBinariesSearchView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def searchBinariesBatchNavigator(self):        

        name = self.request.get("name", "")

        if name:
            binary_packages = list(self.context.findPackagesByName(name))
            start = int(self.request.get('batch_start', 0))
            end = int(self.request.get('batch_end', BATCH_SIZE))
            batch_size = BATCH_SIZE
            batch = Batch(list = binary_packages, start = start,
                          size = batch_size)
            return BatchNavigator(batch = batch,
                                  request = self.request)
        else:
            return None

class DistroReleaseSourceView(object):
    translationPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-translations-sourcepackage.pt')
    watchPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-distroreleasesource-watch.pt')


    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)


    def productTranslations(self):
        if self.context.sourcepackage.product:
            return ViewProduct(self.context.sourcepackage.product,
                               self.request)
        return None

    def sourcepackageWatch(self):
        if self.person is not None:            
            return True

        return False
    

##XXX: (old+stuff) cprov 20041003
## This Old stuff is unmaintained by Soyuz Team
## is it really necessary, I mean should it be kept here
    
################################################################

# these are here because there is a bug in sqlobject that stub is fixing,
# once fixed they should be nuked, and pages/traverse* set to use getters.
# XXX
def urlTraverseProjects(projects, request, name):
    return projects[str(name)]


class SourceSourceView(object):
    """Present a SourceSource table for a browser."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def edit(self):
        if not self.request.form.get("Update", None)=="Update Upstream Source":
            return
        if not self.request.method == "POST":
            return
        formdata = {}
        #
        # Extract the form data
        #
        title = self.form.get('title', None)
        description = self.form.get('description', None)
        cvsroot = self.form.get('cvsroot', None)
        cvsmodule = self.form.get('cvsmodule', None)
        cvstarfileurl = self.form.get('cvstarfileurl', None)
        cvsbranch = self.form.get('cvsbranch', None)
        svnrepository = self.form.get('svnrepository', None)
        releaseroot = self.form.get('releaseroot', None)
        releaseverstyle = self.form.get('releaseverstyle', None)
        releasefileglob = self.form.get('releasefileglob', None)
        newarchive = self.form.get('newarchive', None)
        archversion = self.form.get('newbranchcategory', None)
        newbranchcategory = self.form.get('newbranchcategory', None)
        newbranchbranch = self.form.get('newbranchbranch', None)
        newbranchversion = self.form.get('newbranchversion', None)
        product = self.form.get('product', None)
        if title: self.context.title = title
        if description: self.context.description = description
        if cvsroot: self.context.cvsroot = cvsroot
        if cvsmodule: self.context.cvsmodule = cvsmodule
        if cvstarfileurl: self.context.cvstarfileurl = cvstarfileurl
        if cvsbranch: self.context.cvsbranch = cvsbranch
        if svnrepository: self.context.svnrepository = svnrepository
        if releaseroot: self.context.releaseroot = releaseroot
        if releaseverstyle: self.context.releaseverstyle = releaseverstyle
        if releasefileglob: self.context.releasefileglob = releasefileglob
        if newarchive: self.context.newarchive = newarchive
        if newbranchcategory: self.context.newbranchcategory = newbranchcategory
        if newbranchbranch: self.context.newbranchbranch = newbranchbranch
        if newbranchversion: self.context.newbranchversion = newbranchversion
        if self.form.get('syncCertified', None):
            if not self.context.syncCertified():
                self.context.certifyForSync()
        if self.form.get('autoSyncEnabled', None):
            if not self.context.autoSyncEnabled():
                self.context.enableAutoSync()
        newurl = None
        if product and self.context.canChangeProduct():
            self.context.changeProduct(product)
            newurl='../../../../' + self.context.product.project.name + "/" + self.context.product.name
        if newurl:
            self.request.response.redirect(newurl)


    def selectedProduct(self):
        return self.context.product.name + "/" + self.context.product.project.name

    def products(self):
        """all the products that context can switch between"""
        """ugly"""
        projMapper=ProjectMapper()
        prodMapper=ProductMapper()
        for project in projMapper.findByName("%%"):
            if project.name != "do-not-use-info-imports":
                for product in prodMapper.findByName("%%", project):
                    name=project.name + "/" + product.name
                    if name != "do-not-use-info-imports/unassigned":
                        yield name


#arch-tag: 985007b4-9c10-4601-b3ce-bdb03576569f
