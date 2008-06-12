# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Security policies for using content objects.

"""
__metaclass__ = type

from zope.interface import implements, Interface
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ArchivePurpose, IAnnouncement, IArchive, IArchivePermissionSet,
    IBazaarApplication, IBranch, IBranchMergeProposal, IBranchSubscription,
    IBug, IBugAttachment, IBugBranch, IBugNomination, IBugTracker, IBuild,
    IBuilder, IBuilderSet, ICodeImport, ICodeImportJobSet,
    ICodeImportJobWorkflow, ICodeImportMachine,
    ICodeReviewComment, IDistribution, IDistributionMirror, IDistroSeries,
    IDistroSeriesLanguage, IEntitlement, IFAQ, IFAQTarget, IHWSubmission,
    IHasBug, IHasDrivers, IHasOwner, ILanguage, ILanguagePack, ILanguageSet,
    ILaunchpadCelebrities, IMailingListSet, IMilestone, IOAuthAccessToken,
    IPOFile, IPOTemplate, IPOTemplateSubset, IPackageUpload,
    IPackageUploadQueue, IPackaging, IPerson, IPillar, IPoll, IPollOption,
    IPollSubset, IProduct, IProductRelease, IProductReleaseFile,
    IProductSeries, IQuestion, IQuestionTarget, IRequestedCDs,
    IShipItApplication, IShippingRequest, IShippingRequestSet, IShippingRun,
    ISourcePackage, ISourcePackageRelease, ISpecification,
    ISpecificationBranch, ISpecificationSubscription, ISprint,
    ISprintSpecification, IStandardShipItRequest, IStandardShipItRequestSet,
    ITeam, ITeamMembership, ITranslationGroup, ITranslationGroupSet,
    ITranslationImportQueue, ITranslationImportQueueEntry, ITranslator,
    PersonVisibility)
from canonical.launchpad.interfaces.emailaddress import IEmailAddress

from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import IAuthorization


class AuthorizationBase:
    implements(IAuthorization)
    permission = None
    usedfor = None

    def __init__(self, obj):
        self.obj = obj

    def checkUnauthenticated(self):
        """See `IAuthorization.checkUnauthenticated`.

        :return: True or False.
        """
        return False

    def checkAuthenticated(self, user):
        """See `IAuthorization.checkAuthenticated`.

        :return: True or False.
        """
        return False


class ViewByLoggedInUser(AuthorizationBase):
    """The default ruleset for the launchpad.View permission.

    By default, any logged-in user can see anything. More restrictive
    rulesets are defined in other IAuthorization implementations.
    """
    permission = 'launchpad.View'
    usedfor = Interface

    def checkAuthenticated(self, user):
        """Any authenticated user can see this object."""
        return True


class AdminByAdminsTeam(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = Interface

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class AdminByCommercialTeamOrAdmins(AuthorizationBase):
    permission = 'launchpad.Commercial'
    usedfor = Interface

    def checkAuthenticated(self, user):
        celebrities = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(celebrities.commercial_admin)
                or user.inTeam(celebrities.admin))


class ViewPillar(AuthorizationBase):
    usedfor = IPillar
    permission = 'launchpad.View'

    def checkUnauthenticated(self):
        return self.obj.active

    def checkAuthenticated(self, user):
        """The Admins & Commercial Admins can see inactive pillars."""
        if self.obj.active:
            return True
        else:
            celebrities = getUtility(ILaunchpadCelebrities)
            return (user.inTeam(celebrities.commercial_admin)
                    or user.inTeam(celebrities.admin))


class EditOAuthAccessToken(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IOAuthAccessToken

    def checkAuthenticated(self, user):
        return (self.obj.person == user
                or user.inTeam(getUtility(ILaunchpadCelebrities).admin))


class EditBugNominationStatus(AuthorizationBase):
    permission = 'launchpad.Driver'
    usedfor = IBugNomination

    def checkAuthenticated(self, user):
        return self.obj.canApprove(user)


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkAuthenticated(self, user):
        return (user.inTeam(self.obj.owner)
                or user.inTeam(getUtility(ILaunchpadCelebrities).admin))


class EditByRegistryExpertsOrOwnersOrAdmins(EditByOwnersOrAdmins):
    usedfor = None
    def checkAuthenticated(self, user):
        if user.inTeam(getUtility(ILaunchpadCelebrities).registry_experts):
            return True
        return EditByOwnersOrAdmins.checkAuthenticated(self, user)


class EditProduct(EditByRegistryExpertsOrOwnersOrAdmins):
    usedfor = IProduct


class EditPackaging(EditByRegistryExpertsOrOwnersOrAdmins):
    usedfor = IPackaging


class EditProductReleaseFile(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IProductReleaseFile
    def checkAuthenticated(self, user):
        if (user.inTeam(getUtility(ILaunchpadCelebrities).registry_experts) or
            user.inTeam(self.obj.productrelease.productseries.owner) or
            user.inTeam(self.obj.productrelease.productseries.product.owner)):
            return True
        return False


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


class EditSpecificationBranch(AuthorizationBase):

    usedfor = ISpecificationBranch
    permission = 'launchpad.Edit'

    def checkAuthenticated(self, user):
        """See `IAuthorization.checkAuthenticated`.

        :return: True or False.
        """
        return True


class ViewSpecificationBranch(EditSpecificationBranch):

    permission = 'launchpad.View'

    def checkUnauthenticated(self):
        """See `IAuthorization.checkUnauthenticated`.

        :return: True or False.
        """
        return True


class EditSpecificationByTargetOwnerOrOwnersOrAdmins(AuthorizationBase):
    """We want everybody "related" to a specification to be able to edit it.
    You are related if you have a role on the spec, or if you have a role on
    the spec target (distro/product) or goal (distroseries/productseries).
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


