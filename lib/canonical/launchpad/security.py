# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface
from zope.component import getUtility

from canonical.launchpad.interfaces import IAuthorization, IHasOwner
from canonical.launchpad.interfaces import IPerson, ITeam, IPersonSet
from canonical.launchpad.interfaces import ISourceSource, ISourceSourceAdmin
from canonical.launchpad.interfaces import IMilestone, IBugTask, IBug
from canonical.launchpad.interfaces import IHasProduct, IHasProductAndAssignee
from canonical.launchpad.interfaces import IReadOnlyUpstreamBugTask
from canonical.launchpad.interfaces import IEditableUpstreamBugTask, IProduct
from canonical.launchpad.interfaces import ITeamParticipationSet
from canonical.lp.dbschema import BugSubscription


class AuthorizationBase:
    implements(IAuthorization)
    permission = None
    usedfor = None

    def __init__(self, obj):
        self.obj = obj

    def checkUnauthenticated(self):
        """Must return True or False.  See IAuthorization.checkUnauthenticated.
        """
        return False

    def checkAuthenticated(self, user):
        """Must return True or False.  See IAuthorization.checkAuthenticated.
        """
        return False


class AdminByAdminsTeam(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = Interface

    def checkAuthenticated(self, user):
        admins = getUtility(IPersonSet).getByName('admins')
        return user.inTeam(admins)


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkAuthenticated(self, user):
        if user.id == self.obj.owner.id:
            return True
        elif user.inTeam(getUtility(IPersonSet).getByName('admins')):
            return True
        else:
            return False


class EditByOwnerOfProduct(EditByOwnersOrAdmins):
    usedfor = IProduct


class AdminSourceSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ISourceSourceAdmin

    def checkAuthenticated(self, user):
        buttsource = getUtility(IPersonSet).getByName('buttsource')
        return user.inTeam(buttsource)


class EditSourceSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ISourceSource

    def checkAuthenticated(self, user):
        buttsource = getUtility(IPersonSet).getByName('buttsource')
        if user.inTeam(buttsource):
            return True
        elif not self.obj.syncCertified():
            return True
        else:
            return False


class EditByProductOwner(AuthorizationBase):
    permission = 'launchpad.Edit'
    #usedfor = IHasProduct
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Authorize the product maintainer."""
        return self.obj.product.owner.id == user.id


class EditByProductOwnerOrAssignee:
    permission = 'launchpad.Edit'
    usedfor = IEditableUpstreamBugTask

    def checkAuthenticated(self, user):
        return (self.obj.product.owner.id == user.id or
                self.obj.assignee.id == user.id)


class EditTeamByTeamOwnerOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """A user who is a team's owner has launchpad.Edit on that team.

        The admin team also has launchpad.Edit on all teams.
        """
        return self.obj.teamowner.id == user.id or self.user.inTeam('admins')


class EditPersonBySelfOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPerson

    def checkAuthenticated(self, user):
        """A user can edit the Person who is herself.

        The admin team can also edit any Person.
        """
        return self.obj.id == user.id or self.user.inTeam('admins')


class TaskEditableByMaintainerOrAssignee(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBugTask

    def checkAuthenticated(self, user):
        """Allow the maintainer and possible assignee to edit the task.

        If the maintainer or assignee is a team, everyone belonging to the team
        is allowed to edit the task.
        """
        if self.obj.product is None:
            # It's a distro (release) task, thus all authenticated users
            # may edit it
            return True

        # Otherwise, only a maintainer or assignee may edit it
        teampart = getUtility(ITeamParticipationSet)
        for allowed_person in (self.obj.maintainer, self.obj.assignee):
            if ITeam.providedBy(allowed_person):
                if user in teampart.getAllMembers(allowed_person):
                    return True
            elif IPerson.providedBy(allowed_person):
                if user is allowed_person:
                    return True
        return False


class PublicToAllOrPrivateToExplicitSubscribersForBugTask(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBugTask

    def checkAuthenticated(self, user):
        """Allow any user to see non-private bugs, but only explicit
        subscribers to see private bugs.
        """
        if not self.obj.bug.private:
            # public bug
            return True
        else:
            # private bug
            for subscription in self.obj.bug.subscriptions:
                if (subscription.person.id == user.id and
                   (subscription.subscription == BugSubscription.WATCH.value
                    or subscription.subscription == BugSubscription.CC.value)):
                    return True

            return False

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.bug.private


class PublicToAllOrPrivateToExplicitSubscribersForROBugTask(
    PublicToAllOrPrivateToExplicitSubscribersForBugTask):
    usedfor = IReadOnlyUpstreamBugTask


class PublicToAllOrPrivateToExplicitSubscribersForBug(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBug

    def checkAuthenticated(self, user):
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
                if (subscription.person.id == user.id and 
                    subscription.subscription in watch_or_cc):
                    return True

        return False

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.private


class UseApiDoc(AuthorizationBase):
    permission = 'zope.app.apidoc.UseAPIDoc'
    usedfor = Interface

    def checkAuthenticated(self, user):
        return True

