# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IAuthorization, IHasOwner, IPerson, ITeam, ITeamMembershipSubset,
    ITeamMembership, IProductSeriesSource, IProductSeriesSourceAdmin,
    IMilestone, IBug, IBugTask, IUpstreamBugTask, IDistroBugTask,
    IDistroReleaseBugTask, ITranslator, IProduct, IProductSeries,
    IPOTemplate, IPOFile, IPOTemplateName, IPOTemplateNameSet, ISourcePackage,
    ILaunchpadCelebrities, IDistroRelease, IBugTracker, IPoll, IPollSubset,
    IPollOption, IPollOptionSubset)

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
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(self.obj.owner) or user.inTeam(admins)


class EditDistroReleaseByOwnersOrDistroOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IDistroRelease

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.distribution.owner) or
                user.inTeam(admins))


class AdminSeriesSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IProductSeriesSourceAdmin

    def checkAuthenticated(self, user):
        buttsource = getUtility(ILaunchpadCelebrities).buttsource
        return user.inTeam(buttsource)


class EditSeriesSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IProductSeriesSource

    def checkAuthenticated(self, user):
        buttsource = getUtility(ILaunchpadCelebrities).buttsource
        if user.inTeam(buttsource):
            return True
        elif not self.obj.syncCertified():
            return True
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
        admins = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(self.obj.teamowner) or user.inTeam(admins):
            return True
        else:
            for team in self.obj.administrators:
                if user.inTeam(team):
                    return True

        return False


class EditTeamMembershipByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeamMembership

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
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
        admins = getUtility(ILaunchpadCelebrities).admin
        return self.obj.id == user.id or user.inTeam(admins)


class EditPollByTeamOwnerOrTeamAdminsOrAdmins(
        EditTeamMembershipByTeamOwnerOrTeamAdminsOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IPoll


class EditPollSubsetByTeamOwnerOrTeamAdminsOrAdmins(
        EditPollByTeamOwnerOrTeamAdminsOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IPollSubset


class EditPollOptionByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPollOption

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(self.obj.poll.team.teamowner) or user.inTeam(admins):
            return True
        else:
            for team in self.obj.poll.team.administrators:
                if user.inTeam(team):
                    return True

        return False


class EditPollOptionSubsetByTeamOwnerOrTeamAdminsOrAdmins(
        EditPollOptionByTeamOwnerOrTeamAdminsOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IPollOptionSubset



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


class EditDistroReleaseBugTask(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IDistroReleaseBugTask

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


class EditPublicByLoggedInUserAndPrivateByExplicitSubscribers(
    AuthorizationBase):
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


class OnlyRosettaExpertsAndAdmins(AuthorizationBase):
    """Base class that allow access to Rosetta experts and Launchpad admins.
    """

    def checkAuthenticated(self, user):
        """Allow Launchpad's admins and Rosetta experts edit all fields."""
        admins = getUtility(ILaunchpadCelebrities).admin
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert
        return user.inTeam(admins) or user.inTeam(rosetta_experts)


class EditPOTemplateDetails(EditByOwnersOrAdmins):
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        """Allow product/sourcepackage/potemplate owner, experts and admis.
        """
        if (self.obj.productseries is not None and
            user.inTeam(self.obj.productseries.product.owner)):
            # The user is the owner of the product.
            return True

        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert

        return (EditByOwnersOrAdmins.checkAuthenticated(self, user) or
                user.inTeam(rosetta_experts))


# XXX: Carlos Perello Marin 2005-05-24: This should be using
# SuperSpecialPermissions when implemented.
# See: https://launchpad.ubuntu.com/malone/bugs/753/
class AddPOTemplate(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Append'
    usedfor = IProductSeries


class EditPOFileDetails(EditByOwnersOrAdmins):
    usedfor = IPOFile

    def checkAuthenticated(self, user):
        """Allow anyone that can edit translations, owner, experts and admis.
        """
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert

        return (EditByOwnersOrAdmins.checkAuthenticated(self, user) or
                self.obj.canEditTranslations(user) or
                user.inTeam(rosetta_experts))


class ChangeTranslatorInGroup(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = ITranslator

    def checkAuthenticated(self, user):
        """Allow the owner of a translation group to edit the translator
        of any language in the group."""
        return (user.inTeam(self.obj.translationgroup.owner) or
                OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user))


# XXX: Carlos Perello Marin 2005-05-24: This should be using
# SuperSpecialPermissions when implemented.
# See: https://launchpad.ubuntu.com/malone/bugs/753/
class ListProductPOTemplateNames(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = IProduct

# XXX: Carlos Perello Marin 2005-05-24: This should be using
# SuperSpecialPermissions when implemented.
# See: https://launchpad.ubuntu.com/malone/bugs/753/
class ListSourcePackagePOTemplateNames(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ISourcePackage

class EditPOTemplateName(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = IPOTemplateName


class EditPOTemplateNameSet(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = IPOTemplateNameSet


class EditBugTracker(EditByOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IBugTracker