class Sprint(AuthorizationBase):
    """An attendee, owner, or driver of a sprint."""
    permission = 'launchpad.View'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.driver) or
                user in [attendance.attendee
                         for attendance in self.obj.attendances] or
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


class OnlyRosettaExpertsAndAdmins(AuthorizationBase):
    """Base class that allow access to Rosetta experts and Launchpad admins.
    """

    def checkAuthenticated(self, user):
        """Allow Launchpad's admins and Rosetta experts edit all fields."""
        celebrities = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(celebrities.admin) or
                user.inTeam(celebrities.rosetta_experts))


class AdminProductTranslations(AuthorizationBase):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IProduct

    def checkAuthenticated(self, user):
        """Is the user able to manage `IProduct` translations settings?

        Any Launchpad/Launchpad Translations administrator or owners are
        able to change translation settings for a product.
        """
        celebrities = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(self.obj.owner) or
                user.inTeam(celebrities.admin) or
                user.inTeam(celebrities.rosetta_experts))


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


class AdminShippingRequestSetByShipItAdmins(
        AdminShippingRequestByShipItAdmins):
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
        celebrities = getUtility(ILaunchpadCelebrities)
        if user.inTeam(celebrities.admin):
            return True
        if user.inTeam(celebrities.registry_experts):
            return True
        return user.inTeam(self.obj.target.owner)


