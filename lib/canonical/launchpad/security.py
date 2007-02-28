# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IHasOwner, IPerson, ITeam, ISprint, ISprintSpecification,
    IDistribution, ITeamMembership, IMilestone, IBug, ITranslator,
    IProduct, IProductSeries, IPOTemplate, IPOFile, IPOTemplateName,
    IPOTemplateNameSet, ISourcePackage, ILaunchpadCelebrities, IDistroRelease,
    IBugTracker, IBugAttachment, IPoll, IPollSubset, IPollOption,
    IProductRelease, IShippingRequest, IShippingRequestSet, IRequestedCDs,
    IStandardShipItRequestSet, IStandardShipItRequest, IShipItApplication,
    IShippingRun, ISpecification, IQuestion, ITranslationImportQueueEntry,
    ITranslationImportQueue, IDistributionMirror, IHasBug,
    IBazaarApplication, IDistroReleaseQueue, IBuilderSet, IPackageUploadQueue,
    IBuilder, IBuild, IBugNomination, ISpecificationSubscription, IHasDrivers,
    IBugBranch)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import IAuthorization

from canonical.lp.dbschema import DistroReleaseQueueStatus

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


class EditBugNominationStatus(AuthorizationBase):
    permission = 'launchpad.Driver'
    usedfor = IBugNomination

    def checkAuthenticated(self, user):
        return check_permission("launchpad.Driver", self.obj.target)


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(self.obj.owner) or user.inTeam(admins)


class AdminDistributionMirrorByDistroOwnerOrMirrorAdminsOrAdmins(
        AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IDistributionMirror

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.distribution.owner) or
                user.inTeam(admins) or
                user.inTeam(self.obj.distribution.mirror_admin))


class EditDistributionMirrorByOwnerOrDistroOwnerOrMirrorAdminsOrAdmins(
        AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IDistributionMirror

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or user.inTeam(admins) or
                user.inTeam(self.obj.distribution.owner) or
                user.inTeam(self.obj.distribution.mirror_admin))


class EditSpecificationByTargetOwnerOrOwnersOrAdmins(AuthorizationBase):
    """We want everybody "related" to a specification to be able to edit it.
    You are related if you have a role on the spec, or if you have a role on
    the spec target (distro/product) or goal (distrorelease/productseries).
    """

    permission = 'launchpad.Edit'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        assert self.obj.target
        admins = getUtility(ILaunchpadCelebrities).admin
        goaldrivers = []
        goalowner = None
        if self.obj.goal is not None:
            goalowner = self.obj.goal.owner
            goaldrivers = self.obj.goal.drivers
        for driver in goaldrivers:
            if user.inTeam(driver):
                return True
        return (user.inTeam(self.obj.target.owner) or
                user.inTeam(goalowner) or
                user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.drafter) or
                user.inTeam(self.obj.assignee) or
                user.inTeam(self.obj.approver) or
                user.inTeam(admins))


class AdminSpecification(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        assert self.obj.target
        targetowner = self.obj.target.owner
        targetdrivers = self.obj.target.drivers
        for driver in targetdrivers:
            if user.inTeam(driver):
                return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.target.owner) or
                user.inTeam(admins))


class DriverSpecification(AuthorizationBase):
    permission = 'launchpad.Driver'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        # If no goal is proposed for the spec then there can be no
        # drivers for it - we use launchpad.Driver on a spec to decide
        # if the person can see the page which lets you decide whether
        # to accept the goal, and if there is no goal then this is
        # extremely difficult to do :-)
        return (
            self.obj.goal and
            check_permission("launchpad.Driver", self.obj.goal))


class EditSprintSpecification(AuthorizationBase):
    """The sprint owner or driver can say what makes it onto the agenda for
    the sprint.
    """
    permission = 'launchpad.Driver'
    usedfor = ISprintSpecification

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.sprint.owner) or
                user.inTeam(self.obj.sprint.driver) or
                user.inTeam(admins))


