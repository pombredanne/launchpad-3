# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IAuthorization, IHasOwner, IPerson, ITeam, ITeamMembershipSubset,
    IDistribution, ITeamMembership, IProductSeriesSource,
    IProductSeriesSourceAdmin, IMilestone, IBug, IBugTask, ITranslator,
    IProduct, IProductSeries, IPOTemplate, IPOFile, IPOTemplateName,
    IPOTemplateNameSet, ISourcePackage, ILaunchpadCelebrities, IDistroRelease,
    IBugTracker, IBugAttachment, IPoll, IPollSubset, IPollOption,
    IProductRelease, IShippingRequest, IShippingRequestSet, IRequestedCDs,
    IStandardShipItRequestSet, IStandardShipItRequest, IShipItApplication,
    IShippingRun)

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


class AdminSeriesSourceByButtSource(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IProductSeriesSourceAdmin

    def checkAuthenticated(self, user):
        buttsource = getUtility(ILaunchpadCelebrities).buttsource
        return user.inTeam(buttsource)


class EditRequestedCDsByRecipientOrShipItAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IRequestedCDs

    def checkAuthenticated(self, user):
        shipitadmins = getUtility(ILaunchpadCelebrities).shipit_admin
        return user == self.obj.request.recipient or user.inTeam(shipitadmins)


class EditShippingRequestByRecipientOrShipItAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IShippingRequest

    def checkAuthenticated(self, user):
        shipitadmins = getUtility(ILaunchpadCelebrities).shipit_admin
        return user == self.obj.recipient or user.inTeam(shipitadmins)


class AdminShippingRequestByShipItAdmins(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IShippingRequest

    def checkAuthenticated(self, user):
        shipitadmins = getUtility(ILaunchpadCelebrities).shipit_admin
        return user.inTeam(shipitadmins)


class AdminShippingRunByShipItAdmins(AdminShippingRequestByShipItAdmins):
    usedfor = IShippingRun


class AdminStandardShipItOrderSetByShipItAdmins(
        AdminShippingRequestByShipItAdmins):
    usedfor = IStandardShipItRequestSet


class AdminStandardShipItOrderByShipItAdmins(
        AdminShippingRequestByShipItAdmins):
    usedfor = IStandardShipItRequest


class AdminShipItApplicationByShipItAdmins(
        AdminShippingRequestByShipItAdmins):
    usedfor = IShipItApplication


class AdminShippingRequestSetByShipItAdmins(AdminShippingRequestByShipItAdmins):
    permission = 'launchpad.Admin'
    usedfor = IShippingRequestSet


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


class EditMilestoneByTargetOwnerOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Authorize the product or distribution owner."""
        admins = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(admins):
            return True
        return user.inTeam(self.obj.target.owner)


class AdminTeamByTeamOwnerOrLaunchpadAdmins(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """Only the team owner and Launchpad admins have launchpad.Admin on a
        team.
        """
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(self.obj.teamowner) or user.inTeam(admins)


class EditTeamByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """The team owner and all team admins have launchpad.Edit on that team.

        The Launchpad admins also have launchpad.Edit on all teams.
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


class EditPersonBySelf(AuthorizationBase):
    permission = 'launchpad.Special'
    usedfor = IPerson

    def checkAuthenticated(self, user):
        """A user can edit the Person who is herself."""
        return self.obj.id == user.id


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


class AdminDistribution(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroreleases to the Launchpad admin team."""
    permission = 'launchpad.Admin'
    usedfor = IDistribution


class EditDistribution(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroreleases to the Launchpad admin team."""
    permission = 'launchpad.Edit'
    usedfor = IDistribution


class AdminDistroRelease(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroreleases to the Launchpad admin team."""
    permission = 'launchpad.Admin'
    usedfor = IDistroRelease


class EditDistroRelease(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroreleases to the Launchpad admin team."""
    permission = 'launchpad.Edit'
    usedfor = IDistroRelease


# Mark Shuttleworth - I've commented out the below configuration, because
# of the risk of a distrorelease edit causing huge movements of files in the
# archive and publisher and librarian. Please discuss with me before
# changing it.
#
#class EditDistroReleaseByOwnersOrDistroOwnersOrAdmins(AuthorizationBase):
#    permission = 'launchpad.Edit'
#    usedfor = IDistroRelease
#
#    def checkAuthenticated(self, user):
#        admins = getUtility(ILaunchpadCelebrities).admin
#        return (user.inTeam(self.obj.owner) or
#                user.inTeam(self.obj.distribution.owner) or
#                user.inTeam(admins))


class EditBugTask(AuthorizationBase):
    """Permission checker for IBugTask editing.

    Allow any logged-in user to edit public bugtasks. Allow only
    explicit subscribers to edit private bugtasks.
    """
    permission = 'launchpad.Edit'
    usedfor = IBugTask

    def checkAuthenticated(self, user):
        """Check whether the user has permissions to edit this IBugTask."""
        admins = getUtility(ILaunchpadCelebrities).admin

        if user.inTeam(admins):
            # Admins can always edit bugtasks, whether they're reported on a
            # private bug or not.
            return True

        if not self.obj.bug.private:
            # This is a public bug, so anyone can edit it.
            return True
        else:
            # This is a private bug, and we know the user isn't an admin, so
            # we'll only allow editing if the user is explicitly subscribed to
            # this bug.
            for subscription in self.obj.bug.subscriptions:
                if user.inTeam(subscription.person):
                    return True

            return False


class PublicToAllOrPrivateToExplicitSubscribersForBugTask(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBugTask

    def checkAuthenticated(self, user):
        """Check whether the user has permissions to view this IBugTask."""
        admins = getUtility(ILaunchpadCelebrities).admin

        if user.inTeam(admins):
            # Admins can always edit bugtasks, whether they're reported on a
            # private bug or not.
            return True

        if not self.obj.bug.private:
            # This is a public bug.
            return True
        else:
            # This is a private bug
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
        admins = getUtility(ILaunchpadCelebrities).admin
        if not self.obj.private:
            # This is a public bug.
            return True
        elif user.inTeam(admins):
            # Admins can edit all bugs.
            return True
        else:
            # This is a private bug. Only explicit subscribers may edit it.
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
        admins = getUtility(ILaunchpadCelebrities).admin
        if not self.obj.private:
            # This is a public bug.
            return True
        elif user.inTeam(admins):
            # Admins can view all bugs.
            return True
        else:
            # This is a private bug. Only explicit subscribers may view it.
            for subscription in self.obj.subscriptions:
                if user.inTeam(subscription.person):
                    return True

        return False

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.private


class ViewBugAttachment(PublicToAllOrPrivateToExplicitSubscribersForBug):
    """Security adapter for viewing a bug attachment.

    If the user is authorized to view the bug, he's allowed to view the
    attachment.
    """
    permission = 'launchpad.View'
    usedfor = IBugAttachment

    def __init__(self, bugattachment):
        self.obj = bugattachment.bug


class EditBugAttachment(
    EditPublicByLoggedInUserAndPrivateByExplicitSubscribers):
    """Security adapter for editing a bug attachment.

    If the user is authorized to view the bug, he's allowed to edit the
    attachment.
    """
    permission = 'launchpad.Edit'
    usedfor = IBugAttachment

    def __init__(self, bugattachment):
        self.obj = bugattachment.bug


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


class AdminPOTemplateDetails(OnlyRosettaExpertsAndAdmins):
    """Permissions to edit all aspects of an IPOTemplate."""
    permission = 'launchpad.Admin'
    usedfor = IPOTemplate


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

class EditProductRelease(EditByOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IProductRelease

