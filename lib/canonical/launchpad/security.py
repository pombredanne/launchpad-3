# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface
from zope.component import getUtility

from canonical.launchpad.interfaces import IAuthorization, IHasOwner
from canonical.launchpad.interfaces import IPerson, ITeam, IPersonSet
from canonical.launchpad.interfaces import ITeamMembershipSubset
from canonical.launchpad.interfaces import ITeamMembership
from canonical.launchpad.interfaces import ISourceSource, ISourceSourceAdmin
from canonical.launchpad.interfaces import IMilestone, IBug, IBugTask
from canonical.launchpad.interfaces import IUpstreamBugTask, IDistroBugTask
from canonical.launchpad.interfaces import IHasProduct, IHasProductAndAssignee
from canonical.launchpad.interfaces import IReadOnlyUpstreamBugTask
from canonical.launchpad.interfaces import IEditableUpstreamBugTask, IProduct
from canonical.launchpad.interfaces import ITeamParticipationSet
from canonical.launchpad.interfaces import IPOTemplate, IPOFile
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
        admins = getUtility(IPersonSet).getByName('admins')
        return user.inTeam(self.obj.owner) or user.inTeam(admins)


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


class EditMilestoneByProductMaintainer(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Authorize the product maintainer."""
        return user.inTeam(self.obj.product.owner)


class EditTeamByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """A user who is a team's owner has launchpad.Edit on that team.

        The admin team also has launchpad.Edit on all teams.
        """
        admins = getUtility(IPersonSet).getByName('admins')
        if user.inTeam(self.obj.teamowner) or user.inTeam(admins):
            return True
        else:
            for team in self.obj.teamowner.administrators:
                if user.inTeam(team):
                    return True

        return False


class EditTeamMembershipByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeamMembership

    def checkAuthenticated(self, user):
        admins = getUtility(IPersonSet).getByName('admins')
        if user.inTeam(self.obj.team.teamowner) or user.inTeam(admins):
            return True
        else:
            for team in self.obj.team.administrators:
                if user.inTeam(team):
                    return True

        return False


class EditTeamMembershipSubsetByTeamOwnerOrTeamAdminsOrAdmins(
        EditTeamMembershipByTeamOwnerOrTeamAdminsOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = ITeamMembershipSubset


class EditPersonBySelfOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPerson

    def checkAuthenticated(self, user):
        """A user can edit the Person who is herself.

        The admin team can also edit any Person.
        """
        admins = getUtility(IPersonSet).getByName('admins')
        return self.obj.id == user.id or user.inTeam(admins)


class EditUpstreamBugTask(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IUpstreamBugTask

    def checkAuthenticated(self, user):
        """Allow the maintainer and possible assignee to edit the task.

        If the maintainer or assignee is a team, everyone belonging to the team
        is allowed to edit the task.
        """
        if user.inTeam(self.obj.maintainer):
            return True
        elif self.obj.assignee is not None and user.inTeam(self.obj.assignee):
            return True
        else:
            return False


class EditDistroBugTask(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IDistroBugTask

    def checkAuthenticated(self, user):
        """Allow all authenticated users to edit the task."""
        if not self.obj.bug.private:
            # public bug
            return True
        else:
            # private bug
            for subscription in self.obj.bug.subscriptions:
                if user.inTeam(subscription.person):
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
                if user.inTeam(subscription.person):
                    return True

            return False

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.bug.private


class PublicToAllOrPrivateToExplicitSubscribersForROBugTask(
    PublicToAllOrPrivateToExplicitSubscribersForBugTask):
    usedfor = IReadOnlyUpstreamBugTask


class EditPublicByLoggedInUserAndPrivateByExplicitSubscribers(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBug

    def checkAuthenticated(self, user):
        """Allow any logged in user to edit a public bug, and only
        explicit subscribers to edit private bugs.
        """
        if not self.obj.private:
            # public bug
            return True
        else:
            # private bug
            for subscription in self.obj.subscriptions:
                if user.inTeam(subscription.person):
                    return True

        return False

    def checkUnauthenticated(self):
        """Never allow unauthenticated users to edit a bug."""
        return False


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
            for subscription in self.obj.subscriptions:
                if user.inTeam(subscription.person):
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

class EditPOTemplateDetails(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        """Allow the owner of the POTemplate if it's not in a product release.
        """
        if self.obj.productrelease is not None:
            # It's a PO file from a product, it has no restrictions.
            return True
        elif ITeam.providedBy(self.obj.owner):
            # The PO file is owned by a team.
            if user.inTeam(self.obj.owner):
                # The user is member of that team.
                return True
            else:
                return False
        elif self.obj.owner.id == user.id:
            # The user is directly the owner of the PO file.
            return True
        else:
            return False


class EditPOFileDetails(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPOFile

    def checkAuthenticated(self, user):
        """Allow the owner of the POFile if it's not in a product release.
        """
        if self.obj.potemplate.productrelease is not None:
            # It's a PO file from a product, it has no restrictions.
            return True
        elif ITeam.providedBy(self.obj.owner):
            # The PO file is owned by a team.
            if user.inTeam(self.obj.owner):
                # The user is member of that team.
                return True
            else:
                return False
        elif self.obj.owner.id == user.id:
            # The user is directly the owner of the PO file.
            return True
        else:
            return False

