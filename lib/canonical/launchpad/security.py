# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401

"""Security policies for using content objects."""

__metaclass__ = type
__all__ = [
    ]

from zope.component import (
    getAdapter,
    getUtility,
    )
from zope.interface import Interface

from canonical.config import config
from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.interfaces.emailaddress import IEmailAddress
from canonical.launchpad.interfaces.librarian import (
    ILibraryFileAliasWithParent,
    )
from canonical.launchpad.interfaces.oauth import (
    IOAuthAccessToken,
    IOAuthRequestToken,
    )
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from lp.answers.interfaces.faq import IFAQ
from lp.answers.interfaces.faqtarget import IFAQTarget
from lp.answers.interfaces.question import IQuestion
from lp.answers.interfaces.questionmessage import IQuestionMessage
from lp.answers.interfaces.questionsperson import IQuestionsPerson
from lp.answers.interfaces.questiontarget import IQuestionTarget
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.interfaces.security import IAuthorization
from lp.app.security import (
    AnonymousAuthorization,
    AuthorizationBase,
    ForwardedAuthorization,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfig
from lp.blueprints.interfaces.specification import (
    ISpecification,
    ISpecificationPublic,
    )
from lp.blueprints.interfaces.specificationbranch import ISpecificationBranch
from lp.blueprints.interfaces.specificationsubscription import (
    ISpecificationSubscription,
    )
from lp.blueprints.interfaces.sprint import ISprint
from lp.blueprints.interfaces.sprintspecification import ISprintSpecification
from lp.bugs.interfaces.bugtarget import IOfficialBugTagTargetRestricted
from lp.bugs.interfaces.structuralsubscription import IStructuralSubscription
from lp.buildmaster.interfaces.builder import (
    IBuilder,
    IBuilderSet,
    )
from lp.buildmaster.interfaces.buildfarmbranchjob import IBuildFarmBranchJob
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    IBuildFarmJobOld,
    )
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.code.interfaces.branch import (
    IBranch,
    user_has_special_branch_access,
    )
from lp.code.interfaces.branchmergeproposal import IBranchMergeProposal
from lp.code.interfaces.branchmergequeue import IBranchMergeQueue
from lp.code.interfaces.codeimport import ICodeImport
from lp.code.interfaces.codeimportjob import (
    ICodeImportJobSet,
    ICodeImportJobWorkflow,
    )
from lp.code.interfaces.codeimportmachine import ICodeImportMachine
from lp.code.interfaces.codereviewcomment import (
    ICodeReviewComment,
    ICodeReviewCommentDeletion,
    )
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.code.interfaces.diff import IPreviewDiff
from lp.code.interfaces.sourcepackagerecipe import ISourcePackageRecipe
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild,
    )
from lp.hardwaredb.interfaces.hwdb import (
    IHWDBApplication,
    IHWDevice,
    IHWDeviceClass,
    IHWDriver,
    IHWDriverName,
    IHWDriverPackageName,
    IHWSubmission,
    IHWSubmissionDevice,
    IHWVendorID,
    )
from lp.registry.interfaces.announcement import IAnnouncement
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionmirror import IDistributionMirror
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceAdmin,
    IDistroSeriesDifferenceEdit,
    )
from lp.registry.interfaces.distroseriesparent import IDistroSeriesParent
from lp.registry.interfaces.entitlement import IEntitlement
from lp.registry.interfaces.gpg import IGPGKey
from lp.registry.interfaces.irc import IIrcID
from lp.registry.interfaces.location import IPersonLocation
from lp.registry.interfaces.milestone import (
    IMilestone,
    IProjectGroupMilestone,
    )
from lp.registry.interfaces.nameblacklist import (
    INameBlacklist,
    INameBlacklistSet,
    )
from lp.registry.interfaces.packaging import IPackaging
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    ITeam,
    PersonVisibility,
    )
from lp.registry.interfaces.pillar import IPillar
from lp.registry.interfaces.poll import (
    IPoll,
    IPollOption,
    IPollSubset,
    )
from lp.registry.interfaces.product import (
    IProduct,
    IProductSet,
    )
from lp.registry.interfaces.productrelease import (
    IProductRelease,
    IProductReleaseFile,
    )
from lp.registry.interfaces.productseries import (
    IProductSeries,
    ITimelineProductSeries,
    )
from lp.registry.interfaces.projectgroup import (
    IProjectGroup,
    IProjectGroupSet,
    )
from lp.registry.interfaces.role import (
    IHasDrivers,
    IHasOwner,
    IPersonRoles,
    )
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.interfaces.teammembership import ITeamMembership
from lp.registry.interfaces.wikiname import IWikiName
from lp.services.messages.interfaces.message import IMessage
from lp.services.openid.interfaces.openididentifier import IOpenIdIdentifier
from lp.services.worlddata.interfaces.country import ICountry
from lp.services.worlddata.interfaces.language import (
    ILanguage,
    ILanguageSet,
    )
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.archiveauthtoken import IArchiveAuthToken
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.archivesubscriber import (
    IArchiveSubscriber,
    IArchiveSubscriberSet,
    IPersonalArchiveSubscription,
    )
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.binarypackagerelease import (
    IBinaryPackageReleaseDownloadCount,
    )
from lp.soyuz.interfaces.buildfarmbuildjob import IBuildFarmBuildJob
from lp.soyuz.interfaces.packagecopyjob import IPlainPackageCopyJob
from lp.soyuz.interfaces.packageset import (
    IPackageset,
    IPackagesetSet,
    )
from lp.soyuz.interfaces.publishing import (
    IBinaryPackagePublishingHistory,
    IPublishingEdit,
    ISourcePackagePublishingHistory,
    )
from lp.soyuz.interfaces.queue import (
    IPackageUpload,
    IPackageUploadQueue,
    )
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease
from lp.translations.interfaces.customlanguagecode import ICustomLanguageCode
from lp.translations.interfaces.languagepack import ILanguagePack
from lp.translations.interfaces.pofile import IPOFile
from lp.translations.interfaces.potemplate import IPOTemplate
from lp.translations.interfaces.translationgroup import (
    ITranslationGroup,
    ITranslationGroupSet,
    )
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    ITranslationImportQueueEntry,
    )
from lp.translations.interfaces.translationsperson import ITranslationsPerson
from lp.translations.interfaces.translator import (
    IEditTranslator,
    ITranslator,
    )


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
        return user.in_admin


class AdminByCommercialTeamOrAdmins(AuthorizationBase):
    permission = 'launchpad.Commercial'
    usedfor = Interface

    def checkAuthenticated(self, user):
        return user.in_commercial_admin or user.in_admin


class EditByRegistryExpertsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ILaunchpadRoot

    def checkAuthenticated(self, user):
        return user.in_admin or user.in_registry_experts


class ModerateByRegistryExpertsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Moderate'
    usedfor = None

    def checkAuthenticated(self, user):
        return user.in_admin or user.in_registry_experts


class ModerateDistroSeries(ModerateByRegistryExpertsOrAdmins):
    usedfor = IDistroSeries


class ModerateProduct(ModerateByRegistryExpertsOrAdmins):
    usedfor = IProduct


class ModerateProductSet(ModerateByRegistryExpertsOrAdmins):
    usedfor = IProductSet


class ModerateProject(ModerateByRegistryExpertsOrAdmins):
    usedfor = IProjectGroup


class ModerateProjectGroupSet(ModerateByRegistryExpertsOrAdmins):
    usedfor = IProjectGroupSet


class ModeratePerson(ModerateByRegistryExpertsOrAdmins):
    permission = 'launchpad.Moderate'
    usedfor = IPerson


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
            return (user.in_commercial_admin or
                    user.in_admin or
                    user.in_registry_experts)