class DriveSprint(AuthorizationBase):
    """The sprint owner or driver can say what makes it onto the agenda for
    the sprint.
    """
    permission = 'launchpad.Driver'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.driver) or
                user.inTeam(admins))


class EditSpecificationSubscription(AuthorizationBase):
    """The subscriber, and people related to the spec or the target of the
    spec can determine who is essential."""
    permission = 'launchpad.Edit'
    usedfor = ISpecificationSubscription

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        if self.obj.specification.goal is not None:
            for driver in self.obj.specification.goal.drivers:
                if user.inTeam(driver):
                    return True
        else:
            for driver in self.obj.specification.target.drivers:
                if user.inTeam(driver):
                    return True
        return (user.inTeam(self.obj.person) or
                user.inTeam(self.obj.specification.owner) or
                user.inTeam(self.obj.specification.assignee) or
                user.inTeam(self.obj.specification.drafter) or
                user.inTeam(self.obj.specification.approver) or
                user.inTeam(admins))

class AdminSeriesByVCSImports(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        return user.inTeam(vcs_imports)


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


class EditSeriesSourceByVCSImports(AuthorizationBase):
    permission = 'launchpad.EditSource'
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        if user.inTeam(vcs_imports):
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


class AdminMilestoneByLaunchpadAdmins(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Only the Launchpad admins need this, we are only going to use it
        for connecting up series and distroreleases where we did not have
        them."""
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


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


class EditDistributionByDistroOwnersOrAdmins(AuthorizationBase):
    """The owner of a distribution should be able to edit its
    information; it is mainly administrative data, such as bug
    contacts. Note that creation of new distributions and distribution
    releases is still protected with launchpad.Admin"""
    permission = 'launchpad.Edit'
    usedfor = IDistribution

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(admins))


class AdminDistroRelease(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroreleases to the Launchpad admin team.

    NB: Please consult with SABDFL before modifying this permission because
        changing it could cause the archive to get rearranged, with tons of
        files moved to the new namespace, and mirrors would get very very
        upset. Then James T would be on your case.
    """
    permission = 'launchpad.Admin'
    usedfor = IDistroRelease


class EditDistroReleaseByOwnersOrDistroOwnersOrAdmins(AuthorizationBase):
    """The owner of the distro release should be able to modify some of the
    fields on the IDistroRelease

    NB: there is potential for a great mess if this is not done correctly so
    please consult with SABDFL before modifying these permissions.
    """
    permission = 'launchpad.Edit'
    usedfor = IDistroRelease

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.distribution.owner) or
                user.inTeam(admins))


class ReleaseAndSeriesDrivers(AuthorizationBase):
    """Drivers can approve or decline features and target bugs.

    Drivers exist for distribution releases and product series.
    """
    permission = 'launchpad.Driver'
    usedfor = IHasDrivers

    def checkAuthenticated(self, user):
        for driver in self.obj.drivers:
            if user.inTeam(driver):
                return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class EditProductSeries(EditByOwnersOrAdmins):
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        """Allow product owner, Rosetta Experts, or admins."""
        if user.inTeam(self.obj.product.owner):
            # The user is the owner of the product.
            return True
        # Rosetta experts need to be able to upload translations.
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert
        if user.inTeam(rosetta_experts):
            return True
        return EditByOwnersOrAdmins.checkAuthenticated(self, user)


class EditBugTask(AuthorizationBase):
    """Permission checker for editing objects linked to a bug.

    Allow any logged-in user to edit objects linked to public
    bugs. Allow only explicit subscribers to edit objects linked to
    private bugs.
    """
    permission = 'launchpad.Edit'
    usedfor = IHasBug

    def checkAuthenticated(self, user):
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
    usedfor = IHasBug

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin

        if user.inTeam(admins):
            # Admins can always edit bugs, whether they're public or
            # private.
            return True

        if not self.obj.bug.private:
            # This is a public bug.
            return True
        else:
            # This is a private bug.
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


