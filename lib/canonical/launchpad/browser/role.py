# lp imports
from canonical.lp import dbschema                       

# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility

# interface import
from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import IDistroTools

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