class EditAccountBySelfOrAdmin(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IAccount

    def checkAccountAuthenticated(self, account):
        if account == self.obj:
            return True
        return super(
            EditAccountBySelfOrAdmin, self).checkAccountAuthenticated(account)

    def checkAuthenticated(self, user):
        return user.in_admin


class ViewAccount(EditAccountBySelfOrAdmin):
    permission = 'launchpad.View'


class ViewOpenIdIdentifierBySelfOrAdmin(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IOpenIdIdentifier

    def checkAccountAuthenticated(self, account):
        if account == self.obj.account:
            return True
        return super(
            ViewOpenIdIdentifierBySelfOrAdmin,
            self).checkAccountAuthenticated(account)


class SpecialAccount(EditAccountBySelfOrAdmin):
    permission = 'launchpad.Special'

    def checkAuthenticated(self, user):
        """Extend permission to registry experts."""
        return user.in_admin or user.in_registry_experts


class ModerateAccountByRegistryExpert(AuthorizationBase):
    usedfor = IAccount
    permission = 'launchpad.Moderate'

    def checkAuthenticated(self, user):
        return user.in_admin or user.in_registry_experts


class EditOAuthAccessToken(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IOAuthAccessToken

    def checkAuthenticated(self, user):
        return self.obj.person == user.person or user.in_admin


class EditOAuthRequestToken(EditOAuthAccessToken):
    permission = 'launchpad.Edit'
    usedfor = IOAuthRequestToken


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkAuthenticated(self, user):
        return user.isOwner(self.obj) or user.in_admin


class EditProduct(EditByOwnersOrAdmins):
    usedfor = IProduct


class EditPackaging(EditByOwnersOrAdmins):
    usedfor = IPackaging


class EditProductReleaseFile(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IProductReleaseFile

    def checkAuthenticated(self, user):
        return EditProductRelease(self.obj.productrelease).checkAuthenticated(
            user)


class ViewTimelineProductSeries(AnonymousAuthorization):
    """Anyone can view an ITimelineProductSeries."""
    usedfor = ITimelineProductSeries


class ViewProductReleaseFile(AnonymousAuthorization):
    """Anyone can view an IProductReleaseFile."""
    usedfor = IProductReleaseFile


class AdminDistributionMirrorByDistroOwnerOrMirrorAdminsOrAdmins(
        AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IDistributionMirror

    def checkAuthenticated(self, user):
        return (user.isOwner(self.obj.distribution) or
                user.in_admin or
                user.inTeam(self.obj.distribution.mirror_admin))


class EditDistributionMirrorByOwnerOrDistroOwnerOrMirrorAdminsOrAdmins(
        AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IDistributionMirror

    def checkAuthenticated(self, user):
        return (user.isOwner(self.obj) or user.in_admin or
                user.isOwner(self.obj.distribution) or
                user.inTeam(self.obj.distribution.mirror_admin))


class ViewDistributionMirror(AnonymousAuthorization):
    """Anyone can view an IDistributionMirror."""
    usedfor = IDistributionMirror


class ViewMilestone(AnonymousAuthorization):
    """Anyone can view an IMilestone."""
    usedfor = IMilestone


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


class AnonymousAccessToISpecificationPublic(AnonymousAuthorization):
    """Anonymous users have launchpad.View on ISpecificationPublic.

    This is only needed because lazr.restful is hard-coded to check that
    permission before returning things in a collection.
    """

    permission = 'launchpad.View'
    usedfor = ISpecificationPublic


class EditSpecificationByRelatedPeople(AuthorizationBase):
    """We want everybody "related" to a specification to be able to edit it.
    You are related if you have a role on the spec, or if you have a role on
    the spec target (distro/product) or goal (distroseries/productseries).
    """

    permission = 'launchpad.Edit'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        assert self.obj.target
        goal = self.obj.goal
        if goal is not None:
            if user.isOwner(goal) or user.isOneOfDrivers(goal):
                return True
        return (user.in_admin or
                user.isOwner(self.obj.target) or
                user.isOneOfDrivers(self.obj.target) or
                user.isOneOf(
                    self.obj, ['owner', 'drafter', 'assignee', 'approver']))


class AdminSpecification(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        assert self.obj.target
        return (user.isOwner(self.obj.target) or
                user.isOneOfDrivers(self.obj.target) or
                user.in_admin)


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
            self.forwardCheckAuthenticated(user, self.obj.goal))


class EditSprintSpecification(AuthorizationBase):
    """The sprint owner or driver can say what makes it onto the agenda for
    the sprint.
    """
    permission = 'launchpad.Driver'
    usedfor = ISprintSpecification

    def checkAuthenticated(self, user):
        sprint = self.obj.sprint
        return user.isOwner(sprint) or user.isDriver(sprint) or user.in_admin


class DriveSprint(AuthorizationBase):
    """The sprint owner or driver can say what makes it onto the agenda for
    the sprint.
    """
    permission = 'launchpad.Driver'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        return (user.isOwner(self.obj) or
                user.isDriver(self.obj) or
                user.in_admin)


class Sprint(AuthorizationBase):
    """An attendee, owner, or driver of a sprint."""
    permission = 'launchpad.View'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        return (user.isOwner(self.obj) or
                user.isDriver(self.obj) or
                user.person in [attendance.attendee
                            for attendance in self.obj.attendances] or
                user.in_admin)


class EditSpecificationSubscription(AuthorizationBase):
    """The subscriber, and people related to the spec or the target of the
    spec can determine who is essential."""
    permission = 'launchpad.Edit'
    usedfor = ISpecificationSubscription

    def checkAuthenticated(self, user):
        if self.obj.specification.goal is not None:
            if user.isOneOfDrivers(self.obj.specification.goal):
                return True
        else:
            if user.isOneOfDrivers(self.obj.specification.target):
                return True
        return (user.inTeam(self.obj.person) or
                user.isOneOf(
                    self.obj.specification,
                    ['owner', 'drafter', 'assignee', 'approver']) or
                user.in_admin)


class OnlyRosettaExpertsAndAdmins(AuthorizationBase):
    """Base class that allow access to Rosetta experts and Launchpad admins.
    """

    def checkAuthenticated(self, user):
        """Allow Launchpad's admins and Rosetta experts edit all fields."""
        return user.in_admin or user.in_rosetta_experts


class AdminProjectTranslations(AuthorizationBase):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IProjectGroup

    def checkAuthenticated(self, user):
        """Is the user able to manage `IProjectGroup` translations settings?

        Any Launchpad/Launchpad Translations administrator or owner is
        able to change translation settings for a project group.
        """
        return (user.isOwner(self.obj) or
                user.in_rosetta_experts or
                user.in_admin)


class AdminProductTranslations(AuthorizationBase):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IProduct

    def checkAuthenticated(self, user):
        """Is the user able to manage `IProduct` translations settings?

        Any Launchpad/Launchpad Translations administrator or owners are
        able to change translation settings for a product.
        """
        return (user.isOwner(self.obj) or
                user.isOneOfDrivers(self.obj) or
                user.in_rosetta_experts or
                user.in_admin)


class EditProjectMilestoneNever(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IProjectGroupMilestone

    def checkAuthenticated(self, user):
        """IProjectGroupMilestone is a fake content object."""
        return False


class EditMilestoneByTargetOwnerOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Authorize the product or distribution owner."""
        if user.in_admin:
            return True
        if (self.obj.series_target is not None
            and user.isDriver(self.obj.series_target)):
            # The user is a release manager.
            # XXX sinzui 2009-07-18 bug=40978: The series_target should never
            # be None, but Milestones in the production DB are like this.
            return True
        return user.isOwner(self.obj.target)


class AdminMilestoneByLaunchpadAdmins(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Only the Launchpad admins need this, we are only going to use
        it for connecting up series and distroseries where we did not
        have them.
        """
        return user.in_admin


class ModeratePersonSetByExpertsOrAdmins(ModerateByRegistryExpertsOrAdmins):
    permission = 'launchpad.Moderate'
    usedfor = IPersonSet


class EditTeamByTeamOwnerOrLaunchpadAdmins(AuthorizationBase):
    permission = 'launchpad.Owner'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """Only the team owner and Launchpad admins need this.
        """
        return user.inTeam(self.obj.teamowner) or user.in_admin


class EditTeamByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """The team owner and team admins have launchpad.Edit on that team.

        The Launchpad admins also have launchpad.Edit on all teams.
        """
        return can_edit_team(self.obj, user)


class ModerateTeam(ModerateByRegistryExpertsOrAdmins):
    permission = 'launchpad.Moderate'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """Is the user a privileged team member or Launchpad staff?

        Return true when the user is a member of Launchpad admins,
        registry experts, team admins, or the team owners.
        """
        return (
            super(ModerateTeam, self).checkAuthenticated(user)
            or can_edit_team(self.obj, user))


class EditTeamMembershipByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeamMembership

    def checkAuthenticated(self, user):
        return can_edit_team(self.obj.team, user)


# XXX: 2008-08-01, salgado: At some point we should protect ITeamMembership
# with launchpad.View so that this adapter is used.  For now, though, it's
# going to be used only on the webservice (which explicitly checks for
# launchpad.View) so that we don't leak memberships of private teams.

class ViewTeamMembership(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = ITeamMembership

    def checkUnauthenticated(self):
        """Unauthenticated users can only view public memberships."""
        return self.obj.team.visibility == PersonVisibility.PUBLIC

    def checkAuthenticated(self, user):
        """Verify that the user can view the team's membership.

        Anyone can see a public team's membership. Only a team member or
        commercial admin or a Launchpad admin can view a private team.
        """
        if self.obj.team.visibility == PersonVisibility.PUBLIC:
            return True
        if (user.in_admin or user.in_commercial_admin
            or user.inTeam(self.obj.team)):
            return True
        return False


class EditPersonBySelfOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPerson

    def checkAuthenticated(self, user):
        """A user can edit the Person who is herself.

        The admin team can also edit any Person.
        """
        return self.obj.id == user.person.id or user.in_admin


class EditTranslationsPersonByPerson(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITranslationsPerson

    def checkAuthenticated(self, user):
        person = self.obj.person
        return person == user.person or user.in_admin


class ViewPersonLocation(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IPersonLocation

    def checkUnauthenticated(self):
        return self.obj.visible

    def checkAuthenticated(self, user):
        if self.obj.visible:
            return True
        else:
            return user.person == self.obj.person or user.in_admin


class EditPersonBySelf(AuthorizationBase):
    permission = 'launchpad.Special'
    usedfor = IPerson

    def checkAuthenticated(self, user):
        """A user can edit the Person who is herself."""
        return self.obj.id == user.person.id


class ViewPublicOrPrivateTeamMembers(AuthorizationBase):
    """Restrict viewing of private teams.

    Only members of a private team can view the
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

        Anyone can see a public team's membership. Only a team member,
        commercial admin, or a Launchpad admin can view a private team's
        members.
        """
        if self.obj.visibility == PersonVisibility.PUBLIC:
            return True
        if user.in_admin or user.in_commercial_admin or user.inTeam(self.obj):
            return True
        # We also grant visibility of the private team to administrators of
        # other teams that have been invited to join the private team.
        for invitee in self.obj.invited_members:
            if (invitee.is_team and
                invitee in user.person.getAdministratedTeams()):
                return True

        if (self.obj.is_team
            and self.obj.visibility == PersonVisibility.PRIVATE):
            # Grant visibility to people with subscriptions on a private
            # team's private PPA.
            subscriptions = getUtility(
                IArchiveSubscriberSet).getBySubscriber(user.person)
            subscriber_archive_ids = set(
                sub.archive.id for sub in subscriptions)
            team_ppa_ids = set(
                ppa.id for ppa in self.obj.ppas if ppa.private)
            if len(subscriber_archive_ids.intersection(team_ppa_ids)) > 0:
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
        return user.isOwner(self.obj) or user.in_admin


class ModerateDistributionByDriversOrOwnersOrAdmins(AuthorizationBase):
    """Distribution drivers, owners, and admins may plan releases.

    Drivers of `IDerivativeDistribution`s can create series. Owners and
    admins can create series for all `IDistribution`s.
    """
    permission = 'launchpad.Moderate'
    usedfor = IDistribution

    def checkAuthenticated(self, user):
        if user.isDriver(self.obj) and not self.obj.full_functionality:
            # Drivers of derivative distributions can create a series that
            # they will be the release manager for.
            return True
        return user.isOwner(self.obj) or user.in_admin


class BugSuperviseDistributionSourcePackage(AuthorizationBase):
    """The owner of a distribution should be able to edit its source
    package information"""
    permission = 'launchpad.BugSupervisor'
    usedfor = IDistributionSourcePackage

    def checkAuthenticated(self, user):
        return (user.inTeam(self.obj.distribution.bug_supervisor) or
                user.inTeam(self.obj.distribution.owner) or
                user.in_admin)


class EditDistributionSourcePackage(AuthorizationBase):
    """DistributionSourcePackage is not editable.

    But EditStructuralSubscription needs launchpad.Edit defined on all
    targets.
    """
    permission = 'launchpad.Edit'
    usedfor = IDistributionSourcePackage


class EditProductOfficialBugTagsByOwnerOrBugSupervisorOrAdmins(
    AuthorizationBase):
    """Product's owner and bug supervisor can set official bug tags."""

    permission = 'launchpad.BugSupervisor'
    usedfor = IOfficialBugTagTargetRestricted

    def checkAuthenticated(self, user):
        return (user.inTeam(self.obj.bug_supervisor) or
                user.inTeam(self.obj.owner) or
                user.in_admin)


class NominateBugForProductSeries(AuthorizationBase):
    """Product's owners and bug supervisors can add bug nominations."""

    permission = 'launchpad.BugSupervisor'
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        return (user.inTeam(self.obj.product.bug_supervisor) or
                user.inTeam(self.obj.product.owner) or
                user.in_admin)


class NominateBugForDistroSeries(AuthorizationBase):
    """Distro's owners and bug supervisors can add bug nominations."""

    permission = 'launchpad.BugSupervisor'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        return (user.inTeam(self.obj.distribution.bug_supervisor) or
                user.inTeam(self.obj.distribution.owner) or
                user.in_admin)


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


class EditDistroSeriesByReleaseManagerOrDistroOwnersOrAdmins(
    AuthorizationBase):
    """The owner of the distro series (i.e. the owner of the distribution)
    should be able to modify some of the fields on the IDistroSeries

    NB: there is potential for a great mess if this is not done correctly so
    please consult with Kiko and MDZ on the mailing list before modifying
    these permissions.
    """
    permission = 'launchpad.Edit'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        if (user.inTeam(self.obj.driver)
            and not self.obj.distribution.full_functionality):
            # The series driver (release manager) may edit a series if the
            # distribution is an `IDerivativeDistribution`
            return True
        return (user.inTeam(self.obj.distribution.owner) or
                user.in_admin)


class ViewDistroSeries(AnonymousAuthorization):
    """Anyone can view a DistroSeries."""
    usedfor = IDistroSeries


class EditDistroSeriesParent(AuthorizationBase):
    """DistroSeriesParent can be edited by the same people who can edit
    the derived_distroseries."""
    permission = "launchpad.Edit"
    usedfor = IDistroSeriesParent

    def checkAuthenticated(self, user):
        auth = EditDistroSeriesByReleaseManagerOrDistroOwnersOrAdmins(
            self.obj.derived_series)
        return auth.checkAuthenticated(user)


class ViewCountry(AnonymousAuthorization):
    """Anyone can view a Country."""
    usedfor = ICountry


class AdminDistroSeriesDifference(AuthorizationBase):
    """You need to be an archive admin or LP admin to get lp.Admin."""
    permission = 'launchpad.Admin'
    usedfor = IDistroSeriesDifferenceAdmin

    def checkAuthenticated(self, user):
        # Archive admin is done by component, so here we just
        # see if the user has that permission on any components
        # at all.
        archive = self.obj.derived_series.main_archive
        return bool(
            archive.getComponentsForQueueAdmin(user.person)) or user.in_admin


class EditDistroSeriesDifference(ForwardedAuthorization):
    """Anyone with lp.View on the distribution can edit a DSD."""
    permission = 'launchpad.Edit'
    usedfor = IDistroSeriesDifferenceEdit

    def __init__(self, obj):
        super(EditDistroSeriesDifference, self).__init__(
            obj.derived_series.distribution, 'launchpad.View')

    def checkUnauthenticated(self):
        return False


class SeriesDrivers(AuthorizationBase):
    """Drivers can approve or decline features and target bugs.

    Drivers exist for distribution and product series.  Distribution and
    product owners are implicitly drivers too.
    """
    permission = 'launchpad.Driver'
    usedfor = IHasDrivers

    def checkAuthenticated(self, user):
        return self.obj.personHasDriverRights(user)


class ViewProductSeries(AnonymousAuthorization):

    usedfor = IProductSeries


class EditProductSeries(EditByOwnersOrAdmins):
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        """Allow product owner, some experts, or admins."""
        if (user.inTeam(self.obj.product.owner) or
            user.inTeam(self.obj.driver)):
            # The user is the owner of the product, or the release manager.
            return True
        # Rosetta experts need to be able to upload translations.
        # Registry admins are just special.
        if (user.in_registry_experts or
            user.in_rosetta_experts):
            return True
        return EditByOwnersOrAdmins.checkAuthenticated(self, user)


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
        # Launchpad admins can view any announcement.
        assert self.obj.target
        return (user.isOneOfDrivers(self.obj.target) or
                user.isOwner(self.obj.target) or
                user.in_admin)


class EditAnnouncement(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IAnnouncement

    def checkAuthenticated(self, user):
        """Allow the project owner and drivers to edit any project news."""

        assert self.obj.target
        return (user.isOneOfDrivers(self.obj.target) or
                user.isOwner(self.obj.target) or
                user.in_admin)


class EditStructuralSubscription(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IStructuralSubscription

    def checkAuthenticated(self, user):
        """Who can edit StructuralSubscriptions."""

        assert self.obj.target

        # Removal of a target cascades removals to StructuralSubscriptions,
        # so we need to allow editing to those who can edit the target itself.
        can_edit_target = self.forwardCheckAuthenticated(
            user, self.obj.target)

        # Who is actually allowed to edit a subscription is determined by
        # a helper method on the model.
        can_edit_subscription = self.obj.target.userCanAlterSubscription(
            self.obj.subscriber, user.person)

        return (can_edit_target or can_edit_subscription)


class UseApiDoc(AuthorizationBase):
    """This is just to please apidoc.launchpad.dev."""
    permission = 'zope.app.apidoc.UseAPIDoc'
    usedfor = Interface

    def checkUnauthenticated(self):
        # We only want this permission to work at all for devmode.
        return config.devmode

    def checkAuthenticated(self, user):
        # We only want this permission to work at all for devmode.
        return config.devmode


class ManageApplicationForEverybody(UseApiDoc):
    """This is just to please apidoc.launchpad.dev.

    We do this because zope.app.apidoc uses that permission, but nothing else
    should be using it.
    """
    permission = 'zope.ManageApplication'
    usedfor = Interface


class ZopeViewForEverybody(UseApiDoc):
    """This is just to please apidoc.launchpad.dev.

    We do this because zope.app.apidoc uses that permission, but nothing else
    should be using it.
    """
    permission = 'zope.View'
    usedfor = Interface


class OnlyBazaarExpertsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and Bazaar
    experts."""

    def checkAuthenticated(self, user):
        return user.in_admin


class OnlyVcsImportsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and VCS Imports
    experts."""

    def checkAuthenticated(self, user):
        return user.in_admin or user.in_vcs_imports


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


class EditCodeImportMachine(OnlyBazaarExpertsAndAdmins):
    """Control who can edit the object view of a CodeImportMachine.

    Access is restricted to Launchpad admins.
    """
    permission = 'launchpad.Edit'
    usedfor = ICodeImportMachine


class AdminSourcePackageRecipeBuilds(AuthorizationBase):
    """Control who can edit SourcePackageRecipeBuilds.

    Access is restricted to Buildd Admins.
    """
    permission = 'launchpad.Admin'
    usedfor = ISourcePackageRecipeBuild

    def checkAuthenticated(self, user):
        return user.in_buildd_admin


class EditBranchMergeQueue(AuthorizationBase):
    """Control who can edit a BranchMergeQueue.

    Access is granted only to the owner of the queue.
    """
    permission = 'launchpad.Edit'
    usedfor = IBranchMergeQueue

    def checkAuthenticated(self, user):
        return user.isOwner(self.obj)


class AdminDistributionTranslations(AuthorizationBase):
    """Class for deciding who can administer distribution translations.

    This class is used for `launchpad.TranslationsAdmin` privilege on
    `IDistribution` and `IDistroSeries` and corresponding `IPOTemplate`s,
    and limits access to Rosetta experts, Launchpad admins and distribution
    translation group owner.
    """
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IDistribution

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistribution` translations settings?

        Any Launchpad/Launchpad Translations administrator, translation group
        owner or a person allowed to edit distribution details is able to
        change translations settings for a distribution.
        """
        # Translation group owner for a distribution is also a
        # translations administrator for it.
        translation_group = self.obj.translationgroup
        if translation_group and user.inTeam(translation_group.owner):
            return True
        else:
            return (user.in_rosetta_experts or
                    EditDistributionByDistroOwnersOrAdmins(
                        self.obj).checkAuthenticated(user))


class ViewPOTemplates(AnonymousAuthorization):
    """Anyone can view an IPOTemplate."""
    usedfor = IPOTemplate


class AdminPOTemplateDetails(OnlyRosettaExpertsAndAdmins):
    """Controls administration of an `IPOTemplate`.

    Allow all persons that can also administer the translations to
    which this template belongs to and also translation group owners.

    Product owners does not have administrative privileges.
    """

    permission = 'launchpad.Admin'
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        template = self.obj
        if user.in_rosetta_experts or user.in_admin:
            return True
        if template.distroseries is not None:
            # Template is on a distribution.
            return (
                self.forwardCheckAuthenticated(user, template.distroseries,
                                               'launchpad.TranslationsAdmin'))
        else:
            # Template is on a product.
            return False


class EditPOTemplateDetails(AuthorizationBase):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        template = self.obj
        if template.distroseries is not None:
            # Template is on a distribution.
            return (
                user.isOwner(template) or
                self.forwardCheckAuthenticated(user, template.distroseries))
        else:
            # Template is on a product.
            return (
                user.isOwner(template) or
                self.forwardCheckAuthenticated(user, template.productseries))


class AddPOTemplate(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Append'
    usedfor = IProductSeries


class ViewPOFile(AnonymousAuthorization):
    """Anyone can view an IPOFile."""
    usedfor = IPOFile


class EditPOFile(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPOFile

    def checkAuthenticated(self, user):
        """The `POFile` itself keeps track of this permission."""
        return self.obj.canEditTranslations(user.person)


class AdminTranslator(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslator

    def checkAuthenticated(self, user):
        """Allow the owner of a translation group to edit the translator
        of any language in the group."""
        return (user.inTeam(self.obj.translationgroup.owner) or
                OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user))


class EditTranslator(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = IEditTranslator

    def checkAuthenticated(self, user):
        """Allow the translator and the group owner to edit parts of
        the translator entry."""
        return (user.inTeam(self.obj.translator) or
                user.inTeam(self.obj.translationgroup.owner) or
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

    def _userInAnyOfTheTeams(self, user, archive_permissions):
        if archive_permissions is None or len(archive_permissions) == 0:
            return False
        for permission in archive_permissions:
            if user.inTeam(permission.person):
                return True
        return False

    def checkAuthenticated(self, user):
        """Define who may download these translations.

        Admins and Translations admins have access, as does the owner of
        the translation group (if applicable) and distribution uploaders.
        """
        distribution = self.obj.distribution
        translation_group = distribution.translationgroup
        return (
            # User is admin of some relevant kind.
            OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
            # User is part of the 'driver' team for the distribution.
            (self._userInAnyOfTheTeams(user, distribution.uploaders)) or
            # User is owner of applicable translation group.
            (translation_group is not None and
             user.inTeam(translation_group.owner)))


class EditProductRelease(EditByOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IProductRelease

    def checkAuthenticated(self, user):
        if (user.inTeam(self.obj.productseries.owner) or
            user.inTeam(self.obj.productseries.product.owner) or
            user.inTeam(self.obj.productseries.driver)):
            # The user is an owner or a release manager.
            return True
        return EditByOwnersOrAdmins.checkAuthenticated(
            self, user)


class ViewProductRelease(AnonymousAuthorization):

    usedfor = IProductRelease


class AdminTranslationImportQueueEntry(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ITranslationImportQueueEntry

    def checkAuthenticated(self, user):
        if self.obj.distroseries is not None:
            series = self.obj.distroseries
        else:
            series = self.obj.productseries
        return (
            self.forwardCheckAuthenticated(user, series,
                                           'launchpad.TranslationsAdmin'))


class EditTranslationImportQueueEntry(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITranslationImportQueueEntry

    def checkAuthenticated(self, user):
        """Anyone who can admin an entry, plus its owner or the owner of the
        product or distribution, can edit it.
        """
        return (self.forwardCheckAuthenticated(
                    user, self.obj, 'launchpad.Admin') or
                user.inTeam(self.obj.importer))


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
            self.obj.distroseries.distribution.all_distro_archives,
            user.person)
        return not permissions.is_empty()


class EditPlainPackageCopyJob(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPlainPackageCopyJob

    def checkAuthenticated(self, user):
        archive = self.obj.target_archive
        if archive.is_ppa:
            return archive.checkArchivePermission(user.person)

        permission_set = getUtility(IArchivePermissionSet)
        permissions = permission_set.componentsForQueueAdmin(
            archive, user.person)
        return not permissions.is_empty()


class EditPackageUpload(AdminByAdminsTeam):
    permission = 'launchpad.Edit'
    usedfor = IPackageUpload

    def checkAuthenticated(self, user):
        """Return True if user has an ArchivePermission or is an admin.

        If it's a delayed-copy, check if the user can upload to its targeted
        archive.
        """
        if AdminByAdminsTeam.checkAuthenticated(self, user):
            return True

        if self.obj.is_delayed_copy:
            archive_append = AppendArchive(self.obj.archive)
            return archive_append.checkAuthenticated(user)

        permission_set = getUtility(IArchivePermissionSet)
        permissions = permission_set.componentsForQueueAdmin(
            self.obj.archive, user.person)
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
        return user.in_buildd_admin or user.in_admin


class AdminBuilderSet(AdminByBuilddAdmin):
    usedfor = IBuilderSet


class AdminBuilder(AdminByBuilddAdmin):
    usedfor = IBuilder


class EditBuilder(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuilder


class AdminBuildRecord(AdminByBuilddAdmin):
    usedfor = IBuildFarmJob


class EditBuildFarmJob(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuildFarmJob


class EditPackageBuild(EditBuildFarmJob):
    usedfor = IPackageBuild

    def checkAuthenticated(self, user):
        """Check if the user has access to edit the archive."""
        if EditBuildFarmJob.checkAuthenticated(self, user):
            return True

        # If the user is in the owning team for the archive,
        # then they have access to edit the builds.
        # If it's a PPA or a copy archive only allow its owner.
        return (self.obj.archive.owner and
                user.inTeam(self.obj.archive.owner))


class EditBinaryPackageBuild(EditPackageBuild):
    permission = 'launchpad.Edit'
    usedfor = IBinaryPackageBuild

    def checkAuthenticated(self, user):
        """Check write access for user and different kinds of archives.

        Allow
            * BuilddAdmins, for any archive.
            * The PPA owner for PPAs
            * users with upload permissions (for the respective distribution)
              otherwise.
        """
        if EditPackageBuild.checkAuthenticated(self, user):
            return True

        # Primary or partner section here: is the user in question allowed
        # to upload to the respective component, packageset or package? Allow
        # user to retry build if so.
        # strict_component is True because the source package already exists,
        # otherwise, how can they give it back?
        check_perms = self.obj.archive.checkUpload(
            user.person, self.obj.distro_series,
            self.obj.source_package_release.sourcepackagename,
            self.obj.current_component, self.obj.pocket,
            strict_component=True)
        return check_perms == None


class ViewBinaryPackageBuild(EditBinaryPackageBuild):
    permission = 'launchpad.View'

    # This code MUST match the logic in
    # IBinaryPackageBuildSet.getBuildsForBuilder() otherwise users are
    # likely to get 403 errors, or worse.
    def checkAuthenticated(self, user):
        """Private restricts to admins and archive members."""
        if not self.obj.archive.private:
            # Anyone can see non-private archives.
            return True

        if user.inTeam(self.obj.archive.owner):
            # Anyone in the PPA team gets the nod.
            return True

        # LP admins may also see it.
        if user.in_admin:
            return True

        # If the permission check on the sourcepackagerelease for this
        # build passes then it means the build can be released from
        # privacy since the source package is published publicly.
        # This happens when copy-package is used to re-publish a private
        # package in the primary archive.
        auth_spr = ViewSourcePackageRelease(self.obj.source_package_release)
        if auth_spr.checkAuthenticated(user):
            return True

        # You're not a celebrity, get out of here.
        return False

    def checkUnauthenticated(self):
        """Unauthenticated users can see the build if it's not private."""
        if not self.obj.archive.private:
            return True

        # See comment above.
        auth_spr = ViewSourcePackageRelease(self.obj.source_package_release)
        return auth_spr.checkUnauthenticated()


class ViewBuildFarmJobOld(AuthorizationBase):
    """Permission to view an `IBuildFarmJobOld`.

    This permission is based entirely on permission to view the
    associated `IBinaryPackageBuild` and/or `IBranch`.
    """
    permission = 'launchpad.View'
    usedfor = IBuildFarmJobOld

    def _getBranch(self):
        """Get `IBranch` associated with this job, if any."""
        if IBuildFarmBranchJob.providedBy(self.obj):
            return self.obj.branch
        else:
            return None

    def _getBuild(self):
        """Get `IPackageBuild` associated with this job, if any."""
        if IBuildFarmBuildJob.providedBy(self.obj):
            return self.obj.build
        else:
            return None

    def _checkBuildPermission(self, user=None):
        """Check access to `IPackageBuild` for this job."""
        permission = getAdapter(
            self.obj.build, IAuthorization, self.permission)
        if user is None:
            return permission.checkUnauthenticated()
        else:
            return permission.checkAuthenticated(user)

    def _checkAccess(self, user=None):
        """Unified access check for anonymous and authenticated users."""
        branch = self._getBranch()
        if branch is not None and not branch.visibleByUser(user):
            return False

        build = self._getBuild()
        if build is not None and not self._checkBuildPermission(user):
            return False

        return True

    checkAuthenticated = _checkAccess
    checkUnauthenticated = _checkAccess


class SetQuestionCommentVisibility(AuthorizationBase):
    permission = 'launchpad.Moderate'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Admins and registry admins can set bug comment visibility."""
        return (user.in_admin or user.in_registry_experts)


class AdminQuestion(AdminByAdminsTeam):
    permission = 'launchpad.Admin'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow only admins and owners of the question pillar target."""
        context = self.obj.product or self.obj.distribution
        return (AdminByAdminsTeam.checkAuthenticated(self, user) or
                user.inTeam(context.owner))


class AppendQuestion(AdminQuestion):
    permission = 'launchpad.Append'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow user who can administer the question and answer contacts."""
        if AdminQuestion.checkAuthenticated(self, user):
            return True
        question_target = self.obj.target
        if IDistributionSourcePackage.providedBy(question_target):
            question_targets = (question_target, question_target.distribution)
        else:
            question_targets = (question_target, )
        questions_person = IQuestionsPerson(user.person)
        for target in questions_person.getDirectAnswerQuestionTargets():
            if target in question_targets:
                return True
        for target in questions_person.getTeamAnswerQuestionTargets():
            if target in question_targets:
                return True
        return False


class QuestionOwner(AuthorizationBase):
    permission = 'launchpad.Owner'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow the question's owner."""
        return user.inTeam(self.obj.owner)


class ViewQuestion(AnonymousAuthorization):
    usedfor = IQuestion


class ViewQuestionMessage(AnonymousAuthorization):
    usedfor = IQuestionMessage


class AppendFAQTarget(EditByOwnersOrAdmins):
    permission = 'launchpad.Append'
    usedfor = IFAQTarget

    def checkAuthenticated(self, user):
        """Allow people with launchpad.Edit or an answer contact."""
        if EditByOwnersOrAdmins.checkAuthenticated(self, user):
            return True
        if IQuestionTarget.providedBy(self.obj):
            # Adapt QuestionTargets to FAQTargets to ensure the correct
            # object is being examined; the implementers are not synonymous.
            faq_target = IFAQTarget(self.obj)
            questions_person = IQuestionsPerson(user.person)
            for target in questions_person.getDirectAnswerQuestionTargets():
                if IFAQTarget(target) == faq_target:
                    return True
            for target in questions_person.getTeamAnswerQuestionTargets():
                if IFAQTarget(target) == faq_target:
                    return True
        return False


class EditFAQ(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IFAQ

    def checkAuthenticated(self, user):
        """Everybody who has launchpad.Append on the FAQ target is allowed.
        """
        return AppendFAQTarget(self.obj.target).checkAuthenticated(user)


def can_edit_team(team, user):
    """Return True if the given user has edit rights for the given team."""
    if user.in_admin:
        return True
    else:
        return team in user.person.getAdministratedTeams()


class ViewNameBlacklist(EditByRegistryExpertsOrAdmins):
    permission = 'launchpad.View'
    usedfor = INameBlacklist


class EditNameBlacklist(EditByRegistryExpertsOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = INameBlacklist


class ViewNameBlacklistSet(EditByRegistryExpertsOrAdmins):
    permission = 'launchpad.View'
    usedfor = INameBlacklistSet


class EditNameBlacklistSet(EditByRegistryExpertsOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = INameBlacklistSet


class ViewLanguageSet(AnonymousAuthorization):
    """Anyone can view an ILangaugeSet."""
    usedfor = ILanguageSet


class AdminLanguageSet(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ILanguageSet


class ViewLanguage(AnonymousAuthorization):
    """Anyone can view an ILangauge."""
    usedfor = ILanguage


class AdminLanguage(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ILanguage


class AdminCustomLanguageCode(AuthorizationBase):
    """Controls administration for a custom language code.

    Whoever can admin a product's or distribution's translations can also
    admin the custom language codes for it.
    """
    permission = 'launchpad.TranslationsAdmin'
    usedfor = ICustomLanguageCode

    def checkAuthenticated(self, user):
        if self.obj.product is not None:
            return AdminProductTranslations(
                self.obj.product).checkAuthenticated(user)
        else:
            return AdminDistributionTranslations(
                self.obj.distribution).checkAuthenticated(user)


class AccessBranch(AuthorizationBase):
    """Controls visibility of branches.

    A person can see the branch if the branch is public, they are the owner
    of the branch, they are in the team that owns the branch, subscribed to
    the branch, or a launchpad administrator.
    """
    permission = 'launchpad.View'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        return self.obj.visibleByUser(user.person)

    def checkUnauthenticated(self):
        return self.obj.visibleByUser(None)


class EditBranch(AuthorizationBase):
    """The owner or admins can edit branches."""
    permission = 'launchpad.Edit'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        can_edit = (
            user.inTeam(self.obj.owner) or
            user_has_special_branch_access(user.person) or
            can_upload_linked_package(user, self.obj))
        if can_edit:
            return True
        # It used to be the case that all import branches were owned by the
        # special, restricted team ~vcs-imports. For these legacy code import
        # branches, we still want the code import registrant to be able to
        # edit them. Similarly, we still want vcs-imports members to be able
        # to edit those branches.
        code_import = self.obj.code_import
        if code_import is None:
            return False
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        return (
            user.in_vcs_imports
            or (self.obj.owner == vcs_imports
                and user.inTeam(code_import.registrant)))


def can_upload_linked_package(person_role, branch):
    """True if person may upload the package linked to `branch`."""
    # No associated `ISuiteSourcePackage` data -> not an official branch.
    # Abort.
    ssp_list = branch.associatedSuiteSourcePackages()
    if len(ssp_list) < 1:
        return False

    # XXX al-maisan, 2009-10-20: a branch may currently be associated with a
    # number of (distroseries, sourcepackagename, pocket) combinations.
    # This does not seem right. But until the database model is fixed we work
    # around this by assuming that things are fine as long as we find at least
    # one combination that allows us to upload the corresponding source
    # package.
    for ssp in ssp_list:
        archive = ssp.sourcepackage.get_default_archive()
        if archive.canUploadSuiteSourcePackage(person_role.person, ssp):
            return True
    return False


class AdminBranch(AuthorizationBase):
    """The admins can administer branches."""
    permission = 'launchpad.Admin'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        return user.in_admin


class AdminDistroSeriesTranslations(AuthorizationBase):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistroSeries` translations.

        Distribution translation managers and distribution series drivers
        can manage IDistroSeries translations.
        """
        return (user.isOneOfDrivers(self.obj) or
                self.forwardCheckAuthenticated(user, self.obj.distribution))


class AdminDistributionSourcePackageTranslations(ForwardedAuthorization):
    """DistributionSourcePackage objects link to a distribution."""
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IDistributionSourcePackage

    def __init__(self, obj):
        super(AdminDistributionSourcePackageTranslations, self).__init__(
            obj.distribution)


class AdminProductSeriesTranslations(AuthorizationBase):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        """Is the user able to manage `IProductSeries` translations."""

        return (user.isOwner(self.obj) or
                user.isOneOfDrivers(self.obj) or
                self.forwardCheckAuthenticated(user, self.obj.product))


class BranchMergeProposalView(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBranchMergeProposal

    @property
    def branches(self):
        required = [self.obj.source_branch, self.obj.target_branch]
        if self.obj.prerequisite_branch:
            required.append(self.obj.prerequisite_branch)
        return required

    def checkAuthenticated(self, user):
        """Is the user able to view the branch merge proposal?

        The user can see a merge proposal if they can see the source, target
        and prerequisite branches.
        """
        return all(map(
            lambda b: AccessBranch(b).checkAuthenticated(user),
            self.branches))

    def checkUnauthenticated(self):
        """Is anyone able to view the branch merge proposal?

        Anyone can see a merge proposal between two public branches.
        """
        return all(map(
            lambda b: AccessBranch(b).checkUnauthenticated(),
            self.branches))


class PreviewDiffView(ForwardedAuthorization):
    permission = 'launchpad.View'
    usedfor = IPreviewDiff

    def __init__(self, obj):
        super(PreviewDiffView, self).__init__(obj.branch_merge_proposal)


class CodeReviewVoteReferenceEdit(ForwardedAuthorization):
    permission = 'launchpad.Edit'
    usedfor = ICodeReviewVoteReference

    def __init__(self, obj):
        super(CodeReviewVoteReferenceEdit, self).__init__(
            obj.branch_merge_proposal.target_branch)
        self.obj = obj

    def checkAuthenticated(self, user):
        """Only the affected teams may change the review request.

        The registrant may reassign the request to another entity.
        A member of the review team may assign it to themselves.
        A person to whom it is assigned may delegate it to someone else.

        Anyone with edit permissions on the target branch of the merge
        proposal can also edit the reviews.
        """
        return (user.inTeam(self.obj.reviewer) or
                user.inTeam(self.obj.registrant) or
                super(CodeReviewVoteReferenceEdit, self).checkAuthenticated(
                    user))


class CodeReviewCommentView(ForwardedAuthorization):
    permission = 'launchpad.View'
    usedfor = ICodeReviewComment

    def __init__(self, obj):
        super(CodeReviewCommentView, self).__init__(
            obj.branch_merge_proposal)


class CodeReviewCommentDelete(ForwardedAuthorization):
    permission = 'launchpad.Edit'
    usedfor = ICodeReviewCommentDeletion

    def __init__(self, obj):
        super(CodeReviewCommentDelete, self).__init__(
            obj.branch_merge_proposal)


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
        return (user.inTeam(self.obj.registrant) or
                user.inTeam(self.obj.source_branch.owner) or
                self.forwardCheckAuthenticated(
                    user, self.obj.target_branch) or
                user.inTeam(self.obj.target_branch.reviewer))


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
        return (user.inTeam(self.obj.person) or
                user.inTeam(self.obj.registrant) or
                user.in_admin)


class AdminDistroSeriesLanguagePacks(
    OnlyRosettaExpertsAndAdmins,
    EditDistroSeriesByReleaseManagerOrDistroOwnersOrAdmins):
    permission = 'launchpad.LanguagePacksAdmin'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistroSeries` language packs?

        Any Launchpad/Launchpad Translations administrator, people allowed to
        edit distroseries or members of IDistribution.language_pack_admin team
        are able to change the language packs available.
        """
        EditDS = EditDistroSeriesByReleaseManagerOrDistroOwnersOrAdmins
        return (
            OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
            EditDS.checkAuthenticated(self, user) or
            user.inTeam(self.obj.distribution.language_pack_admin))


class AdminLanguagePack(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.LanguagePacksAdmin'
    usedfor = ILanguagePack


class ViewHWSubmission(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IHWSubmission

    def checkAuthenticated(self, user):
        """Can the user view the submission details?

        Submissions that are not marked private are publicly visible,
        private submissions may only be accessed by their owner and by
        admins.
        """
        if not self.obj.private:
            return True

        return user.inTeam(self.obj.owner) or user.in_admin

    def checkUnauthenticated(self):
        return not self.obj.private


class EditHWSubmission(AdminByAdminsTeam):
    permission = 'launchpad.Edit'
    usedfor = IHWSubmission


class ViewHWDBBase(AuthorizationBase):
    """Base class to restrict access to HWDB data to members of the HWDB team.
    """
    permission = 'launchpad.View'

    def checkAuthenticated(self, user):
        """We give for now access only to Canonical employees."""
        return user.in_hwdb_team

    def checkUnauthenticated(self):
        """No access for anonymous users."""
        return False


class ViewHWDriver(ViewHWDBBase):
    usedfor = IHWDriver


class ViewHWDriverName(ViewHWDBBase):
    usedfor = IHWDriverName


class ViewHWDriverPackageName(ViewHWDBBase):
    usedfor = IHWDriverPackageName


class ViewHWVendorID(ViewHWDBBase):
    usedfor = IHWVendorID


class ViewHWDevice(ViewHWDBBase):
    usedfor = IHWDevice


class ViewHWSubmissionDevice(ViewHWDBBase):
    usedfor = IHWSubmissionDevice


class ViewHWDBApplication(ViewHWDBBase):
    usedfor = IHWDBApplication


class ViewHWDeviceClass(ViewHWDBBase):
    usedfor = IHWDeviceClass


class ViewArchive(AuthorizationBase):
    """Restrict viewing of private archives.

    Only admins or members of a private team can view the archive.
    """
    permission = 'launchpad.View'
    usedfor = IArchive

    def checkAuthenticated(self, user):
        """Verify that the user can view the archive.

        Anyone can see a public and enabled archive.

        Only Launchpad admins and uploaders can view private or disabled
        archives.
        """
        # No further checks are required if the archive is public and
        # enabled.
        if not self.obj.private and self.obj.enabled:
            return True

        # Administrator are allowed to view private archives.
        if user.in_admin or user.in_commercial_admin:
            return True

        # Owners can view the PPA.
        if user.inTeam(self.obj.owner):
            return True

        # Uploaders can view private PPAs.
        if self.obj.is_ppa and self.obj.checkArchivePermission(user.person):
            return True

        # Subscribers can view private PPAs.
        if self.obj.is_ppa and self.obj.private:
            archive_subs = getUtility(IArchiveSubscriberSet).getBySubscriber(
                user.person, self.obj).any()
            if archive_subs:
                return True

        # The software center agent can view commercial archives
        if self.obj.commercial:
            return user.in_software_center_agent

        return False

    def checkUnauthenticated(self):
        """Unauthenticated users can see the PPA if it's not private."""
        return not self.obj.private and self.obj.enabled


class EditArchive(AuthorizationBase):
    """Restrict archive editing operations.

    If the archive a primary archive then we check the user is in the
    distribution's owning team, otherwise we check the archive owner.
    """
    permission = 'launchpad.Edit'
    usedfor = IArchive

    def checkAuthenticated(self, user):
        if self.obj.is_main:
            return user.isOwner(self.obj.distribution) or user.in_admin

        return user.isOwner(self.obj) or user.in_admin


class AppendArchive(AuthorizationBase):
    """Restrict appending (upload and copy) operations on archives.

    No one can upload to disabled archives.

    PPA upload rights are managed via `IArchive.checkArchivePermission`;

    Appending to PRIMARY, PARTNER or COPY archives is restricted to owners.

    Appending to ubuntu main archives can also be done by the
    'ubuntu-security' celebrity.
    """
    permission = 'launchpad.Append'
    usedfor = IArchive

    def checkAuthenticated(self, user):
        if not self.obj.enabled:
            return False

        if user.inTeam(self.obj.owner):
            return True

        if self.obj.is_ppa and self.obj.checkArchivePermission(user.person):
            return True

        celebrities = getUtility(ILaunchpadCelebrities)
        if (self.obj.is_main and
            self.obj.distribution == celebrities.ubuntu and
            user.in_ubuntu_security):
            return True

        # The software center agent can change commercial archives
        if self.obj.commercial:
            return user.in_software_center_agent

        return False


class ViewArchiveAuthToken(AuthorizationBase):
    """Restrict viewing of archive tokens.

    The user just needs to be mentioned in the token, have append privilege
    to the archive or be an admin.
    """
    permission = "launchpad.View"
    usedfor = IArchiveAuthToken

    def checkAuthenticated(self, user):
        if user.person == self.obj.person:
            return True
        auth_edit = EditArchiveAuthToken(self.obj)
        return auth_edit.checkAuthenticated(user)


class EditArchiveAuthToken(ForwardedAuthorization):
    """Restrict editing of archive tokens.

    The user should have append privileges to the context archive, or be an
    admin.
    """
    permission = "launchpad.Edit"
    usedfor = IArchiveAuthToken

    def __init__(self, obj):
        super(EditArchiveAuthToken, self).__init__(
            obj.archive, 'launchpad.Append')

    def checkAuthenticated(self, user):
        return (user.in_admin or
                super(EditArchiveAuthToken, self).checkAuthenticated(user))


class ViewPersonalArchiveSubscription(ForwardedAuthorization):
    """Restrict viewing of personal archive subscriptions (non-db class).

    The user should be the subscriber, have append privilege to the archive
    or be an admin.
    """
    permission = "launchpad.View"
    usedfor = IPersonalArchiveSubscription

    def __init__(self, obj):
        super(ViewPersonalArchiveSubscription, self).__init__(
            obj.archive, 'launchpad.Append')
        self.obj = obj

    def checkAuthenticated(self, user):
        if user.person == self.obj.subscriber or user.in_admin:
            return True
        return super(
            ViewPersonalArchiveSubscription, self).checkAuthenticated(user)


class ViewArchiveSubscriber(ForwardedAuthorization):
    """Restrict viewing of archive subscribers.

    The user should be the subscriber, have append privilege to the
    archive or be an admin.
    """
    permission = "launchpad.View"
    usedfor = IArchiveSubscriber

    def __init__(self, obj):
        super(ViewArchiveSubscriber, self).__init__(
            obj, 'launchpad.Edit')
        self.obj = obj

    def checkAuthenticated(self, user):
        return (user.inTeam(self.obj.subscriber) or
                super(ViewArchiveSubscriber, self).checkAuthenticated(user))


class EditArchiveSubscriber(ForwardedAuthorization):
    """Restrict editing of archive subscribers.

    The user should have append privilege to the archive or be an admin.
    """
    permission = "launchpad.Edit"
    usedfor = IArchiveSubscriber

    def __init__(self, obj):
        super(EditArchiveSubscriber, self).__init__(
            obj.archive, 'launchpad.Append')

    def checkAuthenticated(self, user):
        return (user.in_admin or
                super(EditArchiveSubscriber, self).checkAuthenticated(user))


class DerivedAuthorization(AuthorizationBase):
    """An Authorization that is based on permissions for other objects.

    Implementations must define permission, usedfor and iter_objects.
    iter_objects should iterate through the objects to check permission on.

    Failure on the permission check for any object causes an overall failure.
    """

    def iter_adapters(self):
        return (
            getAdapter(obj, IAuthorization, self.permission)
            for obj in self.iter_objects())

    def checkAuthenticated(self, user):
        for adapter in self.iter_adapters():
            if not adapter.checkAuthenticated(user):
                return False
        return True

    def checkUnauthenticated(self):
        for adapter in self.iter_adapters():
            if not adapter.checkUnauthenticated():
                return False
        return True


class ViewSourcePackageRecipe(DerivedAuthorization):

    permission = "launchpad.View"
    usedfor = ISourcePackageRecipe

    def iter_objects(self):
        return self.obj.getReferencedBranches()


class ViewSourcePackageRecipeBuild(DerivedAuthorization):

    permission = "launchpad.View"
    usedfor = ISourcePackageRecipeBuild

    def iter_objects(self):
        if self.obj.recipe is not None:
            yield self.obj.recipe
        yield self.obj.archive


class ViewSourcePackagePublishingHistory(ViewArchive):
    """Restrict viewing of source publications."""
    permission = "launchpad.View"
    usedfor = ISourcePackagePublishingHistory

    def __init__(self, obj):
        super(ViewSourcePackagePublishingHistory, self).__init__(obj.archive)


class EditPublishing(ForwardedAuthorization):
    """Restrict editing of source and binary packages.."""
    permission = "launchpad.Edit"
    usedfor = IPublishingEdit

    def __init__(self, obj):
        super(EditPublishing, self).__init__(obj.archive, 'launchpad.Append')


class ViewBinaryPackagePublishingHistory(ViewSourcePackagePublishingHistory):
    """Restrict viewing of binary publications."""
    usedfor = IBinaryPackagePublishingHistory


class ViewBinaryPackageReleaseDownloadCount(
    ViewSourcePackagePublishingHistory):
    """Restrict viewing of binary package download counts."""
    usedfor = IBinaryPackageReleaseDownloadCount


class ViewSourcePackageRelease(AuthorizationBase):
    """Restrict viewing of source packages.

    Packages that are only published in private archives are subject to the
    same viewing rules as the archive (see class ViewArchive).

    If the package is published in any non-private archive, then it is
    automatically viewable even if the package is also published in
    a private archive.
    """
    permission = 'launchpad.View'
    usedfor = ISourcePackageRelease

    def checkAuthenticated(self, user):
        """Verify that the user can view the sourcepackagerelease."""
        for archive in self.obj.published_archives:
            adapter = getAdapter(archive, IAuthorization, self.permission)
            if adapter.checkAuthenticated(user):
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


class ViewEmailAddress(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IEmailAddress

    def checkUnauthenticated(self):
        """See `AuthorizationBase`."""
        # Anonymous users can never see email addresses.
        return False

    def checkAccountAuthenticated(self, account):
        """Can the user see the details of this email address?

        If the email address' owner doesn't want his email addresses to be
        hidden, anyone can see them.  Otherwise only the owner himself or
        admins can see them.
        """
        # Always allow users to see their own email addresses.
        if self.obj.account == account:
            return True

        if not (self.obj.person is None or
                self.obj.person.hide_email_addresses):
            return True

        user = IPersonRoles(IPerson(account, None), None)
        if user is None:
            return False

        return (self.obj.person is not None and user.inTeam(self.obj.person)
                or user.in_commercial_admin
                or user.in_registry_experts
                or user.in_admin)


class EditEmailAddress(EditByOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IEmailAddress

    def checkAccountAuthenticated(self, account):
        # Always allow users to see their own email addresses.
        if self.obj.account == account:
            return True
        return super(EditEmailAddress, self).checkAccountAuthenticated(
            account)


class ViewGPGKey(AnonymousAuthorization):
    usedfor = IGPGKey


class ViewIrcID(AnonymousAuthorization):
    usedfor = IIrcID


class ViewWikiName(AnonymousAuthorization):
    usedfor = IWikiName


class ViewPackageset(AnonymousAuthorization):
    """Anyone can view an IPackageset."""
    usedfor = IPackageset


class EditPackageset(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPackageset

    def checkAuthenticated(self, user):
        """The owner of a package set can edit the object."""
        return user.isOwner(self.obj) or user.in_admin


class EditPackagesetSet(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPackagesetSet

    def checkAuthenticated(self, user):
        """Users must be an admin or a member of the tech board."""
        return user.in_admin or user.in_ubuntu_techboard


class EditLibraryFileAliasWithParent(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ILibraryFileAliasWithParent

    def checkAuthenticated(self, user):
        """Only persons which can edit an LFA's parent can edit an LFA.

        By default, a LibraryFileAlias does not know about its parent.
        Such aliases are never editable. Use an adapter to provide a
        parent object.

        If a parent is known, users which can edit the parent can also
        edit properties of the LibraryFileAlias.
        """
        parent = getattr(self.obj, '__parent__', None)
        if parent is None:
            return False
        return self.forwardCheckAuthenticated(user, parent)


class ViewLibraryFileAliasWithParent(AuthorizationBase):
    """Authorization class for viewing LibraryFileAliass having a parent."""

    permission = 'launchpad.View'
    usedfor = ILibraryFileAliasWithParent

    def checkAuthenticated(self, user):
        """Only persons which can edit an LFA's parent can edit an LFA.

        By default, a LibraryFileAlias does not know about its parent.

        If a parent is known, users which can view the parent can also
        view the LibraryFileAlias.
        """
        parent = getattr(self.obj, '__parent__', None)
        if parent is None:
            return False
        return self.forwardCheckAuthenticated(user, parent)


class SetMessageVisibility(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IMessage

    def checkAuthenticated(self, user):
        """Admins and registry admins can set bug comment visibility."""
        return (user.in_admin or user.in_registry_experts)


class ViewPublisherConfig(AdminByAdminsTeam):
    usedfor = IPublisherConfig


class EditSourcePackage(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ISourcePackage

    def checkAuthenticated(self, user):
        """Anyone who can upload a package can edit it."""
        if user.in_admin:
            return True

        distribution = self.obj.distribution
        if user.inTeam(distribution.owner):
            return True

        # We use verifyUpload() instead of checkUpload() because
        # we don't have a pocket.
        # It returns the reason the user can't upload
        # or None if they are allowed.
        reason = distribution.main_archive.verifyUpload(
            user.person, distroseries=self.obj.distroseries,
            sourcepackagename=self.obj.sourcepackagename,
            component=None, strict_component=False)
        return reason is None