class AdminMilestoneByLaunchpadAdmins(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Only the Launchpad admins need this, we are only going to use it
        for connecting up series and distroseriess where we did not have
        them."""
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class EditTeamByTeamOwnerOrLaunchpadAdmins(AuthorizationBase):
    permission = 'launchpad.Owner'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """Only the team owner and Launchpad admins need this.
        """
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(self.obj.teamowner) or user.inTeam(admins)


class EditTeamByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """The team owner and team admins have launchpad.Edit on that team.

        The Launchpad admins also have launchpad.Edit on all teams.
        """
        return can_edit_team(self.obj, user)


class EditTeamMembershipByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeamMembership

    def checkAuthenticated(self, user):
        return can_edit_team(self.obj.team, user)


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


class ViewPublicOrPrivateTeamMembers(AuthorizationBase):
    """Restrict viewing of private memberships of teams.

    Only members of a team with a private membership can view the
    membership list.
    """
    permission = 'launchpad.View'
    usedfor = IPerson

    def checkUnauthenticated(self):
        """Unauthenticated users can only view public memberships."""
        if self.obj.visibility == PersonVisibility.PUBLIC:
            return True
        return False

    def checkAuthenticated(self, user):
        """Verify that the user can view the team's membership.

        Anyone can see a public team's membership.
        Only a team member or a Launchpad admin can view a
        private membership.
        """
        if self.obj.visibility == PersonVisibility.PUBLIC:
            return True
        admins = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(admins) or user.inTeam(self.obj):
            return True
        return False


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
        return can_edit_team(self.obj.poll.team, user)


class AdminDistribution(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroseriess to the Launchpad admin team."""
    permission = 'launchpad.Admin'
    usedfor = IDistribution


class EditDistributionByDistroOwnersOrAdmins(AuthorizationBase):
    """The owner of a distribution should be able to edit its
    information; it is mainly administrative data, such as bug
    contacts. Note that creation of new distributions and distribution
    series is still protected with launchpad.Admin"""
    permission = 'launchpad.Edit'
    usedfor = IDistribution

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(admins))


class AdminDistroSeries(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroseriess to the Launchpad admin team.

    NB: Please consult with SABDFL before modifying this permission because
        changing it could cause the archive to get rearranged, with tons of
        files moved to the new namespace, and mirrors would get very very
        upset. Then James T would be on your case.
    """
    permission = 'launchpad.Admin'
    usedfor = IDistroSeries


class EditDistroSeriesByOwnersOrDistroOwnersOrAdmins(AuthorizationBase):
    """The owner of the distro series should be able to modify some of the
    fields on the IDistroSeries

    NB: there is potential for a great mess if this is not done correctly so
    please consult with SABDFL before modifying these permissions.
    """
    permission = 'launchpad.Edit'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.distribution.owner) or
                user.inTeam(admins))


class SeriesDrivers(AuthorizationBase):
    """Drivers can approve or decline features and target bugs.

    Drivers exist for distribution and product series.
    """
    permission = 'launchpad.Driver'
    usedfor = IHasDrivers

    def checkAuthenticated(self, user):
        for driver in self.obj.drivers:
            if user.inTeam(driver):
                return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class ViewProductSeries(AuthorizationBase):

    usedfor = IProductSeries
    permision = 'launchpad.View'

    def checkUnauthenticated(self):
        """See `IAuthorization.checkUnauthenticated`.

        :return: True or False.
        """
        return True

    def checkAuthenticated(self, user):
        """See `IAuthorization.checkAuthenticated`.

        :return: True or False.
        """
        return True


class EditProductSeries(EditByRegistryExpertsOrOwnersOrAdmins):
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        """Allow product owner, Rosetta Experts, or admins."""
        if user.inTeam(self.obj.product.owner):
            # The user is the owner of the product.
            return True
        # Rosetta experts need to be able to upload translations.
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
        if user.inTeam(rosetta_experts):
            return True
        return EditByRegistryExpertsOrOwnersOrAdmins.checkAuthenticated(
            self, user)


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
        EditPublicByLoggedInUserAndPrivateByExplicitSubscribers.__init__(
            self, bug_branch.bug)


class ViewBugAttachment(PublicToAllOrPrivateToExplicitSubscribersForBug):
    """Security adapter for viewing a bug attachment.

    If the user is authorized to view the bug, he's allowed to view the
    attachment.
    """
    permission = 'launchpad.View'
    usedfor = IBugAttachment

    def __init__(self, bugattachment):
        PublicToAllOrPrivateToExplicitSubscribersForBug.__init__(
            self, bugattachment.bug)


class EditBugAttachment(
    EditPublicByLoggedInUserAndPrivateByExplicitSubscribers):
    """Security adapter for editing a bug attachment.

    If the user is authorized to view the bug, he's allowed to edit the
    attachment.
    """
    permission = 'launchpad.Edit'
    usedfor = IBugAttachment

    def __init__(self, bugattachment):
        EditPublicByLoggedInUserAndPrivateByExplicitSubscribers.__init__(
            self, bugattachment.bug)


class ViewAnnouncement(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IAnnouncement

    def checkUnauthenticated(self):
        """Let anonymous users see published announcements."""
        if self.obj.published:
            return True
        return False

    def checkAuthenticated(self, user):
        """Keep project news invisible to end-users unless they are project
        admins, until the announcements are published."""

        # Every user can view published announcements.
        if self.obj.published:
            return True

        # Project drivers can view any project announcements.
        assert self.obj.target
        if self.obj.target.drivers:
            for driver in self.obj.target.drivers:
                if user.inTeam(driver):
                    return True
        if user.inTeam(self.obj.target.owner):
            return True

        # Launchpad admins can view any announcement.
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class EditAnnouncement(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IAnnouncement

    def checkAuthenticated(self, user):
        """Allow the project owner and drivers to edit any project news."""

        assert self.obj.target
        if self.obj.target.drivers:
            for driver in self.obj.target.drivers:
                if user.inTeam(driver):
                    return True
        if user.inTeam(self.obj.target.owner):
            return True

        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class UseApiDoc(AuthorizationBase):
    permission = 'zope.app.apidoc.UseAPIDoc'
    usedfor = Interface

    def checkAuthenticated(self, user):
        return True


class OnlyBazaarExpertsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and Bazaar
    experts."""

    def checkAuthenticated(self, user):
        bzrexperts = getUtility(ILaunchpadCelebrities).bazaar_experts
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins) or user.inTeam(bzrexperts)


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


