# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface

from canonical.launchpad.interfaces import IAuthorization, IHasOwner, IPerson
from canonical.launchpad.interfaces import ISourceSource, ISourceSourceAdmin

class AuthorizationBase:
    implements(IAuthorization)

    def __init__(self, obj):
        self.obj = obj

    def checkUnauthenticated(self):
        return False

    def checkPermission(self, person):
        raise NotImplementedError


class AdminByAdminsTeam(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = Interface

    def checkPermission(self, person):
        return person.inTeam('admins')


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkPermission(self, person):
        if person.id == self.obj.owner.id:
            return True
        elif person.inTeam('admins'):
            return True
        else:
            return False


class AdminSourceSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ISourceSourceAdmin

    def checkPermission(self, person):
        return person.inTeam('buttsource')


class EditSourceSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ISourceSource

    def checkPermission(self, person):
        if person.inTeam('buttsource'):
            return True
        elif not self.obj.syncCertified():
            return True
        else:
            return False

