"""Soyuz

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# sqlobject/sqlos
from sqlobject import LIKE, LIKE, OR, AND
from canonical.database.sqlbase import quote

# lp imports
from canonical.lp import dbschema
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

# database imports
from canonical.launchpad.database import SourcePackage, WikiName
from canonical.launchpad.database import JabberID 
from canonical.launchpad.database import TeamParticipation, Membership
from canonical.launchpad.database import EmailAddress, IrcID
from canonical.launchpad.database import GPGKey, ArchUserID 
from canonical.launchpad.database import createPerson
from canonical.launchpad.database import createTeam

# interface import
from canonical.launchpad.database import IPerson

# zope imports
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# app components
from canonical.soyuz.sql import Distribution, DistroRelease, Person
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

class PeopleListView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def viewPeopleBatchNavigator(self):
        people = list(Person.select(orderBy='displayname'))
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = people, start = start,
                      size = batch_size)
        return BatchNavigator(batch = batch,
                              request = self.request)    

class PeopleSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []


    def searchPeopleBatchNavigator(self):
        name = self.request.get("name", "")

        if name:
            people = list(self._findPeopleByName(name))
            start = int(self.request.get('batch_start', 0))
            end = int(self.request.get('batch_end', BATCH_SIZE))
            batch_size = BATCH_SIZE
            batch = Batch(list = people, start = start,
                          size = batch_size)
            return BatchNavigator(batch = batch,
                                  request = self.request)
        else:
            return None

    def _findPeopleByName(self, name):
        name = name.replace('%', '%%')
        query = quote('%%'+ name.upper() + '%%')
        return Person.select("""UPPER(displayname) LIKE %s
        OR UPPER(teamdescription) LIKE %s ORDER by displayname"""%(query,
                                                                   query))


class PeopleAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.error_msg = None


    def add_action(self):
        displayname = self.request.get("displayname", "")
        givenname = self.request.get("givenname", "")
        familyname = self.request.get("familyname", "")
        email = self.request.get("email", "")
        password = self.request.get("password", "")
        retype = self.request.get("retype", "")

        if displayname:
            if password != retype:
                self.error_msg = 'Password does not match'
                return False

            self.results = createPerson(displayname, givenname, familyname,
                                        password, email)

            if not self.results:
                # it happens when generate_nick returns
                # a nick that already exists
                self.error_msg = 'Unhandled error creating person'
                return False

            return True

        return False
        
class TeamAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.error_msg = None
        self.permission = False
        self.person = IPerson(self.request.principal, None)
        
        if self.person:
            pid = self.person.id
            
            if pid == self.context.person.id:
                self.permission = True

            if self.context.person.teamowner:
                if pid == self.context.person.teamowner.id:
                    self.permission = True


    def add_action(self):
        enable_added = False

        if not self.permission:
            return False
    
        displayname = self.request.get("displayname", "")
        teamdescription = self.request.get("teamdescription", "")
        email = self.request.get("email", "")
        password = self.request.get("password", "")
        retype = self.request.get("retype", "")

        ##XXX: (uniques) cprov 20041003        
        if displayname:
            if password != retype:
                self.error_msg = 'Password does not match'
                return enable_added

            if self.person:
                teamowner = self.person.id
            
            self.results = createTeam(displayname,
                                      teamowner,
                                      teamdescription,
                                      password,
                                      email)
            
            if not self.results:
                # it happens when generate_nick returns
                # a nick that already exists
                self.error_msg = 'Unhandled error creating person'
                return enable_added

            enable_added = True

        return enable_added
            

class TeamJoinView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)

            
    def join_action(self):
        ## XXX: (proposed+member) cprov 20041003
        ##  Join always as PROPOSED MEMBER 
        role = dbschema.MembershipRole.MEMBER.value
        status = dbschema.MembershipStatus.PROPOSED.value

        if self.person:
            ##XXX: (uniques) cprov 20041003
            Membership(personID=self.person.id,
                       teamID=self.context.id,
                       role=role,
                       status=status)
            
            ##XXX: (teamparticipation) cprov 20041003
            ## How to do it recursively as it is suposed to be,
            ## I mean flatten participation ...            
            TeamParticipation(personID=self.person.id,
                              teamID=self.context.id)
            return True
        
        return False

class TeamUnjoinView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)
            
    def unjoin_action(self):

        if self.person:            
            teampart = TeamParticipation.selectBy(personID=self.person.id,
                                                  teamID=self.context.id)[0]

            membership = Membership.selectBy(personID=self.person.id,
                                             teamID=self.context.id)[0]
            teampart.destroySelf()
            membership.destroySelf()
            
            return True

        return False
        
                    
class PersonView(object):
    ## XXX:  cprov 20041101
    ## Use the already done malone portlet !!!!
    bugsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-bugs.pt')

    teamsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-teams.pt')

    subteamsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-subteams.pt')

    membershipPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-membership.pt')


    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)
        
    def is_member(self):

        if self.person and self.context.person.teamowner:

            membership = Membership.selectBy(personID=self.person.id,
                                             teamID=self.context.id)
            if membership.count() > 0:
                return True
        
        return False

class PersonPackagesView(object):
    packagesPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-packages.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

class PersonEditView(object):
    emailPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-email.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.permission = False
        self.person = IPerson(self.request.principal, None)
        
        if self.person:
            pid = self.person.id
            
            if pid == self.context.person.id:
                self.permission = True

            if self.context.person.teamowner:
                if pid == self.context.person.teamowner.id:
                    self.permission = True
            
    def email_action(self):

        if not self.permission:
            return False

        email = self.request.get("email", "")
        new_email = self.request.get("new_email", "")
        operation = self.request.get("operation", "")
        valid = int(dbschema.EmailAddressStatus.VALIDATED)
        person = self.context.person.id

        if operation == 'add' and new_email:

            res = EmailAddress(email=new_email,
                               personID=person,
                               status=valid)                              
            return res

        elif operation == 'edit' and new_email:

            result = EmailAddress.selectBy(email=email)[0]
            result.email = new_email 
            return result

        elif operation == 'delete':
            result = EmailAddress.selectBy(email=email)[0]
            result.destroySelf()
            return True
        else:
            return False
        


    def edit_action(self):
        enable_edited = False
        if not self.permission:
            return False

        displayname = self.request.get("displayname", "")
        givenname = self.request.get("givenname", "")
        familyname = self.request.get("familyname", "")
        teamdescription = self.request.get("teamdescription", "")

        wiki = self.request.get("wiki", "")
        wikiname = self.request.get("wikiname", "")
        network = self.request.get("network", "")
        nickname = self.request.get("nickname", "")
        jabberid = self.request.get("jabberid", "")
        archuserid = self.request.get("archuserid", "")
        #gpgid = self.request.get("gpgid", "")
        
        ##XXX: (uniques) cprov 20041003
        if displayname :
            self.context.person.displayname = displayname
            self.context.person.givenname = givenname
            self.context.person.familyname = familyname
            self.context.person.teamdescription = teamdescription
            enable_edited = True            

            #WikiName
            if self.context.wiki:
                self.context.wiki.wiki = wiki
                self.context.wiki.wikiname = wikiname
                enable_edited = True
            else:
                if wiki or wikiname:
                    person = self.context.person.id
                    self.context.wiki = WikiName(personID=person,
                                                 wiki=wiki,
                                                 wikiname=wikiname)
                    enable_edited = True
                else:
                    self.context.wiki = None

            #IrcID
            if self.context.irc:
                self.context.irc.network = network
                self.context.irc.nickname = nickname
                enable_edited = True
            else:
                if network or nickname:
                    person = self.context.person.id
                    self.context.irc = IrcID(personID=person,
                                             network=network,
                                             nickname=nickname)
                    enable_edited = True
                else:
                    self.context.irc = None
                    
            #JabberID    
            if self.context.jabber:
                self.context.jabber.jabberid = jabberid
                enable_edited = True
            else:
                if jabberid:
                    person = self.context.person.id                    
                    self.context.jabber = JabberID(personID=person,
                                                   jabberid=jabberid)
                    enable_edited = True
                else:
                    self.context.jabber = None
                    
            #ArchUserID
            if self.context.archuser:
                self.context.archuser.archuserid = archuserid
                enable_edited = True
            else:
                if archuserid:
                    person = self.context.person.id                    
                    self.context.archuser = ArchUserID(personID=person,
                                                       archuserid=archuserid)
                    enable_edited = True
                else:
                    self.context.archuser = None
##TODO: (gpg+portlet) cprov 20041003
## GPG key handling requires a specific Portlet to handle key imports and
##  validation
#             #GPGKey
#             if self.context.gpg:
#                 self.context.gpg.keyid = gpgid
#                 self.context.gpg.fingerprint = fingerprint
#                 self.enable_edited = True
#             else:
#                 if gpgid:
#                     pubkey = 'sample%d'%self.context.id
#                     person = self.context.person.id
#                     self.context.gpg = GPGKey(personID=person,
#                                               keyid=gpgid,
#                                               fingerprint=fingerprint,
#                                               pubkey=pubkey,
#                                               revoked=False)
#                 else:
#                     self.context.gpg = None

        return enable_edited

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