class EditCodeImport(OnlyVcsImportsAndAdmins):
    """Control who can edit the object view of a CodeImport.

    Currently, we restrict the visibility of the new code import
    system to members of ~vcs-imports and Launchpad admins.
    """
    permission = 'launchpad.Edit'
    usedfor = ICodeImport


class SeeCodeImportJobSet(OnlyVcsImportsAndAdmins):
    """Control who can see the CodeImportJobSet utility.

    Currently, we restrict the visibility of the new code import
    system to members of ~vcs-imports and Launchpad admins.
    """
    permission = 'launchpad.View'
    usedfor = ICodeImportJobSet


class EditCodeImportJobWorkflow(OnlyVcsImportsAndAdmins):
    """Control who can use the CodeImportJobWorkflow utility.

    Currently, we restrict the visibility of the new code import
    system to members of ~vcs-imports and Launchpad admins.
    """
    permission = 'launchpad.Edit'
    usedfor = ICodeImportJobWorkflow


class EditCodeImportMachine(OnlyVcsImportsAndAdmins):
    """Control who can edit the object view of a CodeImportMachine.

    Access is restricted to members of ~vcs-imports and Launchpad admins.
    """
    permission = 'launchpad.Edit'
    usedfor = ICodeImportMachine


class EditPOTemplateDetails(EditByOwnersOrAdmins):
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        """Allow product/sourcepackage/potemplate owner, experts and admis.
        """
        if (self.obj.productseries is not None and
            user.inTeam(self.obj.productseries.product.owner)):
            # The user is the owner of the product.
            return True

        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

        return (EditByOwnersOrAdmins.checkAuthenticated(self, user) or
                user.inTeam(rosetta_experts))


class AdminPOTemplateDetails(OnlyRosettaExpertsAndAdmins):
    """Permissions to edit all aspects of an IPOTemplate."""
    permission = 'launchpad.Admin'
    usedfor = IPOTemplate


