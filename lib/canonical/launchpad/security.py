# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface
from zope.component import getUtility

from canonical.lp.dbschema import BugSubscription
from canonical.launchpad.interfaces import IAuthorization, IHasOwner, \
    IPerson, ISourceSource, ISourceSourceAdmin, IMilestone, IHasProduct, \
    IHasProductAndAssignee, IBug, IBugTask, IPersonSet

class AuthorizationBase:
    implements(IAuthorization)

    def __init__(self, obj):
        self.obj = obj

    def checkUnauthenticated(self):
        """Must return True or False. See IAuthorization.checkUnauthenticated."""
        return False

    def checkPermission(self, person):
        """Must return True or False. See IAuthorization.checkPermission."""
        raise NotImplementedError


class AdminByAdminsTeam(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = Interface

    def checkPermission(self, person):
        admins = getUtility(IPersonSet).getByName('admins')
        return person.inTeam(admins)


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkPermission(self, person):
        admins = getUtility(IPersonSet).getByName('admins')
        if person.id == self.obj.owner.id:
            return True
        elif person.inTeam(admins):
            return True
        else:
            return False


class EditByOwner(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkPermission(self, person):
        """Authorize the object owner."""
        if person.id == self.obj.owner.id:
            return True


class AdminSourceSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ISourceSourceAdmin

    def checkPermission(self, person):
        buttsource = getUtility(IPersonSet).getByName('buttsource')
        return person.inTeam(buttsource)


class EditSourceSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ISourceSource

    def checkPermission(self, person):
        buttsource = getUtility(IPersonSet).getByName('buttsource')
        if person.inTeam(buttsource):
            return True
        elif not self.obj.syncCertified():
            return True
        else:
            return False


class EditByProductOwner(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasProduct

    def checkPermission(self, person):
        """Authorize the product maintainer."""
        return self.obj.product.owner.id == person.id


class EditByProductOwnerOrAssignee(EditByProductOwner):
    permission = 'launchpad.Edit'
    usedfor = IHasProductAndAssignee

    def checkPermission(self, person):
        return (
            super(EditByProductOwnerOrAssignee, self).checkPermission(person) or
            self.obj.assignee.id == person.id)


class TaskPublicToAllOrPrivateToExplicitSubscribers(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBugTask

    def checkPermission(self, person):
        """Allow any user to see non-private bugs, but only explicit
        subscribers to see private bugs.
        """
        if not self.obj.bug.private:
            # public bug
            return True
        else:
            # private bug
            watch_or_cc = (
                BugSubscription.WATCH.value, BugSubscription.CC.value)
            for subscription in self.obj.bug.subscriptions:
                if (subscription.person.id == person.id and 
                    subscription.subscription in watch_or_cc):
                    return True

        return False

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.bug.private


class BugPublicToAllOrPrivateToExplicitSubscribers(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBug

    def checkPermission(self, person):
        """Allow any user to see non-private bugs, but only explicit
        subscribers to see private bugs.
        """
        if not self.obj.private:
            # public bug
            return True
        else:
            # private bug
            watch_or_cc = (
                BugSubscription.WATCH.value, BugSubscription.CC.value)
            for subscription in self.obj.subscriptions:
                if (subscription.person.id == person.id and 
                    subscription.subscription in watch_or_cc):
                    return True

        return False

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.private


class UseApiDoc(AuthorizationBase):
    permission = 'zope.app.apidoc.UseAPIDoc'
    usedfor = Interface

    def checkPermission(self, person):
        return True



