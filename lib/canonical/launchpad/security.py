# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface

from canonical.launchpad.interfaces import IAuthorization, IHasOwner
from canonical.launchpad.interfaces import ISourceSource

class AdminByAdminsTeam:
    implements(IAuthorization)
    permission = 'launchpad.Admin'
    usedfor = Interface

    def __init__(self, obj):
        self.obj = obj

    def checkPermission(self, user):
        if IPerson(user).inTeam('admins'):
            return True
        else:
            return False


class EditByOwners:
    implements(IAuthorization)
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def __init__(self, obj):
        self.obj = obj

    def checkPermission(self, user):
        if user.id == self.obj.owner.id:
            return True
        else:
            return False


class AdminSourceSourceByButtSource:
    implements(IAuthorization)
    permission = 'launchpad.Admin'
    usedfor = ISourceSource

    def __init__(self, obj):
        self.obj = obj

    def checkPermission(self, user):
        if IPerson(user).inTeam('buttsource'):
            return True
        else:
            return False