# XXX: Carlos Perello Marin 2005-05-24 bug=753:
# This should be using SuperSpecialPermissions when implemented.
class AddPOTemplate(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Append'
    usedfor = IProductSeries


class EditPOFileDetails(EditByOwnersOrAdmins):
    usedfor = IPOFile

    def checkAuthenticated(self, user):
        """Allow anyone that can edit translations, owner, experts and admis.
        """
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

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


class EditTranslationGroup(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = ITranslationGroup

    def checkAuthenticated(self, user):
        """Allow the owner of a translation group to edit the translator
        of any language in the group."""
        return (user.inTeam(self.obj.owner) or
                OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user))


class EditTranslationGroupSet(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslationGroupSet


class DownloadFullSourcePackageTranslations(OnlyRosettaExpertsAndAdmins):
    """Restrict full `SourcePackage` translation downloads.

    Experience shows that the export queue can easily get swamped by
    large export requests.  Email leads us to believe that many of the
    users making these requests are looking for language packs, or for
    individual translations rather than the whole package.  That's why
    this class defines who is allowed to make those requests.
    """

    permission = 'launchpad.ExpensiveRequest'
    usedfor = ISourcePackage

    def checkAuthenticated(self, user):
        """Define who may download these translations.

        Admins and Translations admins have access, as does the owner of
        the translation group (if applicable).
        """
        translation_group = self.obj.distribution.translationgroup
        return (
            # User is admin of some relevant kind.
            OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
            # User is owner of applicable translation group.
            (translation_group is not None and
             user.inTeam(translation_group.owner)))


class EditBugTracker(EditByRegistryExpertsOrOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IBugTracker


class EditProductRelease(EditByRegistryExpertsOrOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IProductRelease

    def checkAuthenticated(self, user):
        if (user.inTeam(self.obj.productseries.owner) or
            user.inTeam(self.obj.productseries.product.owner)):
            return True
        return EditByRegistryExpertsOrOwnersOrAdmins.checkAuthenticated(
            self, user)


class EditTranslationImportQueueEntry(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = ITranslationImportQueueEntry

    def checkAuthenticated(self, user):
        """Allow who added the entry, experts and admis.
        """
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

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
        """Check user presence in admins or distroseries upload admin team."""
        if AdminByAdminsTeam.checkAuthenticated(self, user):
            return True

        permission_set = getUtility(IArchivePermissionSet)
        permissions = permission_set.componentsForQueueAdmin(
            self.obj.distroseries.main_archive, user)
        return permissions.count() > 0


class EditPackageUpload(AdminByAdminsTeam):
    permission = 'launchpad.Edit'
    usedfor = IPackageUpload

    def checkAuthenticated(self, user):
        """Return True if user has an ArchivePermission or is an admin."""
        if AdminByAdminsTeam.checkAuthenticated(self, user):
            return True

        permission_set = getUtility(IArchivePermissionSet)
        permissions = permission_set.componentsForQueueAdmin(
            self.obj.archive, user)
        if permissions.count() == 0:
            return False
        allowed_components = set(
            permission.component for permission in permissions)
        existing_components = self.obj.components
        # The intersection of allowed_components and
        # existing_components must be equal to existing_components
        # to allow the operation to go ahead.
        return (allowed_components.intersection(existing_components)
                == existing_components)


class AdminByBuilddAdmin(AuthorizationBase):
    permission = 'launchpad.Admin'

    def checkAuthenticated(self, user):
        """Allow admins and buildd_admins."""
        lp_admin = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(lp_admin):
            return True
        buildd_admin = getUtility(ILaunchpadCelebrities).buildd_admin
        return user.inTeam(buildd_admin)


class AdminBuilderSet(AdminByBuilddAdmin):
    usedfor = IBuilderSet


class AdminBuilder(AdminByBuilddAdmin):
    usedfor = IBuilder


# XXX cprov 2006-07-31: As soon as we have external builders, as presumed
# in the original plan, we should grant some rights to the owners and
# that's what Edit is for.
class EditBuilder(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuilder


class AdminBuildRecord(AdminByBuilddAdmin):
    usedfor = IBuild


class EditBuildRecord(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuild

    def _ppaCheckAuthenticated(self, user):
        """Allow only BuilddAdmins and PPA owner."""
        if AdminByBuilddAdmin.checkAuthenticated(self, user):
            return True

        if self.obj.archive.owner and user.inTeam(self.obj.archive.owner):
            return True

        return False

    def checkAuthenticated(self, user):
        """Check write access for user and different kinds of archives.

        Allow
        
            * BuilddAdmins and PPA owner for PPAs
            * users with upload permissions (for the respective distribution)
              otherwise.
        """
        # Is this a PPA? Call the respective method if so.
        if self.obj.archive.purpose == ArchivePurpose.PPA:
            return self._ppaCheckAuthenticated(user)

        # Primary or partner section here: is the user in question allowed
        # to upload to the respective component? Allow user to retry build
        # if so.
        if self.obj.archive.canUpload(user, self.obj.current_component):
            return True
        else:
            return self.obj.archive.canUpload(
                user, self.obj.sourcepackagerelease.sourcepackagename)


class ViewBuildRecord(EditBuildRecord):
    permission = 'launchpad.View'

    def checkAuthenticated(self, user):
        """Private restricts to admins, BuilddAdmins, archive members."""
        if not self.obj.archive.private:
            # Anyone can see non-private archives.
            return True

        # If the permission check on the sourcepackagerelease for this
        # build passes then it means the build can be released from
        # privacy since the source package is published publicly.
        # This happens when copy-package is used to re-publish a private
        # package in the primary archive.
        auth_spr = ViewSourcePackageRelease(self.obj.sourcepackagerelease)
        if auth_spr.checkAuthenticated(user):
            return True

        return EditBuildRecord.checkAuthenticated(self, user)

    def checkUnauthenticated(self):
        """Unauthenticated users can see the build if it's not private."""
        if not self.obj.archive.private:
            return True

        # See comment above.
        auth_spr = ViewSourcePackageRelease(self.obj.sourcepackagerelease)
        return auth_spr.checkUnauthenticated()


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


class ModerateFAQTarget(EditByOwnersOrAdmins):
    permission = 'launchpad.Moderate'
    usedfor = IFAQTarget

    def checkAuthenticated(self, user):
        """Allow people with launchpad.Edit or an answer contact."""
        if EditByOwnersOrAdmins.checkAuthenticated(self, user):
            return True
        if IQuestionTarget.providedBy(self.obj):
            for answer_contact in self.obj.answer_contacts:
                if user.inTeam(answer_contact):
                    return True
        return False


class EditFAQ(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IFAQ

    def checkAuthenticated(self, user):
        """Everybody who has launchpad.Moderate on the FAQ target is allowed.
        """
        return ModerateFAQTarget(self.obj.target).checkAuthenticated(user)


def can_edit_team(team, user):
    """Return True if the given user has edit rights for the given team."""
    if user.inTeam(getUtility(ILaunchpadCelebrities).admin):
        return True
    else:
        return team in user.getAdministratedTeams()


class AdminLanguageSet(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ILanguageSet


class AdminLanguage(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ILanguage


class AccessBranch(AuthorizationBase):
    """Controls visibility of branches.

    A person can see the branch if the branch is public, they are the owner
    of the branch, they are in the team that owns the branch, subscribed to
    the branch, or a launchpad administrator.
    """
    permission = 'launchpad.View'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        if not self.obj.private:
            return True
        if user.inTeam(self.obj.owner):
            return True
        for subscriber in self.obj.subscribers:
            if user.inTeam(subscriber):
                return True
        celebs = getUtility(ILaunchpadCelebrities)
        return user.inTeam(celebs.admin) or user.inTeam(celebs.bazaar_experts)

    def checkUnauthenticated(self):
        return not self.obj.private


class EditBranch(AuthorizationBase):
    """The owner, bazaar experts or admins can edit branches."""
    permission = 'launchpad.Edit'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        celebs = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(self.obj.owner) or
                user.inTeam(celebs.admin) or
                user.inTeam(celebs.bazaar_experts))


class AdminBranch(AuthorizationBase):
    """The bazaar experts or admins can administer branches."""
    permission = 'launchpad.Admin'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        celebs = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(celebs.admin) or
                user.inTeam(celebs.bazaar_experts))


class AdminPOTemplateSubset(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = IPOTemplateSubset


class AdminDistroSeriesLanguage(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = IDistroSeriesLanguage


class AdminDistroSeriesTranslations(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IDistroSeries


class BranchSubscriptionEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBranchSubscription

    def checkAuthenticated(self, user):
        """Is the user able to edit a branch subscription?

        Any team member can edit a branch subscription for their team.
        Launchpad Admins can also edit any branch subscription.
        """
        celebs = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(self.obj.person) or
                user.inTeam(celebs.admin) or
                user.inTeam(celebs.bazaar_experts))


class BranchSubscriptionView(BranchSubscriptionEdit):
    permission = 'launchpad.View'


class BranchMergeProposalView(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBranchMergeProposal

    def checkAuthenticated(self, user):
        """Is the user able to view the branch merge proposal?

        The user can see a merge proposal between two branches
        that the user can see.
        """
        return (AccessBranch(self.obj.source_branch).checkAuthenticated(user)
                and
                AccessBranch(self.obj.target_branch).checkAuthenticated(user))

    def checkUnauthenticated(self):
        """Is anyone able to view the branch merge proposal?

        Anyone can see a merge proposal between two public branches.
        """
        return (AccessBranch(self.obj.source_branch).checkUnauthenticated()
                and
                AccessBranch(self.obj.target_branch).checkUnauthenticated())


class CodeReviewCommentView(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = ICodeReviewComment

    def checkAuthenticated(self, user):
        """Is the user able to view the code review comment?

        The user can see a code review comment if they can see the branch
        merge proposal.
        """
        bmp_checker = BranchMergeProposalView(self.obj.branch_merge_proposal)
        return bmp_checker.checkAuthenticated(user)

    def checkUnauthenticated(self):
        """Are not-logged-in people able to view the code review comment?

        They can see a code review comment if they can see the branch merge
        proposal.
        """
        bmp_checker = BranchMergeProposalView(self.obj.branch_merge_proposal)
        return bmp_checker.checkUnauthenticated()


class BranchMergeProposalEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBranchMergeProposal

    def checkAuthenticated(self, user):
        """Is the user able to edit the branch merge request?

        The user is able to edit if they are:
          * the registrant of the merge proposal
          * the owner of the source_branch
          * the owner of the target_branch
          * the reviewer for the target_branch
          * an administrator
        """
        celebs = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(self.obj.registrant) or
                user.inTeam(self.obj.source_branch.owner) or
                user.inTeam(self.obj.target_branch.owner) or
                user.inTeam(self.obj.target_branch.reviewer) or
                user.inTeam(celebs.admin) or
                user.inTeam(celebs.bazaar_experts))


class ViewEntitlement(AuthorizationBase):
    """Permissions to view IEntitlement objects.

    Allow the owner of the entitlement, the entitlement registrant,
    or any member of the team or any admin to view the entitlement.
    """
    permission = 'launchpad.View'
    usedfor = IEntitlement

    def checkAuthenticated(self, user):
        """Is the user able to view an Entitlement attribute?

        Any team member can edit a branch subscription for their team.
        Launchpad Admins can also edit any branch subscription.
        """
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.person) or
                user.inTeam(self.obj.registrant) or
                user.inTeam(admins))


class AdminDistroSeriesLanguagePacks(
    OnlyRosettaExpertsAndAdmins,
    EditDistroSeriesByOwnersOrDistroOwnersOrAdmins):
    permission = 'launchpad.LanguagePacksAdmin'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistroSeries` language packs?

        Any Launchpad/Launchpad Translations administrator, people allowed to
        edit distroseries or members of IDistribution.language_pack_admin team
        are able to change the language packs available.
        """
        return (
            OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
            EditDistroSeriesByOwnersOrDistroOwnersOrAdmins.checkAuthenticated(
                self, user) or
            user.inTeam(self.obj.distribution.language_pack_admin))


class AdminDistributionTranslations(OnlyRosettaExpertsAndAdmins,
                                    EditDistributionByDistroOwnersOrAdmins):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IDistribution

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistribution` translations settings?

        Any Launchpad/Launchpad Translations administrator or people allowed
        to edit distribution details are able to change translation settings
        for a distribution.
        """
        return (
            OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
            EditDistributionByDistroOwnersOrAdmins.checkAuthenticated(
                self, user))


class AdminLanguagePack(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.LanguagePacksAdmin'
    usedfor = ILanguagePack


class ViewHWSubmission(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IHWSubmission

    def checkAuthenticated(self, user):
        """Can the user view the submission details?

        Submissions that not marked private are publicly visible,
        private submissions may only be accessed by their owner and by
        admins.
        """
        if not self.obj.private:
            return True

        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(self.obj.owner) or user.inTeam(admins)

    def checkUnauthenticated(self):
        return not self.obj.private


class ViewArchive(AuthorizationBase):
    """Restrict viewing of private archives.

    Only admins or members of a team with a private membership can
    view the archive.
    """
    permission = 'launchpad.View'
    usedfor = IArchive

    def checkAuthenticated(self, user):
        """Verify that the user can view the archive.

        Anyone can see a public archive.

        Only a team member or a Launchpad admin can view a
        private archive.
        """
        # No further checks are required if the archive is not private.
        if not self.obj.private:
            return True

        # Admins and this archive's owner or team members are allowed.
        admins = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(admins):
            return True

        if self.obj.owner and user.inTeam(self.obj.owner):
            return True

        return False

    def checkUnauthenticated(self):
        """Unauthenticated users can see the PPA if it's not private."""
        return not self.obj.private


class ViewSourcePackageRelease(AuthorizationBase):
    """Restrict viewing of source packages.

    Packages that are only published in private archives are subject to the
    same viewing rules as the archive (see class ViewArchive).

    If the package is published in any non-private archive, then it is
    automatically viewable even if the package is also published in
    a private archive.
    """
    permission = 'launchpad.View'
    userfor = ISourcePackageRelease

    def checkAuthenticated(self, user):
        """Verify that the user can view the sourcepackagerelease."""
        for archive in self.obj.published_archives:
            if check_permission('launchpad.View', archive):
                return True
        return False

    def checkUnauthenticated(self):
        """Check unauthenticated users.

        Unauthenticated users can see the package as long as it's published
        in a non-private archive.
        """
        for archive in self.obj.published_archives:
            if not archive.private:
                return True
        return False


class MailingListApprovalByExperts(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IMailingListSet

    def checkAuthenticated(self, user):
        experts = getUtility(ILaunchpadCelebrities).mailing_list_experts
        return user.inTeam(experts)


class ViewEmailAddress(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IEmailAddress

    def checkAuthenticated(self, user):
        """Can the user see the details of this email address?

        If the email address' owner doesn't want his email addresses to be
        hidden, anyone can see them.  Otherwise only the owner himself or
        admins can see them.
        """
        if not self.obj.person.hide_email_addresses:
            return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return user == self.obj.person or user.inTeam(admins)
