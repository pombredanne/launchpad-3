# sqlobject/sqlos
from sqlobject import LIKE, AND

# lp imports
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.lp import dbschema                       

# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility

# interface import
from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import IDistroTools


# XXX: (batch_size+global) cprov 20041003
# really crap constant definition for BatchPages 
BATCH_SIZE = 40

#
# Distributions
#

class DistrosSearchView(object):
    """
    DistroSearchView:
    This Views able the user to search on all distributions hosted on
    Soyuz by Name Distribution Title (Dispalyed name),  
    """
    # TODO: (class+doc) cprov 20041003
    # This is the EpyDoc Class Document Format,
    # Does it fits our expectations ? (except the poor content)
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def search_action(self):
        name = self.request.get("name", "")
        title = self.request.get("title", "")
        description = self.request.get("description", "")

        if not (name or title or description):
            return False

        name = name.replace('%', '%%')
        title = title.replace('%', '%%')
        description = description.replace('%', '%%')

        name_like = LIKE(Distribution.q.name, "%%" + name + "%%")
        title_like = LIKE(Distribution.q.title, "%%" + title + "%%")
        description_like = LIKE(Distribution.q.description,
                                "%%" + description + "%%")
        query = AND(name_like, title_like, description_like) 

##XXX: (case+insensitive) cprov 20041003
## Performe case insensitive queries using ILIKE doesn't work
## properly, since we don't have ILIKE method on SQLObject
## ===============================================================            
#            name_like = ("name ILIKE %s" % "%%" + name + "%%")
#            title_like = ("title ILIKE %s" % "%%" + title + "%%")
#            description_like = ("description ILIKE %s" % "%%"\
#                                + description + "%%")
#=================================================================

        self.results = Distribution.select(query)
        self.entries = self.results.count()
        return True

class DistrosAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add_action(self):
        title = self.request.get("title", "")
        description = self.request.get("description", "")
        domain = self.request.get("domain", "")
        person = IPerson(self.request.principal, None)

        
        if not person:
            return False
        
        if not title:
            return False

        dt = getUtility(IDistroTools)
        res = dt.createDistro(person.id, title, description, domain)
        self.results = res
        return res

class DistrosEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def edit_action(self):
        name = self.request.get("name", "")
        title = self.request.get("title", "")
        domainname = self.request.get("domainname", "")
        description = self.request.get("description", "")

        if not (name or title or description):
            return False

        ##XXX: (uniques) cprov 20041003
        ## again :)
        self.context.distribution.name = name
        self.context.distribution.title = title
        self.context.distribution.domainname = domainname
        self.context.distribution.description = description
        return True

#
# Releases
#

class DistroReleaseView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def bugSourcePackagesBatchNavigator(self):
        packages = list(self.context.bugSourcePackages())
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))

        batch = Batch(list=packages, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)

class ReleasesAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def add_action(self):
        person = IPerson(self.request.principal, None)        
        if not person:
            return False

        title = self.request.get("title", "")
        shortdesc = self.request.get("shortdesc", "")
        description = self.request.get("description", "")
        version = self.request.get("version", "")
        parent = self.request.get("parentrelease", "")

        if not (title and version and parent):
            return False

        distro_id = self.context.distribution.id

        dt = getUtility(IDistroTools)
        res = dt.createDistroRelease(person.id, title, distro_id,
                                     shortdesc, description, version,
                                     parent)
        self.results = res
        return res

    def getReleases(self):
        d_util = getUtility(IDistroTools)
        return d_util.getDistroReleases()

class ReleaseEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def edit_action(self):

        name = self.request.get("name", "")        
        title = self.request.get("title", "")
        shortdesc = self.request.get("shortdesc", "")
        description = self.request.get("description", "")
        version = self.request.get("version", "")

        if not (name or title or description or version):
            return False
        
        ##XXX: (uniques) cprov 20041003
        self.context.release.name = name
        self.context.release.title = title
        self.context.release.shortdesc = shortdesc
        self.context.release.description = description
        self.context.release.version = version
        return True

class ReleaseSearchView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.sources = []
        self.binaries = []

    def search_action(self):
        name = self.request.get("name", "")
        context = self.context

        if not name:
            return False

        self.sources = list(context.findSourcesByName(name))
        self.binaries = list(context.findBinariesByName(name))
        return True

#
# Roles
#

class AddRoleViewBase(object):
    rolesPortlet = None
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def is_owner(self):
        person = IPerson(self.request.principal, None)
        if not person:
            return False

        # XXX: cprov 20041202
        # verify also the DistributionRoles for persons 
        # with Admin Role
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
        return self.create_role_user(container.id, person, role)

    def get_people(self):
        return getUtility(IPersonSet).getAll()

    def get_role_users(self):
        return self.get_container().role_users

    def create_role_user(self):
        raise NotImplementedError

    def get_roles(self):
        raise NotImplementedError

    def get_container(self):
        raise NotImplementedError

class AddDistroRoleView(AddRoleViewBase):
    rolesPortlet = ViewPageTemplateFile(
        '../templates/portlet-distroroles.pt')

    def get_container(self):
        return self.context.distribution

    def create_role_user(self, container_id, person, role):
        d_util = getUtility(IDistroTools)        
        return d_util.createDistributionRole(container_id,
                                             person,
                                             role)

    def get_roles(self):
        return dbschema.DistributionRole.items

class AddDistroReleaseRoleView(AddRoleViewBase):
    rolesPortlet = ViewPageTemplateFile(
        '../templates/portlet-distroroles.pt')

    def get_container(self):
        return self.context.release
    
    def create_role_user(self, container_id, person, role):
        d_util = getUtility(IDistroTools)                
        return d_util.createDistroReleaseRole(container_id,
                                              person,
                                              role)
    
    def get_roles(self):
        return dbschema.DistroReleaseRole.items

