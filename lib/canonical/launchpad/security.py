# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface

from canonical.launchpad.interfaces import IAuthorization, IHasOwner, IPerson
from canonical.launchpad.interfaces import ISourceSource, ISourceSourceAdmin

class AdminByAdminsTeam:
    implements(IAuthorization)
    permission = 'launchpad.Admin'
    usedfor = Interface

    def __init__(self, obj):
        self.obj = obj

    def checkPermission(self, person):
        if person is None:
            return False
        else:
            return person.inTeam('admins')


class EditByOwnersOrAdmins:
    implements(IAuthorization)
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def __init__(self, obj):
        self.obj = obj

    def checkPermission(self, person):
        if person is None:
            return False
        elif person.id == self.obj.owner.id:
            return True
        elif person.inTeam('admins'):
            return True
        else:
            return False


class AdminSourceSourceByButtSource:
    implements(IAuthorization)
    permission = 'launchpad.Admin'
    usedfor = ISourceSourceAdmin

    def __init__(self, obj):
        self.obj = obj

    def checkPermission(self, person):
        if person is None:
            return False
        else:
            return person.inTeam('buttsource')


class EditSourceSourceByButtSource:
    implements(IAuthorization)
    permission = 'launchpad.Edit'
    usedfor = ISourceSource

    def __init__(self, obj):
        self.obj = obj

    def checkPermission(self, person):
        if person is None:
            return False
        if person.inTeam('buttsource'):
            return True
        elif not self.obj.syncCertified():
            return True
        else:
            return False