class EditBugBranch(EditPublicByLoggedInUserAndPrivateByExplicitSubscribers):
    permission = 'launchpad.Edit'
    usedfor = IBugBranch

    def __init__(self, bug_branch):
        # The same permissions as for the BugBranch's bug should apply
        # to the BugBranch itself.
        self.obj = bug_branch.bug


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


class OnlyBazaarExpertsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and Bazaar
    experts."""

    def checkAuthenticated(self, user):
        bzrexpert = getUtility(ILaunchpadCelebrities).bazaar_expert
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins) or user.inTeam(bzrexpert)


class OnlyVcsImportsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and VCS Imports
    experts."""

    def checkAuthenticated(self, user):
        vcsexpert = getUtility(ILaunchpadCelebrities).vcs_imports
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins) or user.inTeam(vcsexpert)


class AdminTheBazaar(OnlyVcsImportsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = IBazaarApplication


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

class EditTranslationImportQueueEntry(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = ITranslationImportQueueEntry

    def checkAuthenticated(self, user):
        """Allow who added the entry, experts and admis.
        """
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert

        return (OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
                user.inTeam(self.obj.importer))

class AdminTranslationImportQueueEntry(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslationImportQueueEntry

class AdminTranslationImportQueue(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslationImportQueue

class EditPackageUploadQueue(AdminByAdminsTeam):
    permission = 'launchpad.Edit'
    usedfor = IPackageUploadQueue

    def checkAuthenticated(self, user):
        """Check user presence in admins or distrorelease upload admin team."""
        if AdminByAdminsTeam.checkAuthenticated(self, user):
            return True

        return user.inTeam(self.obj.distrorelease.distribution.upload_admin)


class ViewPackageUploadQueue(EditPackageUploadQueue):
    permission = 'launchpad.View'
    usedfor = IPackageUploadQueue

    def checkAuthenticated(self, user):
        """Allow only members of the admin team to view unapproved entries.

        Any logged in user can view entries in other state.
        """
        if EditPackageUploadQueue.checkAuthenticated(self, user):
            return True
        # deny access to non-admin on unapproved records
        if self.obj.status == DistroReleaseQueueStatus.UNAPPROVED:
            return False

        return True


class EditDistroReleaseQueue(EditPackageUploadQueue):
    permission = 'launchpad.Edit'
    usedfor = IDistroReleaseQueue


class ViewDistroReleaseQueue(ViewPackageUploadQueue):
    permission = 'launchpad.View'
    usedfor = IDistroReleaseQueue


class AdminByBuilddAdmin(AuthorizationBase):
    permission = 'launchpad.Admin'

    def checkAuthenticated(self, user):
        """Allow only admins and members of buildd_admin team"""
        lp_admin = getUtility(ILaunchpadCelebrities).admin
        buildd_admin = getUtility(ILaunchpadCelebrities).buildd_admin
        return (user.inTeam(buildd_admin) or
                user.inTeam(lp_admin))


class AdminBuilderSet(AdminByBuilddAdmin):
    usedfor = IBuilderSet


class AdminBuilder(AdminByBuilddAdmin):
    usedfor = IBuilder


# XXX cprov 20060731: As soon as we have external builders, as presumed
# in the original plan, we should grant some rights to the owners and
# that's what Edit is for.
class EditBuilder(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuilder


class AdminBuildRecord(AdminByBuilddAdmin):
    usedfor = IBuild


class AdminQuestion(AdminByAdminsTeam):
    permission = 'launchpad.Admin'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow only admins and owners of the question pillar target."""
        context = self.obj.product or self.obj.distribution
        return (AdminByAdminsTeam.checkAuthenticated(self, user) or
                user.inTeam(context.owner))


class ModerateQuestion(AdminQuestion):
    permission = 'launchpad.Moderate'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow user who can administer the question and answer contacts."""
        if AdminQuestion.checkAuthenticated(self, user):
            return True
        for answer_contact in self.obj.target.answer_contacts:
            if user.inTeam(answer_contact):
                return True
        return False


class QuestionOwner(AuthorizationBase):
    permission = 'launchpad.Owner'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow the question's owner."""
        return user.inTeam(self.obj.owner)
