# sqlobject/sqlos
from sqlobject import LIKE, AND

# lp imports
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.lp import dbschema                       

# zope imports
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# interface import
from canonical.launchpad.interfaces import IPerson

from canonical.launchpad.database import Distribution, DistroRelease
from canonical.launchpad.database import Person
from canonical.launchpad.database import DistributionRole
from canonical.launchpad.database import DistroReleaseRole


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
        person = IPerson(self.request.principal, None)
        
        if (name or title or description) and person:
            ##XXX: (uniques) cprov 20041003

            ##XXX: (authserver) cprov 20041003
            ## The owner is hardcoded to Mark.
            ## Authserver Security/Authentication Issues ?!?!
            self.results = Distribution(name=name, title=title, 
                                        description=description,
                                        domainname='domain',
                                        owner=person.id)
            ##XXX: (results) cprov 20041003
            enable_added = True

        return enable_added

class DistrosEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def edit_action(self):
        enable_edited = False
        
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

        distro_id = self.context.distribution.id
        person = IPerson(self.request.principal, None)        
   
        if (name or title or description or version) and person:
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
            
            self.results = DistroRelease(distribution=distro_id,
                                         name=name, title=title,
                                         shortdesc=shortdesc,
                                         description=description,
                                         version=version,
                                         owner=person.id,
                                         components=1,
                                         releasestate=1,
                                         sections=1,
                                         parentrelease=1,
                                         datereleased='2004-08-15 10:00',
                                         lucilleconfig='')
            ##XXX: (results) cprov 20041003
            ## again
            enable_added = True
        return enable_added

class ReleaseEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def edit_action(self):
        enable_edited = False
        
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


class AddRoleViewBase(object):
    rolesPortlet = None
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.roles = dbschema.DistributionRole.items
        self.people = Person.select(orderBy='displayname')

    def is_owner(self):
        person = IPerson(self.request.principal, None)
        if not person:
            return False

        # XXX: cprov 20041202
        # verify also the DistributionRoles for persons with Admin Role
        owner = self.get_container().owner
        return owner.id == person.id

    def add_role(self):
        person = self.request.get("person", "")
        role = self.request.get("role", "")

        if not (person and role):
            return False

        container = self.get_container()
        # XXX: check for duplicates -- user,role should be unique.

        # XXX: change to container.create_role (?)
        return self.create_role(container.id, person, role)


class AddDistroRoleView(AddRoleViewBase):
    rolesPortlet = ViewPageTemplateFile(
        '../templates/portlet-distroroles.pt')

    def get_container(self):
        return self.context.distribution

    # XXX rename!
    def get_roles(self):
        # XXX: rename roles to role_members
        return self.context.distribution.roles

    def create_role(self, container_id, person, role):
        return DistributionRole(distribution=container_id,
                                personID=person, role=role)


class AddDistroReleaseRoleView(AddRoleViewBase):
    rolesPortlet = ViewPageTemplateFile(
        '../templates/portlet-distroroles.pt')

    def get_container(self):
        return self.context.release
    
    # XXX rename!
    def get_roles(self):
        # XXX: move to DistroRelease.role_members (?)
        return DistroReleaseRole.selectBy(distroreleaseID=\
                                          self.context.release.id)        

    def create_role(self, container_id, person, role):
        return DistroReleaseRole(distrorelease=container_id,
                                 personID=person, role=role)

