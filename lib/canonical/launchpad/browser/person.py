# Copyright 2004-2007 Canonical Ltd

"""Person-related wiew classes."""

__metaclass__ = type

__all__ = [
    'BaseListView',
    'BeginTeamClaimView',
    'BugContactPackageBugsSearchListingView',
    'FOAFSearchView',
    'PeopleListView',
    'PersonAddView',
    'PersonAnswerContactForView',
    'PersonAnswersMenu',
    'PersonAssignedBugTaskSearchListingView',
    'PersonBranchesMenu',
    'PersonBranchesView',
    'PersonBrandingView',
    'PersonBugsMenu',
    'PersonChangePasswordView',
    'PersonClaimView',
    'PersonCodeOfConductEditView',
    'PersonCommentedBugTaskSearchListingView',
    'PersonDeactivateAccountView',
    'PersonDynMenu',
    'PersonEditEmailsView',
    'PersonEditHomePageView',
    'PersonEditIRCNicknamesView',
    'PersonEditJabberIDsView',
    'PersonEditSSHKeysView',
    'PersonEditView',
    'PersonEditWikiNamesView',
    'PersonFacets',
    'PersonGPGView',
    'PersonIndexView',
    'PersonLanguagesView',
    'PersonLatestQuestionsView',
    'PersonNavigation',
    'PersonOAuthTokensView',
    'PersonOverviewMenu',
    'PersonOwnedBranchesView',
    'PersonRdfView',
    'PersonRegisteredBranchesView',
    'PersonRelatedBugsView',
    'PersonRelatedProjectsView',
    'PersonSearchQuestionsView',
    'PersonSetContextMenu',
    'PersonSetFacets',
    'PersonSetNavigation',
    'PersonSetSOP',
    'PersonSOP',
    'PersonSpecFeedbackView',
    'PersonSpecsMenu',
    'PersonSpecWorkLoadView',
    'PersonSubscribedBranchesView',
    'PersonTeamBranchesView',
    'PersonTranslationView',
    'PersonView',
    'RedirectToEditLanguagesView',
    'ReportedBugTaskSearchListingView',
    'RestrictedMembershipsPersonView',
    'SearchAnsweredQuestionsView',
    'SearchAssignedQuestionsView',
    'SearchCommentedQuestionsView',
    'SearchCreatedQuestionsView',
    'SearchNeedAttentionQuestionsView',
    'SearchSubscribedQuestionsView',
    'SubscribedBugTaskSearchListingView',
    'TeamAddMyTeamsView',
    'TeamJoinView',
    'TeamLeaveView',
    'TeamListView',
    'TeamNavigation',
    'TeamOverviewMenu',
    'TeamReassignmentView',
    'TeamSpecsMenu',
    'UbunteroListView',
    ]

import cgi
import copy
from datetime import datetime, timedelta
from operator import attrgetter, itemgetter
import pytz
import urllib

from zope.app.form.browser import SelectWidget, TextAreaWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.formlib.form import FormFields
from zope.interface import implements, Interface
from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.schema import Choice, List, Text, TextLine
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.security.interfaces import Unauthorized

from canonical.config import config
from canonical.database.sqlbase import flush_database_updates

from canonical.widgets import (
    LaunchpadRadioWidget, LaunchpadRadioWidgetWithDescription,
    PasswordChangeWidget)
from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget

from canonical.cachedproperty import cachedproperty

from canonical.launchpad.interfaces import (
    AccountStatus, BranchListingSort, BugTaskSearchParams,
    BugTaskStatus, CannotUnsubscribe,
    DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT, EmailAddressStatus,
    GPGKeyNotFoundError, IBranchSet, ICountry, IEmailAddress,
    IEmailAddressSet, IGPGHandler, IGPGKeySet, IIrcIDSet,
    IJabberIDSet, ILanguageSet, ILaunchBag, ILoginTokenSet,
    IMailingListSet, INewPerson, IOAuthConsumerSet, IOpenLaunchBag,
    IPOTemplateSet, IPasswordEncryptor, IPerson,
    IPersonChangePassword, IPersonClaim, IPersonSet, IPollSet,
    IPollSubset, IRequestPreferredLanguages, ISSHKeySet,
    ISignedCodeOfConductSet, ITeam, ITeamMembership,
    ITeamMembershipSet, ITeamReassignment, IWikiNameSet,
    LoginTokenType, MailingListAutoSubscribePolicy,
    NotFoundError, PersonCreationRationale,
    PersonVisibility, QuestionParticipation, SSHKeyType,
    SpecificationFilter, TeamMembershipRenewalPolicy,
    TeamMembershipStatus, TeamSubscriptionPolicy, UBUNTU_WIKI_URL,
    UNRESOLVED_BUGTASK_STATUSES, UnexpectedFormData)

from canonical.launchpad.browser.bugtask import (
    BugListingBatchNavigator, BugTaskSearchListingView)
from canonical.launchpad.browser.branchlisting import BranchListingView
from canonical.launchpad.browser.feeds import FeedsMixin
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.browser.objectreassignment import (
    ObjectReassignmentView)
from canonical.launchpad.browser.openiddiscovery import (
    OpenIDPersistentIdentity, XRDSContentNegotiationMixin)
from canonical.launchpad.browser.specificationtarget import (
    HasSpecificationsView)
from canonical.launchpad.browser.branding import BrandingChangeView
from canonical.launchpad.browser.questiontarget import SearchQuestionsView

from canonical.launchpad.helpers import convertToHtmlCode, obfuscateEmail

from canonical.launchpad.validators.email import valid_email

from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.dynmenu import DynMenu, neverempty
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.login import logoutPerson
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.webapp import (
    ApplicationMenu, ContextMenu, LaunchpadEditFormView, LaunchpadFormView,
    Link, Navigation, StandardLaunchpadFacets, action, canonical_url,
    custom_widget, enabled_with_permission, smartquote, stepthrough, stepto)

from canonical.launchpad import _


class RestrictedMembershipsPersonView(LaunchpadView):
    """Secure access to team membership information for a person.

    This class checks that the logged-in user has access to view
    all the teams that these attributes and functions return.
    """

    def getLatestApprovedMembershipsForPerson(self):
        """Returns a list of teams the person has recently joined.

        Private teams are filtered out if the user is not a member of them.
        """
        # This method returns a list as opposed to the database object's
        # getLatestApprovedMembershipsForPerson which returns a sqlobject
        # result set.
        membership_list = self.context.getLatestApprovedMembershipsForPerson()
        return [membership for membership in membership_list
                if check_permission('launchpad.View', membership.team)]

    @property
    def teams_with_icons(self):
        """Returns list of teams with custom icons.

        These are teams that the person is an active member of.
        Private teams are filtered out if the user is not a member of them.
        """
        # This method returns a list as opposed to the database object's
        # teams_with_icons which returns a sqlobject
        # result set.
        return [team for team in self.context.teams_with_icons
                if check_permission('launchpad.View', team)]

    @property
    def administrated_teams(self):
        """Return the list of teams administrated by the person.

        The user must be an administrator of the team, and the team must
        be public.
        """
        return [team for team in self.context.getAdministratedTeams()
                if team.visibility == PersonVisibility.PUBLIC]

    def userCanViewMembership(self):
        """Return true if the user can view a team's membership.

        Only launchpad admins and team members can view the private
        membership. Anyone can view a public team's membership.
        """
        return check_permission('launchpad.View', self.context)


class BranchTraversalMixin:
    """Branch of this person or team for the specified product and
    branch names.

    For example:

    * '/~ddaa/bazaar/devel' points to the branch whose owner
    name is 'ddaa', whose product name is 'bazaar', and whose branch name
    is 'devel'.

    * '/~sabdfl/+junk/junkcode' points to the branch whose
    owner name is 'sabdfl', with no associated product, and whose branch
    name is 'junkcode'.

    * '/~ddaa/+branch/bazaar/devel' redirects to '/~ddaa/bazaar/devel'

    """

    @stepto('+branch')
    def redirect_branch(self):
        """Redirect to canonical_url, which is ~user/product/name."""
        stepstogo = self.request.stepstogo
        product_name = stepstogo.consume()
        branch_name = stepstogo.consume()
        if product_name is not None and branch_name is not None:
            branch = self.context.getBranch(product_name, branch_name)
            if branch:
                return self.redirectSubTree(canonical_url(branch))
        raise NotFoundError

    def traverse(self, product_name):
        branch_name = self.request.stepstogo.consume()
        if branch_name is not None:
            branch = self.context.getBranch(product_name, branch_name)
            if branch is not None and branch.product is not None:
                # The launch bag contains "stuff of interest" related to where
                # the user is traversing to.  When a user traverses over a
                # product, the product gets added to the launch bag by the
                # traversal machinery, however when traversing to a branch, we
                # short circuit it somewhat by looking for a two part key (in
                # addition to the user) to identify the branch, and as such
                # the product isnt't being added to the bag by the internals.
                getUtility(IOpenLaunchBag).add(branch.product)
            return branch
        else:
            return super(BranchTraversalMixin, self).traverse(product_name)


class PersonNavigation(BranchTraversalMixin, Navigation):

    usedfor = IPerson

    def breadcrumb(self):
        return self.context.displayname

    @stepthrough('+expiringmembership')
    def traverse_expiring_membership(self, name):
        # Return the found membership regardless of its status as we know
        # TeamMembershipSelfRenewalView will tell users why the memembership
        # can't be renewed when necessary.
        membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.context, getUtility(IPersonSet).getByName(name))
        if membership is None:
            return None
        return TeamMembershipSelfRenewalView(membership, self.request)

    @stepto('+archive')
    def traverse_archive(self):
        return self.context.archive


class PersonDynMenu(DynMenu):

    menus = {
        'contributions': 'contributionsMenu',
        }

    @neverempty
    def contributionsMenu(self):
        L = [self.makeBreadcrumbLink(item)
             for item in self.context.iterTopProjectsContributedTo()]
        L.sort(key=lambda item: item.text.lower())
        if L:
            for obj in L:
                yield obj
        else:
            yield self.makeLink(
                'Projects you contribute to go here.', target=None)
        yield self.makeLink('See all projects...', target='/products')


class TeamNavigation(PersonNavigation):

    usedfor = ITeam

    def breadcrumb(self):
        return smartquote('"%s" team') % self.context.displayname

    @stepthrough('+poll')
    def traverse_poll(self, name):
        return getUtility(IPollSet).getByTeamAndName(self.context, name)

    @stepthrough('+invitation')
    def traverse_invitation(self, name):
        # Return the found membership regardless of its status as we know
        # TeamInvitationView can handle memberships in statuses other than
        # INVITED.
        membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.context, getUtility(IPersonSet).getByName(name))
        if membership is None:
            return None
        return TeamInvitationView(membership, self.request)

    @stepthrough('+member')
    def traverse_member(self, name):
        person = getUtility(IPersonSet).getByName(name)
        if person is None:
            return None
        return getUtility(ITeamMembershipSet).getByPersonAndTeam(
            person, self.context)


class TeamMembershipSelfRenewalView(LaunchpadFormView):

    implements(IBrowserPublisher)

    schema = ITeamMembership
    field_names = []
    label = 'Renew team membership'
    template = ViewPageTemplateFile(
        '../templates/teammembership-self-renewal.pt')

    def __init__(self, context, request):
        # Only the member himself or admins of the member (in case it's a
        # team) can see the page in which they renew memberships that are
        # about to expire.
        if not check_permission('launchpad.Edit', context.person):
            raise Unauthorized(
                "Only the member himself can renew his memberships.")
        LaunchpadFormView.__init__(self, context, request)

    def browserDefault(self, request):
        return self, ()

    def getReasonForDeniedRenewal(self):
        """Return text describing why the membership can't be renewed."""
        context = self.context
        ondemand = TeamMembershipRenewalPolicy.ONDEMAND
        admin = TeamMembershipStatus.ADMIN
        approved = TeamMembershipStatus.APPROVED
        date_limit = datetime.now(pytz.timezone('UTC')) - timedelta(
            days=DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT)
        if context.status not in (admin, approved):
            text = "it is not active."
        elif context.team.renewal_policy != ondemand:
            text = ('<a href="%s">%s</a> is not a team which accepts its '
                    'members to renew their own memberships.'
                    % (canonical_url(context.team),
                       context.team.unique_displayname))
        elif context.dateexpires is None or context.dateexpires > date_limit:
            if context.person.isTeam():
                link_text = "Somebody else has already renewed it."
            else:
                link_text = (
                    "You or one of the team administrators has already "
                    "renewed it.")
            text = ('it is not set to expire in %d days or less. '
                    '<a href="%s/+members">%s</a>'
                    % (DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT,
                       canonical_url(context.team), link_text))
        else:
            raise AssertionError('This membership can be renewed!')
        return text

    @property
    def time_before_expiration(self):
        return self.context.dateexpires - datetime.now(pytz.timezone('UTC'))

    @property
    def next_url(self):
        return canonical_url(self.context.person)

    @action(_("Renew"), name="renew")
    def renew_action(self, action, data):
        member = self.context.person
        member.renewTeamMembership(self.context.team)
        self.request.response.addInfoNotification(
            _("Membership renewed until ${date}.", mapping=dict(
                    date=self.context.dateexpires.strftime('%Y-%m-%d'))))

    @action(_("Let it Expire"), name="nothing")
    def do_nothing_action(self, action, data):
        # Redirect back and wait for the membership to expire automatically.
        pass


class ITeamMembershipInvitationAcknowledgementForm(Interface):
    """Schema for the form in which team admins acknowledge invitations.

    We could use ITeamMembership for that, but the acknowledger_comment is
    marked readonly there and that means LaunchpadFormView won't include the
    value of that in the data given to our action handler.
    """

    acknowledger_comment = Text(
        title=_("Comment"), required=False, readonly=False)


class TeamInvitationView(LaunchpadFormView):
    """Where team admins can accept/decline membership invitations."""

    implements(IBrowserPublisher)

    schema = ITeamMembershipInvitationAcknowledgementForm
    label = 'Team membership invitation'
    field_names = ['acknowledger_comment']
    custom_widget('acknowledger_comment', TextAreaWidget, height=5, width=60)
    template = ViewPageTemplateFile(
        '../templates/teammembership-invitation.pt')

    def __init__(self, context, request):
        # Only admins of the invited team can see the page in which they
        # approve/decline invitations.
        if not check_permission('launchpad.Edit', context.person):
            raise Unauthorized(
                "Only team administrators can approve/decline invitations "
                "sent to this team.")
        LaunchpadFormView.__init__(self, context, request)

    def browserDefault(self, request):
        return self, ()

    @property
    def next_url(self):
        return canonical_url(self.context.person)

    @action(_("Accept"), name="accept")
    def accept_action(self, action, data):
        if self.context.status != TeamMembershipStatus.INVITED:
            self.request.response.addInfoNotification(
                _("This invitation has already been processed."))
            return
        member = self.context.person
        member.acceptInvitationToBeMemberOf(
            self.context.team, data['acknowledger_comment'])
        self.request.response.addInfoNotification(
            _("This team is now a member of ${team}", mapping=dict(
                  team=self.context.team.browsername)))

    @action(_("Decline"), name="decline")
    def decline_action(self, action, data):
        if self.context.status != TeamMembershipStatus.INVITED:
            self.request.response.addInfoNotification(
                _("This invitation has already been processed."))
            return
        member = self.context.person
        member.declineInvitationToBeMemberOf(
            self.context.team, data['acknowledger_comment'])
        self.request.response.addInfoNotification(
            _("Declined the invitation to join ${team}", mapping=dict(
                  team=self.context.team.browsername)))

    @action(_("Cancel"), name="cancel")
    def cancel_action(self, action, data):
        # Simply redirect back.
        pass


class PersonSetNavigation(Navigation):

    usedfor = IPersonSet

    def breadcrumb(self):
        return 'People'

    def traverse(self, name):
        # Raise a 404 on an invalid Person name
        person = self.context.getByName(name)
        if person is None:
            raise NotFoundError(name)
        # Redirect to /~name
        return self.redirectSubTree(canonical_url(person))

    @stepto('+me')
    def me(self):
        me = getUtility(ILaunchBag).user
        if me is None:
            raise Unauthorized("You need to be logged in to view this URL.")
        return self.redirectSubTree(canonical_url(me), status=303)


class PersonSetSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return 'People and Teams'

    def listChildren(self, num):
        return []

    def listAltChildren(self, num):
        return None


class PersonSetFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for the IPersonSet."""

    usedfor = IPersonSet

    enable_only = ['overview']


class PersonSetContextMenu(ContextMenu):

    usedfor = IPersonSet

    links = ['products', 'distributions', 'people', 'meetings', 'peoplelist',
             'teamlist', 'ubunterolist', 'newteam', 'adminpeoplemerge',
             'adminteammerge', 'mergeaccounts']

    def products(self):
        return Link('/projects/', 'View projects')

    def distributions(self):
        return Link('/distros/', 'View distributions')

    def people(self):
        return Link('/people/', 'View people')

    def meetings(self):
        return Link('/sprints/', 'View meetings')

    def peoplelist(self):
        text = 'List all people'
        return Link('+peoplelist', text, icon='people')

    def teamlist(self):
        text = 'List all teams'
        return Link('+teamlist', text, icon='people')

    def ubunterolist(self):
        text = 'List all Ubunteros'
        return Link('+ubunterolist', text, icon='people')

    def newteam(self):
        text = 'Register a team'
        return Link('+newteam', text, icon='add')

    def mergeaccounts(self):
        text = 'Merge accounts'
        return Link('+requestmerge', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def adminpeoplemerge(self):
        text = 'Admin merge people'
        return Link('+adminpeoplemerge', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def adminteammerge(self):
        text = 'Admin merge teams'
        return Link('+adminteammerge', text, icon='edit')


class PersonSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return self.context.title

    def listChildren(self, num):
        return []

    def countChildren(self):
        return 0

    def listAltChildren(self, num):
        return None

    def countAltChildren(self):
        raise NotImplementedError


class PersonFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IPerson."""

    usedfor = IPerson

    enable_only = ['overview', 'bugs', 'answers', 'specifications',
                   'branches', 'translations']

    def overview(self):
        text = 'Overview'
        summary = 'General information about %s' % self.context.browsername
        return Link('', text, summary)

    def bugs(self):
        text = 'Bugs'
        summary = (
            'Bug reports that %s is involved with' % self.context.browsername)
        return Link('', text, summary)

    def specifications(self):
        text = 'Blueprints'
        summary = (
            'Feature specifications that %s is involved with' %
            self.context.browsername)
        return Link('', text, summary)

    def bounties(self):
        text = 'Bounties'
        browsername = self.context.browsername
        summary = (
            'Bounty offers that %s is involved with' % browsername)
        return Link('+bounties', text, summary)

    def branches(self):
        text = 'Code'
        summary = ('Bazaar Branches and revisions registered and authored '
                   'by %s' % self.context.browsername)
        return Link('', text, summary)

    def answers(self):
        text = 'Answers'
        summary = (
            'Questions that %s is involved with' % self.context.browsername)
        return Link('', text, summary)

    def translations(self):
        text = 'Translations'
        summary = (
            'Software that %s is involved in translating' %
            self.context.browsername)
        return Link('', text, summary)


class PersonBranchesMenu(ApplicationMenu):

    usedfor = IPerson
    facet = 'branches'
    links = ['all_related', 'registered', 'owned', 'subscribed', 'addbranch']

    def all_related(self):
        text = 'All related'
        return Link(canonical_url(self.context, rootsite='code'),
                    text, icon='branch')

    def owned(self):
        text = 'Owned'
        return Link('+ownedbranches', text, icon='branch')

    def registered(self):
        text = 'Registered'
        return Link('+registeredbranches', text, icon='branch')

    def subscribed(self):
        text = 'Subscribed'
        return Link('+subscribedbranches', text, icon='branch')

    def addbranch(self):
        if self.user is None:
            enabled = False
        else:
            enabled = self.user.inTeam(self.context)
        text = 'Register branch'
        return Link('+addbranch', text, icon='add', enabled=enabled)


class PersonBugsMenu(ApplicationMenu):

    usedfor = IPerson
    facet = 'bugs'
    links = ['assignedbugs', 'commentedbugs', 'reportedbugs',
             'subscribedbugs', 'relatedbugs', 'softwarebugs', 'mentoring']

    def relatedbugs(self):
        text = 'List all related bugs'
        summary = ('Lists all bug reports which %s reported, is assigned to, '
                   'or is subscribed to.' % self.context.displayname)
        return Link('', text, summary=summary)

    def assignedbugs(self):
        text = 'List assigned bugs'
        summary = 'Lists bugs assigned to %s.' % self.context.displayname
        return Link('+assignedbugs', text, summary=summary)

    def softwarebugs(self):
        text = 'Show package report'
        summary = (
            'A summary report for packages where %s is a bug supervisor.'
            % self.context.displayname)
        return Link('+packagebugs', text, summary=summary)

    def reportedbugs(self):
        text = 'List reported bugs'
        summary = 'Lists bugs reported by %s.' % self.context.displayname
        return Link('+reportedbugs', text, summary=summary)

    def subscribedbugs(self):
        text = 'List subscribed bugs'
        summary = ('Lists bug reports %s is subscribed to.'
                   % self.context.displayname)
        return Link('+subscribedbugs', text, summary=summary)

    def mentoring(self):
        text = 'Mentoring offered'
        summary = ('Lists bugs for which %s has offered to mentor someone.'
                   % self.context.displayname)
        enabled = self.context.mentoring_offers
        return Link('+mentoring', text, enabled=enabled, summary=summary)

    def commentedbugs(self):
        text = 'List commented bugs'
        summary = ('Lists bug reports on which %s has commented.'
                   % self.context.displayname)
        return Link('+commentedbugs', text, summary=summary)


class PersonSpecsMenu(ApplicationMenu):

    usedfor = IPerson
    facet = 'specifications'
    links = ['assignee', 'drafter', 'approver',
             'subscriber', 'registrant', 'feedback',
             'workload', 'mentoring', 'roadmap']

    def registrant(self):
        text = 'Registrant'
        summary = 'List specs registered by %s' % self.context.browsername
        return Link('+specs?role=registrant', text, summary, icon='spec')

    def approver(self):
        text = 'Approver'
        summary = 'List specs with %s is supposed to approve' % (
            self.context.browsername)
        return Link('+specs?role=approver', text, summary, icon='spec')

    def assignee(self):
        text = 'Assignee'
        summary = 'List specs for which %s is the assignee' % (
            self.context.browsername)
        return Link('+specs?role=assignee', text, summary, icon='spec')

    def drafter(self):
        text = 'Drafter'
        summary = 'List specs drafted by %s' % self.context.browsername
        return Link('+specs?role=drafter', text, summary, icon='spec')

    def subscriber(self):
        text = 'Subscriber'
        return Link('+specs?role=subscriber', text, icon='spec')

    def feedback(self):
        text = 'Feedback requests'
        summary = 'List specs where feedback has been requested from %s' % (
            self.context.browsername)
        return Link('+specfeedback', text, summary, icon='info')

    def mentoring(self):
        text = 'Mentoring offered'
        enabled = self.context.mentoring_offers
        return Link('+mentoring', text, enabled=enabled, icon='info')

    def workload(self):
        text = 'Workload'
        summary = 'Show all specification work assigned'
        return Link('+specworkload', text, summary, icon='info')

    def roadmap(self):
        text = 'Roadmap'
        summary = 'Show recommended sequence of feature implementation'
        return Link('+roadmap', text, summary, icon='info')


class PersonTranslationsMenu(ApplicationMenu):

    usedfor = IPerson
    facet = 'translations'
    links = ['imports']

    def imports(self):
        text = 'See import queue'
        return Link('+imports', text)


class TeamSpecsMenu(PersonSpecsMenu):

    usedfor = ITeam
    facet = 'specifications'

    def mentoring(self):
        target = '+mentoring'
        text = 'Mentoring offered'
        summary = 'Offers of mentorship for prospective team members'
        return Link(target, text, summary=summary, icon='info')


class TeamBugsMenu(PersonBugsMenu):

    usedfor = ITeam
    facet = 'bugs'
    links = ['assignedbugs', 'relatedbugs', 'softwarebugs', 'subscribedbugs',
             'mentorships']

    def mentorships(self):
        target = '+mentoring'
        text = 'Mentoring offered'
        summary = 'Offers of mentorship for prospective team members'
        return Link(target, text, summary=summary, icon='info')


class CommonMenuLinks:

    @enabled_with_permission('launchpad.Edit')
    def common_edithomepage(self):
        target = '+edithomepage'
        text = 'Change home page'
        return Link(target, text, icon='edit')

    def common_packages(self):
        target = '+packages'
        text = 'List assigned packages'
        summary = 'Packages assigned to %s' % self.context.browsername
        return Link(target, text, summary, icon='packages')

    def related_projects(self):
        target = '+projects'
        text = 'List related projects'
        summary = 'Projects %s is involved with' % self.context.browsername
        return Link(target, text, summary, icon='packages')

    @enabled_with_permission('launchpad.Edit')
    def activate_ppa(self):
        target = "+activate-ppa"
        text = 'Activate Personal Package Archive'
        summary = ('Acknowledge terms of service for Launchpad Personal '
                   'Package Archive.')
        enable_link = (self.context.archive is None)
        return Link(target, text, summary, icon='edit', enabled=enable_link)

    def show_ppa(self):
        target = '+archive'
        text = 'Personal Package Archive'
        summary = 'Browse Personal Package Archive packages.'
        enable_link = (self.context.archive is not None and
                       check_permission('launchpad.View',
                                        self.context.archive))
        return Link(target, text, summary, icon='info', enabled=enable_link)


class PersonOverviewMenu(ApplicationMenu, CommonMenuLinks):

    usedfor = IPerson
    facet = 'overview'
    links = ['edit', 'branding', 'common_edithomepage',
             'editemailaddresses', 'editlanguages', 'editwikinames',
             'editircnicknames', 'editjabberids', 'editpassword',
             'editsshkeys', 'editpgpkeys',
             'memberships', 'mentoringoffers',
             'codesofconduct', 'karma', 'common_packages', 'administer',
             'related_projects', 'activate_ppa', 'show_ppa']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        target = '+edit'
        text = 'Change details'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def branding(self):
        target = '+branding'
        text = 'Change branding'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def editlanguages(self):
        target = '+editlanguages'
        text = 'Set preferred languages'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def editemailaddresses(self):
        target = '+editemails'
        text = 'Change e-mail settings'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def editwikinames(self):
        target = '+editwikinames'
        text = 'Update wiki names'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def editircnicknames(self):
        target = '+editircnicknames'
        text = 'Update IRC nicknames'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def editjabberids(self):
        target = '+editjabberids'
        text = 'Update Jabber IDs'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def editpassword(self):
        target = '+changepassword'
        text = 'Change your password'
        return Link(target, text, icon='edit')

    def karma(self):
        target = '+karma'
        text = 'Show karma summary'
        summary = (
            u'%s\N{right single quotation mark}s activities '
            u'in Launchpad' % self.context.browsername)
        return Link(target, text, summary, icon='info')

    def memberships(self):
        target = '+participation'
        text = 'Show team participation'
        return Link(target, text, icon='info')

    def mentoringoffers(self):
        target = '+mentoring'
        text = 'Mentoring offered'
        enabled = self.context.mentoring_offers
        return Link(target, text, enabled=enabled, icon='info')

    @enabled_with_permission('launchpad.Edit')
    def editsshkeys(self):
        target = '+editsshkeys'
        text = 'Update SSH keys'
        summary = (
            'Used if %s stores code on the Supermirror' %
            self.context.browsername)
        return Link(target, text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def editpgpkeys(self):
        target = '+editpgpkeys'
        text = 'Update OpenPGP keys'
        summary = 'Used for the Supermirror, and when maintaining packages'
        return Link(target, text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def codesofconduct(self):
        target = '+codesofconduct'
        text = 'Codes of Conduct'
        summary = (
            'Agreements to abide by the rules of a distribution or project')
        return Link(target, text, summary, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        target = '+review'
        text = 'Administer'
        return Link(target, text, icon='edit')


class TeamOverviewMenu(ApplicationMenu, CommonMenuLinks):

    usedfor = ITeam
    facet = 'overview'
    links = ['edit', 'branding', 'common_edithomepage', 'members',
             'add_member', 'memberships', 'received_invitations', 'mugshots',
             'editemail', 'configure_mailing_list', 'editlanguages', 'polls',
             'add_poll', 'joinleave', 'add_my_teams', 'mentorships',
             'reassign', 'common_packages', 'related_projects',
             'activate_ppa', 'show_ppa']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        target = '+edit'
        text = 'Change details'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def branding(self):
        target = '+branding'
        text = 'Change branding'
        return Link(target, text, icon='edit')

    @enabled_with_permission('launchpad.Owner')
    def reassign(self):
        target = '+reassign'
        text = 'Change owner'
        summary = 'Change the owner of the team'
        # alt="(Change owner)"
        return Link(target, text, summary, icon='edit')

    @enabled_with_permission('launchpad.View')
    def members(self):
        target = '+members'
        text = 'Show all members'
        return Link(target, text, icon='people')

    @enabled_with_permission('launchpad.Edit')
    def received_invitations(self):
        target = '+invitations'
        text = 'Show received invitations'
        return Link(target, text, icon='info')

    @enabled_with_permission('launchpad.Edit')
    def add_member(self):
        target = '+addmember'
        text = 'Add member'
        return Link(target, text, icon='add')

    def add_my_teams(self):
        target = '+add-my-teams'
        text = 'Add one of my teams'
        return Link(target, text, icon='add')

    def memberships(self):
        target = '+participation'
        text = 'Show team participation'
        return Link(target, text, icon='info')

    def mentorships(self):
        target = '+mentoring'
        text = 'Mentoring available'
        enabled = self.context.team_mentorships
        summary = 'Offers of mentorship for prospective team members'
        return Link(target, text, summary=summary, enabled=enabled,
                    icon='info')

    @enabled_with_permission('launchpad.View')
    def mugshots(self):
        target = '+mugshots'
        text = 'Show group photo'
        return Link(target, text, icon='people')

    def polls(self):
        target = '+polls'
        text = 'Show polls'
        return Link(target, text, icon='info')

    @enabled_with_permission('launchpad.Edit')
    def add_poll(self):
        target = '+newpoll'
        text = 'Create a poll'
        return Link(target, text, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def editemail(self):
        target = '+contactaddress'
        text = 'Change contact address'
        summary = (
            'The address Launchpad uses to contact %s' %
            self.context.browsername)
        return Link(target, text, summary, icon='mail')

    @enabled_with_permission('launchpad.Edit')
    def configure_mailing_list(self):
        target = '+mailinglist'
        text = 'Configure mailing list'
        summary = (
            'The mailing list associated with %s' % self.context.browsername)
        return Link(target, text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def editlanguages(self):
        target = '+editlanguages'
        text = 'Set preferred languages'
        return Link(target, text, icon='edit')

    def joinleave(self):
        team = self.context
        enabled = True
        if userIsActiveTeamMember(team):
            target = '+leave'
            text = 'Leave the Team' # &#8230;
            icon = 'remove'
        else:
            if team.subscriptionpolicy == TeamSubscriptionPolicy.RESTRICTED:
                # This is a restricted team; users can't join.
                enabled = False
            target = '+join'
            text = 'Join the team' # &#8230;
            icon = 'add'
        return Link(target, text, icon=icon, enabled=enabled)


class BaseListView:

    header = ""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _getBatchNavigator(self, results):
        return BatchNavigator(results, self.request)

    def getTeamsList(self):
        results = getUtility(IPersonSet).getAllTeams()
        return self._getBatchNavigator(results)

    def getPeopleList(self):
        results = getUtility(IPersonSet).getAllPersons()
        return self._getBatchNavigator(results)

    def getUbunterosList(self):
        results = getUtility(IPersonSet).getUbunteros()
        return self._getBatchNavigator(results)


class PeopleListView(BaseListView):

    header = "People Launchpad knows about"

    def getList(self):
        return self.getPeopleList()


class TeamListView(BaseListView):

    header = "Teams registered in Launchpad"

    def getList(self):
        return self.getTeamsList()


class UbunteroListView(BaseListView):

    header = "Ubunteros registered in Launchpad"

    def getList(self):
        return self.getUbunterosList()


class FOAFSearchView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def teamsCount(self):
        return getUtility(IPersonSet).teamsCount()

    def peopleCount(self):
        return getUtility(IPersonSet).peopleCount()

    def topPeople(self):
        return getUtility(IPersonSet).topPeople()

    def searchPeopleBatchNavigator(self):
        name = self.request.get("name")

        if not name:
            return None

        searchfor = self.request.get("searchfor")
        if searchfor == "peopleonly":
            results = getUtility(IPersonSet).findPerson(name)
        elif searchfor == "teamsonly":
            results = getUtility(IPersonSet).findTeam(name)
        else:
            results = getUtility(IPersonSet).find(name)

        return BatchNavigator(results, self.request)


class PersonAddView(LaunchpadFormView):
    """The page where users can create new Launchpad profiles."""

    label = "Create a new Launchpad profile"
    schema = INewPerson
    custom_widget('creation_comment', TextAreaWidget, height=5, width=60)

    @action(_("Create Profile"), name="create")
    def create_action(self, action, data):
        emailaddress = data['emailaddress']
        displayname = data['displayname']
        creation_comment = data['creation_comment']
        person, ignored = getUtility(IPersonSet).createPersonAndEmail(
            emailaddress, PersonCreationRationale.USER_CREATED,
            displayname=displayname, comment=creation_comment,
            registrant=self.user)
        self.next_url = canonical_url(person)
        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(
            requester=self.user,
            requesteremail=self.user.preferredemail.email,
            email=emailaddress, tokentype=LoginTokenType.NEWPROFILE)
        token.sendProfileCreatedEmail(person, creation_comment)


class PersonDeactivateAccountView(LaunchpadFormView):

    schema = IPerson
    field_names = ['account_status_comment', 'password']
    label = "Deactivate your Launchpad account"
    custom_widget('account_status_comment', TextAreaWidget, height=5,
                  width=60)

    def validate(self, data):
        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(
            self.user.preferredemail.email)
        assert principal is not None, "User must be logged in at this point."
        if not principal.validate(data.get('password')):
            self.setFieldError('password', 'Incorrect password.')
            return

    @action(_("Deactivate My Account"), name="deactivate")
    def deactivate_action(self, action, data):
        self.context.deactivateAccount(data['account_status_comment'])
        logoutPerson(self.request)
        self.request.response.addNoticeNotification(
            _(u'Your account has been deactivated.'))
        self.next_url = self.request.getApplicationURL()


class PersonClaimView(LaunchpadFormView):
    """The page where a user can claim an unvalidated profile."""

    schema = IPersonClaim

    def initialize(self):
        if self.context.is_valid_person_or_team:
            # Valid teams and people aren't claimable. We pull the path
            # out of PATH_INFO to make sure that the exception looks
            # good for subclasses. We're that picky!
            name = self.request['PATH_INFO'].split("/")[-1]
            raise NotFound(self, name, request=self.request)
        LaunchpadFormView.initialize(self)

    def validate(self, data):
        emailaddress = data.get('emailaddress')
        if emailaddress is None:
            self.setFieldError(
                'emailaddress', 'Please enter the email address')
            return

        email = getUtility(IEmailAddressSet).getByEmail(emailaddress)
        error = ""
        if email is None:
            # Email not registered in launchpad, ask the user to try another
            # one.
            error = ("We couldn't find this email address. Please try "
                     "another one that could possibly be associated with "
                     "this profile. Note that this profile's name (%s) was "
                     "generated based on the email address it's "
                     "associated with."
                     % self.context.name)
        elif email.person != self.context:
            if email.person.is_valid_person:
                error = structured(
                         "This email address is associated with yet another "
                         "Launchpad profile, which you seem to have used at "
                         "some point. If that's the case, you can "
                         '<a href="/people/+requestmerge'
                         '?field.dupeaccount=%s">combine '
                         "this profile with the other one</a> (you'll "
                         "have to log in with the other profile first, "
                         "though). If that's not the case, please try with a "
                         "different email address.",
                         self.context.name)
            else:
                # There seems to be another unvalidated profile for you!
                error = structured(
                         "Although this email address is not associated with "
                         "this profile, it's associated with yet another "
                         'one. You can <a href="%s/+claim">claim that other '
                         'profile</a> and then later '
                         '<a href="/people/+requestmerge">combine</a> both '
                         'of them into a single one.',
                         canonical_url(email.person))
        else:
            # Yay! You got the right email this time.
            pass
        if error:
            self.setFieldError('emailaddress', error)

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action(_("E-mail Me"), name="confirm")
    def confirm_action(self, action, data):
        email = data['emailaddress']
        token = getUtility(ILoginTokenSet).new(
            requester=None, requesteremail=None, email=email,
            tokentype=LoginTokenType.PROFILECLAIM)
        token.sendClaimProfileEmail()
        self.request.response.addInfoNotification(_(
            "A confirmation  message has been sent to '${email}'. "
            "Follow the instructions in that message to finish claiming this "
            "profile. "
            "(If the message doesn't arrive in a few minutes, your mail "
            "provider might use 'greylisting', which could delay the message "
            "for up to an hour or two.)", mapping=dict(email=email)))


class BeginTeamClaimView(PersonClaimView):
    """Where you can claim an unvalidated profile turning it into a team.

    This is actually just the first step, where you enter the email address
    of the team and we email further instructions to that address.
    """

    @action(_("Continue"), name="confirm")
    def confirm_action(self, action, data):
        email = data['emailaddress']
        token = getUtility(ILoginTokenSet).new(
            requester=self.user, requesteremail=None, email=email,
            tokentype=LoginTokenType.TEAMCLAIM)
        token.sendClaimTeamEmail()
        self.request.response.addInfoNotification(_(
            "A confirmation message has been sent to '${email}'. "
            "Follow the instructions in that message to finish claiming this "
            "team. "
            "(If the above address is from a mailing list, it may be "
            "necessary to talk with one of its admins to accept the message "
            "from Launchpad so that you can finish the process.)",
            mapping=dict(email=email)))


class RedirectToEditLanguagesView(LaunchpadView):
    """Redirect the logged in user to his +editlanguages page.

    This view should always be registered with a launchpad.AnyPerson
    permission, to make sure the user is logged in. It exists so that
    we provide a link for non logged in users that will require them to login
    and them send them straight to the page they want to go.
    """

    def initialize(self):
        self.request.response.redirect(
            '%s/+editlanguages' % canonical_url(self.user))


class PersonRdfView:
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile(
        '../templates/person-foaf.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Render RDF output, and return it as a string encoded in UTF-8.

        Render the page template to produce RDF output.
        The return value is string data encoded in UTF-8.

        As a side-effect, HTTP headers are set for the mime type
        and filename for download."""
        self.request.response.setHeader('content-type',
                                        'application/rdf+xml')
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename=%s.rdf' %
                                            self.context.name)
        unicodedata = self.template()
        encodeddata = unicodedata.encode('utf-8')
        return encodeddata


def userIsActiveTeamMember(team):
    """Return True if the user is an active member of this team."""
    user = getUtility(ILaunchBag).user
    if user is None:
        return False
    if not check_permission('launchpad.View', team):
        return False
    return user in team.activemembers


class PersonSpecWorkLoadView(LaunchpadView):
    """View used to render the specification workload for a particular person.

    It shows the set of specifications with which this person has a role.
    """

    def initialize(self):
        assert IPerson.providedBy(self.context), (
            'PersonSpecWorkLoadView should be used only on an IPerson.')

    class PersonSpec:
        """One record from the workload list."""

        def __init__(self, spec, person):
            self.spec = spec
            self.assignee = spec.assignee == person
            self.drafter = spec.drafter == person
            self.approver = spec.approver == person

    @cachedproperty
    def workload(self):
        """This code is copied in large part from browser/sprint.py. It may
        be worthwhile refactoring this to use a common code base.

        Return a structure that lists the specs for which this person is the
        approver, the assignee or the drafter.
        """
        return [PersonSpecWorkLoadView.PersonSpec(spec, self.context)
                for spec in self.context.specifications()]


class PersonSpecFeedbackView(HasSpecificationsView):

    @cachedproperty
    def feedback_specs(self):
        filter = [SpecificationFilter.FEEDBACK]
        return self.context.specifications(filter=filter)


class ReportedBugTaskSearchListingView(BugTaskSearchListingView):
    """All bugs reported by someone."""

    columns_to_show = ["id", "summary", "bugtargetdisplayname",
                       "importance", "status"]

    def search(self):
        # Specify both owner and bug_reporter to try to prevent the same
        # bug (but different tasks) being displayed.
        return BugTaskSearchListingView.search(
            self,
            extra_params=dict(owner=self.context, bug_reporter=self.context))

    def getSearchPageHeading(self):
        """The header for the search page."""
        return "Bugs reported by %s" % self.context.displayname

    def getAdvancedSearchPageHeading(self):
        """The header for the advanced search page."""
        return "Bugs Reported by %s: Advanced Search" % (
            self.context.displayname)

    def getAdvancedSearchButtonLabel(self):
        """The Search button for the advanced search page."""
        return "Search bugs reported by %s" % self.context.displayname

    def getSimpleSearchURL(self):
        """Return a URL that can be used as an href to the simple search."""
        return canonical_url(self.context) + "/+reportedbugs"

    def shouldShowReporterWidget(self):
        """Should the reporter widget be shown on the advanced search page?"""
        return False

    def shouldShowTagsCombinatorWidget(self):
        """Should the tags combinator widget show on the search page?"""
        return False


class BugContactPackageBugsSearchListingView(BugTaskSearchListingView):
    """Bugs reported on packages for a bug contact."""

    columns_to_show = ["id", "summary", "importance", "status"]

    @property
    def current_package(self):
        """Get the package whose bugs are currently being searched."""
        if not (
            self.widgets['distribution'].hasInput() and
            self.widgets['distribution'].getInputValue()):
            raise UnexpectedFormData("A distribution is required")
        if not (
            self.widgets['sourcepackagename'].hasInput() and
            self.widgets['sourcepackagename'].getInputValue()):
            raise UnexpectedFormData("A sourcepackagename is required")

        distribution = self.widgets['distribution'].getInputValue()
        return distribution.getSourcePackage(
            self.widgets['sourcepackagename'].getInputValue())

    def search(self, searchtext=None):
        distrosourcepackage = self.current_package
        return BugTaskSearchListingView.search(
            self, searchtext=searchtext, context=distrosourcepackage)

    @cachedproperty
    def total_bug_counts(self):
        """Return the totals of each type of package bug count as a dict."""
        totals = {
            'open_bugs_count': 0,
            'critical_bugs_count': 0,
            'unassigned_bugs_count': 0,
            'inprogress_bugs_count': 0,}

        for package_counts in self.package_bug_counts:
            for key in totals.keys():
                totals[key] += int(package_counts[key])

        return totals

    @cachedproperty
    def package_bug_counts(self):
        """Return a list of dicts used for rendering package bug counts."""
        L = []
        for package_counts in self.context.getBugContactOpenBugCounts(
            self.user):
            package = package_counts['package']
            L.append({
                'package_name': package.displayname,
                'package_search_url':
                    self.getBugContactPackageSearchURL(package),
                'open_bugs_count': package_counts['open'],
                'open_bugs_url': self.getOpenBugsURL(package),
                'critical_bugs_count': package_counts['open_critical'],
                'critical_bugs_url': self.getCriticalBugsURL(package),
                'unassigned_bugs_count': package_counts['open_unassigned'],
                'unassigned_bugs_url': self.getUnassignedBugsURL(package),
                'inprogress_bugs_count': package_counts['open_inprogress'],
                'inprogress_bugs_url': self.getInProgressBugsURL(package)
            })

        return sorted(L, key=itemgetter('package_name'))

    def getOtherBugContactPackageLinks(self):
        """Return a list of the other packages for a bug contact.

        This excludes the current package.
        """
        current_package = self.current_package

        other_packages = [
            package for package in self.context.getBugContactPackages()
            if package != current_package]

        package_links = []
        for other_package in other_packages:
            package_links.append({
                'title': other_package.displayname,
                'url': self.getBugContactPackageSearchURL(other_package)})

        return package_links

    def getBugContactPackageSearchURL(self, distributionsourcepackage=None,
                                      advanced=False, extra_params=None):
        """Construct a default search URL for a distributionsourcepackage.

        Optional filter parameters can be specified as a dict with the
        extra_params argument.
        """
        if distributionsourcepackage is None:
            distributionsourcepackage = self.current_package

        params = {
            "field.distribution": distributionsourcepackage.distribution.name,
            "field.sourcepackagename": distributionsourcepackage.name,
            "search": "Search"}

        if extra_params is not None:
            # We must UTF-8 encode searchtext to play nicely with
            # urllib.urlencode, because it may contain non-ASCII characters.
            if extra_params.has_key("field.searchtext"):
                extra_params["field.searchtext"] = (
                    extra_params["field.searchtext"].encode("utf8"))

            params.update(extra_params)

        person_url = canonical_url(self.context)
        query_string = urllib.urlencode(sorted(params.items()), doseq=True)

        if advanced:
            return (person_url + '/+packagebugs-search?advanced=1&%s'
                    % query_string)
        else:
            return person_url + '/+packagebugs-search?%s' % query_string

    def getBugContactPackageAdvancedSearchURL(self,
                                              distributionsourcepackage=None):
        """Build the advanced search URL for a distributionsourcepackage."""
        return self.getBugContactPackageSearchURL(advanced=True)

    def getOpenBugsURL(self, distributionsourcepackage):
        """Return the URL for open bugs on distributionsourcepackage."""
        status_params = {'field.status': []}

        for status in UNRESOLVED_BUGTASK_STATUSES:
            status_params['field.status'].append(status.title)

        return self.getBugContactPackageSearchURL(
            distributionsourcepackage=distributionsourcepackage,
            extra_params=status_params)

    def getCriticalBugsURL(self, distributionsourcepackage):
        """Return the URL for critical bugs on distributionsourcepackage."""
        critical_bugs_params = {
            'field.status': [], 'field.importance': "Critical"}

        for status in UNRESOLVED_BUGTASK_STATUSES:
            critical_bugs_params["field.status"].append(status.title)

        return self.getBugContactPackageSearchURL(
            distributionsourcepackage=distributionsourcepackage,
            extra_params=critical_bugs_params)

    def getUnassignedBugsURL(self, distributionsourcepackage):
        """Return the URL for unassigned bugs on distributionsourcepackage."""
        unassigned_bugs_params = {
            "field.status": [], "field.unassigned": "on"}

        for status in UNRESOLVED_BUGTASK_STATUSES:
            unassigned_bugs_params["field.status"].append(status.title)

        return self.getBugContactPackageSearchURL(
            distributionsourcepackage=distributionsourcepackage,
            extra_params=unassigned_bugs_params)

    def getInProgressBugsURL(self, distributionsourcepackage):
        """Return the URL for unassigned bugs on distributionsourcepackage."""
        inprogress_bugs_params = {"field.status": "In Progress"}

        return self.getBugContactPackageSearchURL(
            distributionsourcepackage=distributionsourcepackage,
            extra_params=inprogress_bugs_params)

    def shouldShowSearchWidgets(self):
        # XXX: Guilherme Salgado 2005-11-05:
        # It's not possible to search amongst the bugs on maintained
        # software, so for now I'll be simply hiding the search widgets.
        return False

    # Methods that customize the advanced search form.
    def getAdvancedSearchPageHeading(self):
        return (
            "Bugs in %s: Advanced Search" % self.current_package.displayname)

    def getAdvancedSearchButtonLabel(self):
        return "Search bugs in %s" % self.current_package.displayname

    def getSimpleSearchURL(self):
        return self.getBugContactPackageSearchURL()


class PersonRelatedBugsView(BugTaskSearchListingView, FeedsMixin):
    """All bugs related to someone."""

    columns_to_show = ["id", "summary", "bugtargetdisplayname",
                       "importance", "status"]

    def search(self, extra_params=None):
        """Return the open bugs related to a person.

        :param extra_params: A dict that provides search params added to
            the search criteria taken from the request. Params in
            `extra_params` take precedence over request params.
        """
        context = self.context
        params = self.buildSearchParams(extra_params=extra_params)
        subscriber_params = copy.copy(params)
        subscriber_params.subscriber = context
        assignee_params = copy.copy(params)
        owner_params = copy.copy(params)
        commenter_params = copy.copy(params)

        # Only override the assignee, commenter and owner if they were not
        # specified by the user.
        if assignee_params.assignee is None:
            assignee_params.assignee = context
        if owner_params.owner is None:
            # Specify both owner and bug_reporter to try to prevent the same
            # bug (but different tasks) being displayed.
            owner_params.owner = context
            owner_params.bug_reporter = context
        if commenter_params.bug_commenter is None:
            commenter_params.bug_commenter = context

        tasks = self.context.searchTasks(
            assignee_params, subscriber_params, owner_params,
            commenter_params)
        return BugListingBatchNavigator(
            tasks, self.request, columns_to_show=self.columns_to_show,
            size=config.malone.buglist_batch_size)

    def getSearchPageHeading(self):
        return "Bugs related to %s" % self.context.displayname

    def getAdvancedSearchPageHeading(self):
        return "Bugs Related to %s: Advanced Search" % (
            self.context.displayname)

    def getAdvancedSearchButtonLabel(self):
        return "Search bugs related to %s" % self.context.displayname

    def getSimpleSearchURL(self):
        return canonical_url(self.context) + "/+bugs"


class PersonAssignedBugTaskSearchListingView(BugTaskSearchListingView):
    """All bugs assigned to someone."""

    columns_to_show = ["id", "summary", "bugtargetdisplayname",
                       "importance", "status"]

    def search(self):
        """Return the open bugs assigned to a person."""
        return BugTaskSearchListingView.search(
            self, extra_params={'assignee': self.context})

    def shouldShowAssigneeWidget(self):
        """Should the assignee widget be shown on the advanced search page?"""
        return False

    def shouldShowAssignedToTeamPortlet(self):
        """Should the team assigned bugs portlet be shown?"""
        return True

    def shouldShowTagsCombinatorWidget(self):
        """Should the tags combinator widget show on the search page?"""
        return False

    def getSearchPageHeading(self):
        """The header for the search page."""
        return "Bugs assigned to %s" % self.context.displayname

    def getAdvancedSearchPageHeading(self):
        """The header for the advanced search page."""
        return "Bugs Assigned to %s: Advanced Search" % (
            self.context.displayname)

    def getAdvancedSearchButtonLabel(self):
        """The Search button for the advanced search page."""
        return "Search bugs assigned to %s" % self.context.displayname

    def getSimpleSearchURL(self):
        """Return a URL that can be usedas an href to the simple search."""
        return canonical_url(self.context) + "/+assignedbugs"


class PersonCommentedBugTaskSearchListingView(BugTaskSearchListingView):
    """All bugs commented on by a Person."""

    columns_to_show = ["id", "summary", "bugtargetdisplayname",
                       "importance", "status"]

    def search(self):
        """Return the open bugs commented on by a person."""
        return BugTaskSearchListingView.search(
            self, extra_params={'bug_commenter': self.context})

    def getSearchPageHeading(self):
        """The header for the search page."""
        return "Bugs commented on by %s" % self.context.displayname

    def getAdvancedSearchPageHeading(self):
        """The header for the advanced search page."""
        return "Bugs commented on by %s: Advanced Search" % (
            self.context.displayname)

    def getAdvancedSearchButtonLabel(self):
        """The Search button for the advanced search page."""
        return "Search bugs commented on by %s" % self.context.displayname

    def getSimpleSearchURL(self):
        """Return a URL that can be used as an href to the simple search."""
        return canonical_url(self.context) + "/+commentedbugs"


class SubscribedBugTaskSearchListingView(BugTaskSearchListingView):
    """All bugs someone is subscribed to."""

    columns_to_show = ["id", "summary", "bugtargetdisplayname",
                       "importance", "status"]

    def search(self):
        return BugTaskSearchListingView.search(
            self, extra_params={'subscriber': self.context})

    def getSearchPageHeading(self):
        """The header for the search page."""
        return "Bugs %s is subscribed to" % self.context.displayname

    def getAdvancedSearchPageHeading(self):
        """The header for the advanced search page."""
        return "Bugs %s is Cc'd to: Advanced Search" % (
            self.context.displayname)

    def getAdvancedSearchButtonLabel(self):
        """The Search button for the advanced search page."""
        return "Search bugs %s is Cc'd to" % self.context.displayname

    def getSimpleSearchURL(self):
        """Return a URL that can be used as an href to the simple search."""
        return canonical_url(self.context) + "/+subscribedbugs"


class PersonLanguagesView(LaunchpadView):

    def initialize(self):
        request = self.request
        if request.method == "POST" and "SAVE-LANGS" in request.form:
            self.submitLanguages()

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return (
            IRequestPreferredLanguages(self.request).getPreferredLanguages())

    def visible_checked_languages(self):
        return self.context.languages

    def visible_unchecked_languages(self):
        common_languages = getUtility(ILanguageSet).common_languages
        person_languages = self.context.languages
        return sorted(set(common_languages) - set(person_languages),
                      key=attrgetter('englishname'))

    def getRedirectionURL(self):
        request = self.request
        referrer = request.getHeader('referer')
        if referrer and referrer.startswith(request.getApplicationURL()):
            return referrer
        else:
            return ''

    @property
    def is_current_user(self):
        """Return True when the Context is also the User."""
        return self.user == self.context

    def submitLanguages(self):
        '''Process a POST request to the language preference form.

        This list of languages submitted is compared to the the list of
        languages the user has, and the latter is matched to the former.
        '''

        all_languages = getUtility(ILanguageSet)
        old_languages = self.context.languages
        new_languages = []

        for key in all_languages.keys():
            if self.request.has_key(key) and self.request.get(key) == u'on':
                new_languages.append(all_languages[key])

        if self.is_current_user:
            subject = "your"
        else:
            subject = "%s's" % self.context.displayname

        # Add languages to the user's preferences.
        for language in set(new_languages) - set(old_languages):
            self.context.addLanguage(language)
            self.request.response.addInfoNotification(
                "Added %(language)s to %(subject)s preferred languages." %
                {'language' : language.englishname, 'subject' : subject})

        # Remove languages from the user's preferences.
        for language in set(old_languages) - set(new_languages):
            self.context.removeLanguage(language)
            self.request.response.addInfoNotification(
                "Removed %(language)s from %(subject)s preferred languages." %
                {'language' : language.englishname, 'subject' : subject})

        redirection_url = self.request.get('redirection_url')
        if redirection_url:
            self.request.response.redirect(redirection_url)


class PersonView(LaunchpadView, FeedsMixin):
    """A View class used in almost all Person's pages."""

    @cachedproperty
    def recently_approved_members(self):
        members = self.context.getMembersByStatus(
            TeamMembershipStatus.APPROVED,
            orderBy='-TeamMembership.date_joined')
        return members[:5]

    @cachedproperty
    def recently_proposed_members(self):
        members = self.context.getMembersByStatus(
            TeamMembershipStatus.PROPOSED,
            orderBy='-TeamMembership.date_proposed')
        return members[:5]

    @cachedproperty
    def openpolls(self):
        assert self.context.isTeam()
        return IPollSubset(self.context).getOpenPolls()

    @cachedproperty
    def closedpolls(self):
        assert self.context.isTeam()
        return IPollSubset(self.context).getClosedPolls()

    @cachedproperty
    def notyetopenedpolls(self):
        assert self.context.isTeam()
        return IPollSubset(self.context).getNotYetOpenedPolls()

    @cachedproperty
    def contributions(self):
        """Cache the results of getProjectsAndCategoriesContributedTo()."""
        return self.context.getProjectsAndCategoriesContributedTo(
            limit=5)

    @cachedproperty
    def contributed_categories(self):
        """Return all karma categories in which this person has some karma."""
        categories = set()
        for contrib in self.contributions:
            categories.update(category for category in contrib['categories'])
        return sorted(categories, key=attrgetter('title'))

    @cachedproperty
    def context_is_probably_a_team(self):
        """Return True if we have any indication that context is a team.

        For now, all we do is check whether or not any email associated with
        our context contains the '@lists.' string as that's a very good
        indication this is a team which was automatically created.

        This can only be used when the context is an automatically created
        profile (account_status == NOACCOUNT).
        """
        assert self.context.account_status == AccountStatus.NOACCOUNT, (
            "This can only be used when the context has no account.")
        emails = getUtility(IEmailAddressSet).getByPerson(self.context)
        for email in emails:
            if '@lists.' in email.email:
                return True
        return False

    @cachedproperty
    def openid_identity_url(self):
        """The identity URL for the person."""
        return canonical_url(OpenIDPersistentIdentity(self.context))

    @property
    def subscription_policy_description(self):
        """Return the description of this team's subscription policy."""
        team = self.context
        assert team.isTeam(), (
            'This method can only be called when the context is a team.')
        if team.subscriptionpolicy == TeamSubscriptionPolicy.RESTRICTED:
            description = _(
                "This is a restricted team; new members can only be added "
                "by one of the team's administrators.")
        elif team.subscriptionpolicy == TeamSubscriptionPolicy.MODERATED:
            description = _(
                "This is a moderated team; all subscriptions are subjected "
                "to approval by one of the team's administrators.")
        elif team.subscriptionpolicy == TeamSubscriptionPolicy.OPEN:
            description = _(
                "This is an open team; any user can join and no approval "
                "is required.")
        else:
            raise AssertionError('Unknown subscription policy.')
        return description

    @property
    def user_can_subscribe_to_list(self):
        """Can the user subscribe to this team's mailing list?

        A user can subscribe to the list if the team has an active
        mailing list, and if they do not already have a subscription.
        """
        if self.team_has_mailing_list:
            # If we are already subscribed, then we can not subscribe again.
            return not self.user_is_subscribed_to_list
        else:
            return False

    @property
    def user_is_subscribed_to_list(self):
        """Is the user subscribed to the team's mailing list?

        Subscriptions hang around even if the list is deactivated, etc.

        It is an error to ask if the user is subscribed to a mailing list
        that doesn't exist.
        """
        if self.user is None:
            return False

        mailing_list = self.context.mailing_list
        assert mailing_list is not None, "This team has no mailing list."
        has_subscription = bool(mailing_list.getSubscription(self.user))
        return has_subscription

    @property
    def team_has_mailing_list(self):
        """Is the team mailing list available for subscription?"""
        mailing_list = self.context.mailing_list
        return mailing_list is not None and mailing_list.isUsable()

    def getURLToAssignedBugsInProgress(self):
        """Return an URL to a page which lists all bugs assigned to this
        person that are In Progress.
        """
        query_string = urllib.urlencode(
            [('field.status', BugTaskStatus.INPROGRESS.title)])
        url = "%s/+assignedbugs" % canonical_url(self.context)
        return ("%(url)s?search=Search&%(query_string)s"
                % {'url': url, 'query_string': query_string})

    def getBugsInProgress(self):
        """Return up to 5 assigned bugs that are In Progress."""
        params = BugTaskSearchParams(
            user=self.user, assignee=self.context, omit_dupes=True,
            status=BugTaskStatus.INPROGRESS, orderby='-date_last_updated')
        return self.context.searchTasks(params)[:5]

    def viewingOwnPage(self):
        return self.user == self.context

    def hasCurrentPolls(self):
        """Return True if this team has any non-closed polls."""
        assert self.context.isTeam()
        return bool(self.openpolls) or bool(self.notyetopenedpolls)

    def no_bounties(self):
        return not (self.context.ownedBounties or
            self.context.reviewerBounties or
            self.context.subscribedBounties or
            self.context.claimedBounties)

    def userIsOwner(self):
        """Return True if the user is the owner of this Team."""
        if self.user is None:
            return False

        return self.user.inTeam(self.context.teamowner)

    def findUserPathToTeam(self):
        assert self.user is not None
        return self.user.findPathToTeam(self.context)

    def indirect_teams_via(self):
        """Return a list of dictionaries, where each dictionary has a team
        in which the person is an indirect member, and a path to membership
        in that team.
        """
        return [{'team': team,
                 'via': ', '.join(
                    [viateam.displayname for viateam in
                        self.context.findPathToTeam(team)[:-1]])}
                for team in self.context.teams_indirectly_participated_in]

    def userIsParticipant(self):
        """Return true if the user is a participant of this team.

        A person is said to be a team participant when he's a member
        of that team, either directly or indirectly via another team
        membership.
        """
        if self.user is None:
            return False
        return self.user.inTeam(self.context)

    def userIsActiveMember(self):
        """Return True if the user is an active member of this team."""
        return userIsActiveTeamMember(self.context)

    def userIsProposedMember(self):
        """Return True if the user is a proposed member of this team."""
        if self.user is None:
            return False
        return self.user in self.context.proposedmembers

    def userCanRequestToLeave(self):
        """Return true if the user can request to leave this team.

        A given user can leave a team only if he's an active member.
        """
        return self.userIsActiveMember()

    def obfuscatedEmail(self):
        if self.context.preferredemail is not None:
            return obfuscateEmail(self.context.preferredemail.email)
        else:
            return None

    def htmlEmail(self):
        if self.context.preferredemail is not None:
            return convertToHtmlCode(self.context.preferredemail.email)
        else:
            return None

    def htmlJabberIDs(self):
        """Return the person's Jabber IDs somewhat obfuscated.

        The IDs are encoded using HTML hexadecimal entities to hinder
        email harvesting. (Jabber IDs are sometime valid email accounts,
        gmail for example.)
        """
        return [convertToHtmlCode(jabber.jabberid)
                for jabber in self.context.jabberids]

    def showSSHKeys(self):
        """Return a data structure used for display of raw SSH keys"""
        self.request.response.setHeader('Content-Type', 'text/plain')
        keys = []
        for key in self.context.sshkeys:
            if key.keytype == SSHKeyType.DSA:
                type_name = 'ssh-dss'
            elif key.keytype == SSHKeyType.RSA:
                type_name = 'ssh-rsa'
            else:
                type_name = 'Unknown key type'
            keys.append("%s %s %s" % (type_name, key.keytext, key.comment))
        return "\n".join(keys)

    @cachedproperty
    def archive_url(self):
        """Return a url to a mailing list archive for the team's list.

        If the person is not a team, does not have a mailing list, or that
        mailing list has never been activated, return None instead.
        """
        mailing_list = self.context.mailing_list
        if mailing_list is None:
            return None
        return mailing_list.archive_url

    def getLatestUploadedPPAPackages(self):
        """Return the sourcepackagereleases uploaded to PPAs by this person.

        Results are filtered according to the permission of the requesting
        user to see private archives.
        """
        packages = self.context.getLatestUploadedPPAPackages()

        # For each package we find out which archives it was published in.
        # If the user has permission to see any of those archives then
        # the user is permitted to see the package.
        #
        # Ideally this check should be done in
        # IPerson.getLatestUploadedPPAPackages() but formulating the SQL
        # query is virtually impossible!
        results = []
        for package in packages:
            # Make a shallow copy to remove the Zope security.
            archives = set(package.published_archives)
            # Ensure the SPR.upload_archive is also considered.
            archives.add(package.upload_archive)
            for archive in archives:
                if check_permission('launchpad.View', archive):
                    results.append(package)
                    break
        return results


class PersonIndexView(XRDSContentNegotiationMixin, PersonView):
    """View class for person +index and +xrds pages."""

    xrds_template = ViewPageTemplateFile("../templates/person-xrds.pt")

    def initialize(self):
        super(PersonIndexView, self).initialize()
        if self.request.method == "POST":
            self.processForm()

    @cachedproperty
    def enable_xrds_discovery(self):
        """Only enable discovery if person is OpenID enabled."""
        return self.context.is_openid_enabled

    def processForm(self):
        if not self.request.form.get('unsubscribe'):
            raise UnexpectedFormData(
                "The mailing list form did not receive the expected form "
                "fields.")

        mailing_list = self.context.mailing_list
        if mailing_list is None:
            raise UnexpectedFormData(
                _("This team does not have a mailing list."))
        if not self.user:
            raise Unauthorized(
                _("You must be logged in to unsubscribe."))
        try:
            mailing_list.unsubscribe(self.user)
        except CannotUnsubscribe:
            self.request.response.addErrorNotification(
                _("You could not be unsubscribed from the team mailing "
                  "list."))
        else:
            self.request.response.addInfoNotification(
                _("You have been unsubscribed from the team "
                  "mailing list."))
        self.request.response.redirect(canonical_url(self.context))


class PersonRelatedProjectsView(LaunchpadView):

    # Safety net for the Registry Admins case which is the owner/driver of
    # lots of projects.
    max_results_to_display = config.launchpad.default_batch_size

    def _related_projects(self):
        """Return all projects owned or driven by this person."""
        return self.context.getOwnedOrDrivenPillars()

    @cachedproperty
    def relatedProjects(self):
        """Return projects owned or driven by this person up to the maximum
        configured."""
        return list(self._related_projects()[:self.max_results_to_display])

    @cachedproperty
    def firstFiveRelatedProjects(self):
        """Return first five projects owned or driven by this person."""
        return list(self._related_projects()[:5])

    @cachedproperty
    def related_projects_count(self):
        return self._related_projects().count()

    def tooManyRelatedProjectsFound(self):
        return self.related_projects_count > self.max_results_to_display


class PersonCodeOfConductEditView(LaunchpadView):

    def performCoCChanges(self):
        """Make changes to code-of-conduct signature records for this
        person.
        """
        sig_ids = self.request.form.get("DEACTIVATE_SIGNATURE")

        if sig_ids is not None:
            sCoC_util = getUtility(ISignedCodeOfConductSet)

            # verify if we have multiple entries to deactive
            if not isinstance(sig_ids, list):
                sig_ids = [sig_ids]

            for sig_id in sig_ids:
                sig_id = int(sig_id)
                # Deactivating signature
                comment = 'Deactivated by Owner'
                sCoC_util.modifySignature(sig_id, self.user, comment, False)

            return True


class PersonEditWikiNamesView(LaunchpadView):

    def _sanitizeWikiURL(self, url):
        """Strip whitespaces and make sure :url ends in a single '/'."""
        if not url:
            return url
        return '%s/' % url.strip().rstrip('/')

    def initialize(self):
        """Process the WikiNames form."""
        self.error_message = None
        if self.request.method != "POST":
            # Nothing to do
            return

        form = self.request.form
        context = self.context
        wikinameset = getUtility(IWikiNameSet)
        ubuntuwikiname = form.get('ubuntuwikiname')
        existingwiki = wikinameset.getByWikiAndName(
            UBUNTU_WIKI_URL, ubuntuwikiname)

        if not ubuntuwikiname:
            self.error_message = "Your Ubuntu WikiName cannot be empty."
            return
        elif existingwiki is not None and existingwiki.person != context:
            self.error_message = (
                'The Ubuntu WikiName %s is already registered by '
                '<a href="%s">%s</a>.'
                % (ubuntuwikiname, canonical_url(existingwiki.person),
                   cgi.escape(existingwiki.person.browsername)))
            return
        context.ubuntuwiki.wikiname = ubuntuwikiname

        for w in context.otherwikis:
            # XXX: GuilhermeSalgado 2005-08-25:
            # We're exposing WikiName IDs here because that's the only
            # unique column we have. If we don't do this we'll have to
            # generate the field names using the WikiName.wiki and
            # WikiName.wikiname columns (because these two columns make
            # another unique identifier for WikiNames), but that's tricky and
            # not worth the extra work.
            if form.get('remove_%d' % w.id):
                w.destroySelf()
            else:
                wiki = self._sanitizeWikiURL(form.get('wiki_%d' % w.id))
                wikiname = form.get('wikiname_%d' % w.id)
                if not (wiki and wikiname):
                    self.error_message = (
                        "Neither Wiki nor WikiName can be empty.")
                    return
                # Try to make sure people will have only a single Ubuntu
                # WikiName registered. Although this is almost impossible
                # because they can do a lot of tricks with the URLs to make
                # them look different from UBUNTU_WIKI_URL but still point to
                # the same place.
                elif wiki == UBUNTU_WIKI_URL:
                    self.error_message = (
                        "You cannot have two Ubuntu WikiNames.")
                    return
                w.wiki = wiki
                w.wikiname = wikiname

        wiki = self._sanitizeWikiURL(form.get('newwiki'))
        wikiname = form.get('newwikiname')
        if wiki or wikiname:
            if wiki and wikiname:
                existingwiki = wikinameset.getByWikiAndName(wiki, wikiname)
                if existingwiki and existingwiki.person != context:
                    self.error_message = (
                        'The WikiName %s%s is already registered by '
                        '<a href="%s">%s</a>.'
                        % (wiki, wikiname, canonical_url(existingwiki.person),
                           cgi.escape(existingwiki.person.browsername)))
                    return
                elif existingwiki:
                    self.error_message = (
                        'The WikiName %s%s already belongs to you.'
                        % (wiki, wikiname))
                    return
                elif wiki == UBUNTU_WIKI_URL:
                    self.error_message = (
                        "You cannot have two Ubuntu WikiNames.")
                    return
                wikinameset.new(context, wiki, wikiname)
            else:
                self.newwiki = wiki
                self.newwikiname = wikiname
                self.error_message = "Neither Wiki nor WikiName can be empty."
                return


class PersonEditIRCNicknamesView(LaunchpadView):

    def initialize(self):
        """Process the IRC nicknames form."""
        self.error_message = None
        if self.request.method != "POST":
            # Nothing to do
            return

        form = self.request.form
        for ircnick in self.context.ircnicknames:
            # XXX: GuilhermeSalgado 2005-08-25:
            # We're exposing IrcID IDs here because that's the only
            # unique column we have, so we don't have anything else that we
            # can use to make field names that allow us to uniquely identify
            # them.
            if form.get('remove_%d' % ircnick.id):
                ircnick.destroySelf()
            else:
                nick = form.get('nick_%d' % ircnick.id)
                network = form.get('network_%d' % ircnick.id)
                if not (nick and network):
                    self.error_message = (
                        "Neither Nickname nor Network can be empty.")
                    return
                ircnick.nickname = nick
                ircnick.network = network

        nick = form.get('newnick')
        network = form.get('newnetwork')
        if nick or network:
            if nick and network:
                getUtility(IIrcIDSet).new(self.context, network, nick)
            else:
                self.newnick = nick
                self.newnetwork = network
                self.error_message = (
                    "Neither Nickname nor Network can be empty.")
                return


class PersonEditJabberIDsView(LaunchpadView):

    def initialize(self):
        """Process the Jabber ID form."""
        self.error_message = None
        if self.request.method != "POST":
            # Nothing to do
            return

        form = self.request.form
        for jabber in self.context.jabberids:
            if form.get('remove_%s' % jabber.jabberid):
                jabber.destroySelf()
            else:
                jabberid = form.get('jabberid_%s' % jabber.jabberid)
                if not jabberid:
                    self.error_message = "You cannot save an empty Jabber ID."
                    return
                jabber.jabberid = jabberid

        jabberid = form.get('newjabberid')
        if jabberid:
            jabberset = getUtility(IJabberIDSet)
            existingjabber = jabberset.getByJabberID(jabberid)
            if existingjabber is None:
                jabberset.new(self.context, jabberid)
            elif existingjabber.person != self.context:
                self.error_message = (
                    'The Jabber ID %s is already registered by '
                    '<a href="%s">%s</a>.'
                    % (jabberid, canonical_url(existingjabber.person),
                       cgi.escape(existingjabber.person.browsername)))
                return
            else:
                self.error_message = (
                    'The Jabber ID %s already belongs to you.' % jabberid)
                return


class PersonEditSSHKeysView(LaunchpadView):

    info_message = None
    error_message = None

    def initialize(self):
        if self.request.method != "POST":
            # Nothing to do
            return

        action = self.request.form.get('action')

        if action == 'add_ssh':
            self.add_ssh()
        elif action == 'remove_ssh':
            self.remove_ssh()
        else:
            raise UnexpectedFormData("Unexpected action: %s" % action)

    def add_ssh(self):
        sshkey = self.request.form.get('sshkey')
        try:
            kind, keytext, comment = sshkey.split(' ', 2)
        except ValueError:
            self.error_message = 'Invalid public key'
            return

        if not (kind and keytext and comment):
            self.error_message = 'Invalid public key'
            return

        if kind == 'ssh-rsa':
            keytype = SSHKeyType.RSA
        elif kind == 'ssh-dss':
            keytype = SSHKeyType.DSA
        else:
            self.error_message = 'Invalid public key'
            return

        getUtility(ISSHKeySet).new(self.user, keytype, keytext, comment)
        self.info_message = 'SSH public key added.'

    def remove_ssh(self):
        key_id = self.request.form.get('key')
        if not key_id:
            raise UnexpectedFormData('SSH Key was not defined')

        sshkey = getUtility(ISSHKeySet).getByID(key_id)
        if sshkey is None:
            self.error_message = "Cannot remove a key that doesn't exist"
            return

        if sshkey.person != self.user:
            raise UnexpectedFormData("Cannot remove someone else's key")

        comment = sshkey.comment
        sshkey.destroySelf()
        self.info_message = 'Key "%s" removed' % comment


class PersonTranslationView(LaunchpadView):
    """View for translation-related Person pages."""
    @cachedproperty
    def batchnav(self):
        batchnav = BatchNavigator(self.context.translation_history,
                                  self.request)
        # XXX: kiko 2006-03-17 bug=60320: Because of a template reference
        # to pofile.potemplate.displayname, it would be ideal to also
        # prejoin inside translation_history:
        #   potemplate.productseries
        #   potemplate.productseries.product
        #   potemplate.distroseries
        #   potemplate.distroseries.distribution
        #   potemplate.sourcepackagename
        # However, a list this long may be actually suggesting that
        # displayname be cached in a table field; particularly given the
        # fact that it won't be altered very often. At any rate, the
        # code below works around this by caching all the templates in
        # one shot. The list() ensures that we materialize the query
        # before passing it on to avoid reissuing it. Note also that the
        # fact that we iterate over currentBatch() here means that the
        # translation_history query is issued again. Tough luck.
        ids = set(record.pofile.potemplate.id
                  for record in batchnav.currentBatch())
        if ids:
            cache = list(getUtility(IPOTemplateSet).getByIDs(ids))

        return batchnav

    @cachedproperty
    def translation_groups(self):
        """Return translation groups a person is a member of."""
        return list(self.context.translation_groups)

    def should_display_message(self, translationmessage):
        """Should a certain `TranslationMessage` be displayed.

        Return False if user is not logged in and message may contain
        sensitive data such as email addresses.

        Otherwise, return True.
        """
        if self.user:
            return True
        return not (
            translationmessage.potmsgset.hide_translations_from_anonymous)


class PersonGPGView(LaunchpadView):
    """View for the GPG-related actions for a Person

    Supports claiming (importing) a key, validating it and deactivating
    it. Also supports removing the token generated for validation (in
    the case you want to give up on importing the key).
    """
    key = None
    fingerprint = None

    key_ok = False
    invalid_fingerprint = False
    key_retrieval_failed = False
    key_already_imported = False

    error_message = None
    info_message = None

    def keyserver_url(self):
        assert self.fingerprint
        return getUtility(
            IGPGHandler).getURLForKeyInServer(self.fingerprint, public=True)

    def form_action(self):
        permitted_actions = ['claim_gpg', 'deactivate_gpg',
                             'remove_gpgtoken', 'reactivate_gpg']
        if self.request.method != "POST":
            return ''
        action = self.request.form.get('action')
        if action and (action not in permitted_actions):
            raise UnexpectedFormData("Action was not defined")
        getattr(self, action)()

    def claim_gpg(self):
        # XXX cprov 2005-04-01: As "Claim GPG key" takes a lot of time, we
        # should process it throught the NotificationEngine.
        gpghandler = getUtility(IGPGHandler)
        fingerprint = self.request.form.get('fingerprint')
        self.fingerprint = gpghandler.sanitizeFingerprint(fingerprint)

        if not self.fingerprint:
            self.invalid_fingerprint = True
            return

        gpgkeyset = getUtility(IGPGKeySet)
        if gpgkeyset.getByFingerprint(self.fingerprint):
            self.key_already_imported = True
            return

        try:
            key = gpghandler.retrieveKey(self.fingerprint)
        except GPGKeyNotFoundError:
            self.key_retrieval_failed = True
            return

        self.key = key
        if not key.expired and not key.revoked:
            self._validateGPG(key)
            self.key_ok = True

    def deactivate_gpg(self):
        key_ids = self.request.form.get('DEACTIVATE_GPGKEY')

        if key_ids is None:
            self.error_message = 'No Key(s) selected for deactivation.'
            return

        # verify if we have multiple entries to deactive
        if not isinstance(key_ids, list):
            key_ids = [key_ids]

        gpgkeyset = getUtility(IGPGKeySet)

        deactivated_keys = []
        for key_id in key_ids:
            gpgkey = gpgkeyset.get(key_id)
            if gpgkey is None:
                continue
            if gpgkey.owner != self.user:
                self.error_message = "Cannot deactivate someone else's key"
                return
            gpgkey.active = False
            deactivated_keys.append(gpgkey.displayname)

        flush_database_updates()
        self.info_message = (
            'Deactivated key(s): %s' % ", ".join(deactivated_keys))

    def remove_gpgtoken(self):
        token_fingerprints = self.request.form.get('REMOVE_GPGTOKEN')

        if token_fingerprints is None:
            self.error_message = 'No key(s) pending validation selected.'
            return

        logintokenset = getUtility(ILoginTokenSet)
        if not isinstance(token_fingerprints, list):
            token_fingerprints = [token_fingerprints]

        cancelled_fingerprints = []
        for fingerprint in token_fingerprints:
            logintokenset.deleteByFingerprintRequesterAndType(
                fingerprint, self.user, LoginTokenType.VALIDATEGPG)
            logintokenset.deleteByFingerprintRequesterAndType(
                fingerprint, self.user, LoginTokenType.VALIDATESIGNONLYGPG)
            cancelled_fingerprints.append(fingerprint)

        self.info_message = ('Cancelled validation of key(s): %s'
                             % ", ".join(cancelled_fingerprints))

    def reactivate_gpg(self):
        key_ids = self.request.form.get('REACTIVATE_GPGKEY')

        if key_ids is None:
            self.error_message = 'No Key(s) selected for reactivation.'
            return

        found = []
        notfound = []
        # verify if we have multiple entries to deactive
        if not isinstance(key_ids, list):
            key_ids = [key_ids]

        gpghandler = getUtility(IGPGHandler)
        keyset = getUtility(IGPGKeySet)

        for key_id in key_ids:
            gpgkey = keyset.get(key_id)
            try:
                key = gpghandler.retrieveKey(gpgkey.fingerprint)
            except GPGKeyNotFoundError:
                notfound.append(gpgkey.fingerprint)
            else:
                found.append(key.displayname)
                self._validateGPG(key)

        comments = []
        if len(found) > 0:
            comments.append(
                'A message has been sent to %s with instructions to '
                'reactivate these key(s): %s'
                % (self.context.preferredemail.email, ', '.join(found)))
        if len(notfound) > 0:
            if len(notfound) == 1:
                comments.append(
                    'Launchpad failed to retrieve this key from '
                    'the keyserver: %s. Please make sure the key is '
                    'published in a keyserver (such as '
                    '<a href="http://pgp.mit.edu">pgp.mit.edu</a>) before '
                    'trying to reactivate it again.' % (', '.join(notfound)))
            else:
                comments.append(
                    'Launchpad failed to retrieve these keys from '
                    'the keyserver: %s. Please make sure the keys '
                    'are published in a keyserver (such as '
                    '<a href="http://pgp.mit.edu">pgp.mit.edu</a>) '
                    'before trying to reactivate them '
                    'again.' % (', '.join(notfound)))

        self.info_message = '\n<br>\n'.join(comments)

    def _validateGPG(self, key):
        logintokenset = getUtility(ILoginTokenSet)
        bag = getUtility(ILaunchBag)

        preferredemail = bag.user.preferredemail.email
        login = bag.login

        if key.can_encrypt:
            tokentype = LoginTokenType.VALIDATEGPG
        else:
            tokentype = LoginTokenType.VALIDATESIGNONLYGPG

        token = logintokenset.new(self.context, login,
                                  preferredemail,
                                  tokentype,
                                  fingerprint=key.fingerprint)

        token.sendGPGValidationRequest(key)


class PersonChangePasswordView(LaunchpadFormView):

    label = "Change your password"
    schema = IPersonChangePassword
    field_names = ['currentpassword', 'password']
    custom_widget('password', PasswordChangeWidget)

    @property
    def next_url(self):
        return canonical_url(self.context)

    def validate(self, form_values):
        currentpassword = form_values.get('currentpassword')
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(currentpassword, self.context.password):
            self.setFieldError('currentpassword', _(
                "The provided password doesn't match your current password."))

    @action(_("Change Password"), name="submit")
    def submit_action(self, action, data):
        password = data['password']
        self.context.password = password
        self.request.response.addInfoNotification(_(
            "Password changed successfully"))


class BasePersonEditView(LaunchpadEditFormView):

    schema = IPerson
    field_names = []

    @action(_("Save"), name="save")
    def action_save(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class PersonEditHomePageView(BasePersonEditView):

    field_names = ['homepage_content']
    custom_widget(
        'homepage_content', TextAreaWidget, height=30, width=30)


class PersonEditView(BasePersonEditView):

    field_names = ['displayname', 'name', 'hide_email_addresses',
        'verbose_bugnotifications', 'timezone']
    custom_widget('timezone', SelectWidget, size=15)


class PersonBrandingView(BrandingChangeView):

    field_names = ['logo', 'mugshot']
    schema = IPerson


class TeamJoinView(PersonView):

    def initialize(self):
        super(TeamJoinView, self).initialize()
        if self.request.method == "POST":
            self.processForm()

    @property
    def join_allowed(self):
        """Is the logged in user allowed to join this team?

        The answer is yes if this team's subscription policy is not RESTRICTED
        and this team's visibility is either None or PUBLIC.
        """
        # Joining a moderated team will put you on the proposed_members
        # list. If it is a private membership team, you are not allowed
        # to view the proposed_members attribute until you are an
        # active member; therefore, it would look like the join button
        # is broken. Either private membership teams should always have a
        # restricted subscription policy, or we need a more complicated
        # permission model.
        if not (self.context.visibility is None
                or self.context.visibility == PersonVisibility.PUBLIC):
            return False

        restricted = TeamSubscriptionPolicy.RESTRICTED
        return self.context.subscriptionpolicy != restricted

    @property
    def user_can_request_to_join(self):
        """Can the logged in user request to join this team?

        The user can request if he's allowed to join this team and if he's
        not yet an active member of this team.
        """
        if not self.join_allowed:
            return False
        return not (self.userIsActiveMember() or self.userIsProposedMember())

    @property
    def team_is_moderated(self):
        """Is this team a moderated team?

        Return True if the team's subscription policy is MODERATED.
        """
        policy = self.context.subscriptionpolicy
        return policy == TeamSubscriptionPolicy.MODERATED

    def processForm(self):
        request = self.request
        user = self.user
        context = self.context
        response = self.request.response

        notification = None
        if 'join' in request.form and self.user_can_request_to_join:
            # Shut off mailing list auto-subscription - we want direct
            # control over it.
            user.join(context, may_subscribe_to_list=False)

            if self.team_is_moderated:
                response.addInfoNotification(
                    _('Your request to join ${team} is awaiting '
                      'approval.',
                      mapping={'team': context.displayname}))
            else:
                response.addInfoNotification(
                    _('You have successfully joined ${team}.',
                      mapping={'team': context.displayname}))

            if 'mailinglist_subscribe' in request.form:
                self._subscribeToList()

        elif 'join' in request.form:
            response.addErrorNotification(
                _('You cannot join ${team}.',
                  mapping={'team': context.displayname}))
        elif 'goback' in request.form:
            # User clicked on the 'Go back' button, so we'll simply redirect.
            pass
        else:
            raise UnexpectedFormData(
                "Couldn't find any of the expected actions.")
        self.request.response.redirect(canonical_url(context))

    def _subscribeToList(self):
        """Subscribe the user to the team's mailing list."""
        response = self.request.response

        if self.user_can_subscribe_to_list:
            # 'user_can_subscribe_to_list' should have dealt with
            # all of the error cases.
            self.context.mailing_list.subscribe(self.user)

            if self.team_is_moderated:
                response.addInfoNotification(
                    _('Your mailing list subscription is '
                      'awaiting approval.'))
            else:
                response.addInfoNotification(
                    structured(
                        _("You have been subscribed to this "
                          "team&#x2019;s mailing list.")))
        else:
            # A catch-all case, perhaps from stale or mangled
            # form data.
            response.addErrorNotification(
                _('Mailing list subscription failed.'))


class TeamAddMyTeamsView(LaunchpadFormView):
    """Propose/add to this team any team that you're an administrator of."""

    custom_widget('teams', LabeledMultiCheckBoxWidget)

    def initialize(self):
        context = self.context
        if context.subscriptionpolicy == TeamSubscriptionPolicy.MODERATED:
            self.label = 'Propose these teams as members'
        else:
            self.label = 'Add these teams to %s' % context.displayname
        self.next_url = canonical_url(context)
        super(TeamAddMyTeamsView, self).initialize()

    def setUpFields(self):
        terms = []
        for team in self.candidate_teams:
            text = '<a href="%s">%s</a>' % (
                canonical_url(team), team.displayname)
            terms.append(SimpleTerm(team, team.name, text))
        self.form_fields = FormFields(
            List(__name__='teams',
                 title=_(''),
                 value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                 required=False),
            custom_widget=self.custom_widgets['teams'],
            render_context=self.render_context)

    def setUpWidgets(self, context=None):
        super(TeamAddMyTeamsView, self).setUpWidgets(context)
        self.widgets['teams'].display_label = False

    @cachedproperty
    def candidate_teams(self):
        """Return the set of teams that can be added/proposed for the context.

        We return only teams that the user can administer, that aren't already
        a member in the context or that the context isn't a member of. (Of
        course, the context is also omitted.)
        """
        candidates = []
        for team in self.user.getAdministratedTeams():
            if team == self.context:
                continue
            elif team in self.context.activemembers:
                continue
            elif self.context.hasParticipationEntryFor(team):
                continue
            candidates.append(team)
        return candidates

    @action(_("Cancel"), name="cancel",
            validator=LaunchpadFormView.validate_none)
    def cancel_action(self, action, data):
        """Simply redirect to the team's page."""
        pass

    def validate(self, data):
        if len(data.get('teams', [])) == 0:
            self.setFieldError('teams',
                               'Please select the team(s) you want to be '
                               'member(s) of this team.')

    def hasCandidates(self, action):
        """Return whether the user has teams to propose."""
        return len(self.candidate_teams) > 0

    @action(_("Continue"), name="continue", condition=hasCandidates)
    def continue_action(self, action, data):
        """Make the selected teams join this team."""
        context = self.context
        for team in data['teams']:
            team.join(context, requester=self.user)
        if context.subscriptionpolicy == TeamSubscriptionPolicy.MODERATED:
            msg = 'proposed to this team.'
        else:
            msg = 'added to this team.'
        if len(data['teams']) > 1:
            msg = "have been %s" % msg
        else:
            msg = "has been %s" % msg
        team_names = ', '.join(team.displayname for team in data['teams'])
        self.request.response.addInfoNotification("%s %s" % (team_names, msg))


class TeamLeaveView(PersonView):

    def processForm(self):
        if self.request.method != "POST" or not self.userCanRequestToLeave():
            # Nothing to do
            return

        if self.request.form.get('leave'):
            self.user.leave(self.context)

        self.request.response.redirect('./')


class PersonEditEmailsView(LaunchpadFormView):
    """A view for editing a person's email settings.

    The user can associate emails with their account, verify emails
    the system associated with their account, and remove associated
    emails.
    """

    schema = IEmailAddress

    custom_widget('VALIDATED_SELECTED', LaunchpadRadioWidget,
                  orientation='vertical')
    custom_widget('UNVALIDATED_SELECTED', LaunchpadRadioWidget,
                  orientation='vertical')
    custom_widget('mailing_list_auto_subscribe_policy',
                  LaunchpadRadioWidgetWithDescription)

    def setUpFields(self):
        """Set up fields for this view.

        The main fields of interest are the selection fields with custom
        vocabularies for the lists of validated and unvalidated email
        addresses.
        """
        super(PersonEditEmailsView, self).setUpFields()
        self.form_fields = (self._validated_emails_field() +
                            self._unvalidated_emails_field() +
                            FormFields(TextLine(__name__='newemail',
                                                title=u'Add a new address'))
                            + self._mailing_list_fields()
                            + self._autosubscribe_policy_fields())

    @property
    def initial_values(self):
        """Set up default values for the radio widgets.

        A radio widget must have a selected value, so we select the
        first unvalidated and validated email addresses in the lists
        to be the default for the corresponding widgets.

        The only exception is if the user has a preferred email
        address: then, that address is used as the default validated
        email address.
        """
        # Defaults for the user's email addresses.
        validated = self.context.preferredemail
        if validated is None and self.context.validatedemails.count() > 0:
            validated = self.context.validatedemails[0]
        unvalidated = self.unvalidated_addresses
        if len(unvalidated) > 0:
            unvalidated = unvalidated.pop()
        initial = dict(VALIDATED_SELECTED=validated,
                       UNVALIDATED_SELECTED=unvalidated)

        # Defaults for the mailing list autosubscribe buttons.
        policy = self.context.mailing_list_auto_subscribe_policy
        initial.update(mailing_list_auto_subscribe_policy=policy)

        return initial

    def setUpWidgets(self, context=None):
        """See `LaunchpadFormView`."""
        super(PersonEditEmailsView, self).setUpWidgets(context)
        widget = self.widgets['mailing_list_auto_subscribe_policy']
        widget.display_label = False

    def _validated_emails_field(self):
        """Create a field with a vocabulary of validated emails.

        :return: A Choice field containing the list of validated emails
        """
        terms = [SimpleTerm(term, term.email)
                 for term in self.context.validatedemails]
        preferred = self.context.preferredemail
        if preferred:
            terms.insert(0, SimpleTerm(preferred, preferred.email))

        return FormFields(
            Choice(__name__='VALIDATED_SELECTED',
                   title=_('These addresses are confirmed as being yours'),
                   source=SimpleVocabulary(terms),
                   ),
            custom_widget = self.custom_widgets['VALIDATED_SELECTED'])

    def _unvalidated_emails_field(self):
        """Create a field with a vocabulary of unvalidated and guessed emails.

        :return: A Choice field containing the list of emails
        """
        terms = []
        for term in self.unvalidated_addresses:
            if isinstance(term, unicode):
                term = SimpleTerm(term)
            else:
                term = SimpleTerm(term, term.email)
            terms.append(term)
        if self.validated_addresses:
            title = _('These addresses may also be yours')
        else:
            title = _('These addresses may be yours')

        return FormFields(
            Choice(__name__='UNVALIDATED_SELECTED', title=title,
                   source=SimpleVocabulary(terms)),
            custom_widget = self.custom_widgets['UNVALIDATED_SELECTED'])

    def _mailing_list_subscription_type(self, mailing_list):
        """Return the context user's subscription type for the given list.

        This is 'Preferred address' if the user is subscribed using her
        preferred address and 'Don't subscribe' if the user is not
        subscribed at all. Otherwise it's the EmailAddress under
        which the user is subscribed to this mailing list.
        """
        subscription = mailing_list.getSubscription(self.context)
        if subscription is not None:
            if subscription.email_address is None:
                return "Preferred address"
            else:
                return subscription.email_address
        else:
            return "Don't subscribe"

    def _mailing_list_fields(self):
        """Creates a field for each mailing list the user can subscribe to.

        If a team doesn't have a mailing list, or the mailing list
        isn't usable, it's not included.
        """
        mailing_list_set = getUtility(IMailingListSet)
        fields = []
        terms = [SimpleTerm("Preferred address"),
                 SimpleTerm("Don't subscribe")]
        terms += [SimpleTerm(email, email.email)
                   for email in self.validated_addresses]
        for team in self.context.teams_participated_in:
            mailing_list = mailing_list_set.get(team.name)
            if mailing_list is not None and mailing_list.isUsable():
                name = 'subscription.%s' % team.name
                value = self._mailing_list_subscription_type(mailing_list)
                field = Choice(__name__=name,
                               title=team.name,
                               source=SimpleVocabulary(terms), default=value)
                fields.append(field)
        return FormFields(*fields)

    def _autosubscribe_policy_fields(self):
        """Create a field for each mailing list auto-subscription option."""
        return FormFields(
            Choice(__name__='mailing_list_auto_subscribe_policy',
                   title=_('When should launchpad automatically subscribe '
                           'you to a team&#x2019;s mailing list?'),
                   source=MailingListAutoSubscribePolicy),
            custom_widget=self.custom_widgets[
                    'mailing_list_auto_subscribe_policy'])

    @property
    def mailing_list_widgets(self):
        """Return all the mailing list subscription widgets."""
        return [widget for widget in self.widgets
                if 'field.subscription.' in widget.name]

    def _validate_selected_address(self, data, field='VALIDATED_SELECTED'):
        """A generic validator for this view's actions.

        Makes sure one (and only one) email address is selected and that
        the selected address belongs to the context person. The address may
        be represented by an EmailAddress object or (for unvalidated
        addresses) a LoginToken object.
        """
        self.validate_widgets(data, [field])

        email = data.get(field)
        if email is None:
            return None
        elif isinstance(data[field], list):
            self.addError("You must not select more than one address.")
            return None

        # Make sure the selected address or login token actually
        # belongs to this person.
        if IEmailAddress.providedBy(email):
            person = email.person

            assert person == self.context, (
                "differing ids in emailaddress.person.id(%s,%d) == "
                "self.context.id(%s,%d) (%s)"
                % (person.name, person.id, self.context.name, self.context.id,
                   email.email))
        elif isinstance(email, unicode):
            tokenset = getUtility(ILoginTokenSet)
            email = tokenset.searchByEmailRequesterAndType(
                email, self.context, LoginTokenType.VALIDATEEMAIL)
            assert email is not None, "Couldn't find login token!"
        else:
            raise AssertionError("Selected address was not EmailAddress "
                                 "or unicode string!")

        # Return the EmailAddress/LoginToken object for use in any
        # further validation.
        return email

    @property
    def validated_addresses(self):
        """All of this person's validated email addresses, including
        their preferred address (if any).
        """
        addresses = []
        if self.context.preferredemail:
            addresses.append(self.context.preferredemail)
        addresses += [email for email in self.context.validatedemails]
        return addresses

    @property
    def unvalidated_addresses(self):
        """All of this person's unvalidated and guessed emails.

        The guessed emails will be EmailAddress objects, and the
        unvalidated emails will be unicode strings.
        """
        emailset = set(self.context.unvalidatedemails)
        emailset = emailset.union(
            [guessed for guessed in self.context.guessedemails
             if not guessed.email in emailset])
        return emailset

    # Actions to do with validated email addresses.

    def validate_action_remove_validated(self, action, data):
        """Make sure the user selected an email address to remove."""
        emailaddress = self._validate_selected_address(data,
                                                       'VALIDATED_SELECTED')
        if emailaddress is None:
            return self.errors

        if self.context.preferredemail == emailaddress:
            self.addError(
                "You can't remove %s because it's your contact email "
                "address." % self.context.preferredemail.email)
            return self.errors
        return self.errors

    @action(_("Remove"), name="remove_validated",
            validator=validate_action_remove_validated)
    def action_remove_validated(self, action, data):
        """Delete the selected (validated) email address."""
        emailaddress = data['VALIDATED_SELECTED']
        emailaddress.destroySelf()
        self.request.response.addInfoNotification(
            "The email address '%s' has been removed." % emailaddress.email)
        self.next_url = self.action_url

    def validate_action_set_preferred(self, action, data):
        """Make sure the user selected an address."""
        emailaddress = self._validate_selected_address(data,
                                                       'VALIDATED_SELECTED')
        if emailaddress is None:
            return self.errors

        if emailaddress.status == EmailAddressStatus.PREFERRED:
            self.request.response.addInfoNotification(
                "%s is already set as your contact address." % (
                    emailaddress.email))
        return self.errors

    @action(_("Set as Contact Address"), name="set_preferred",
            validator=validate_action_set_preferred)
    def action_set_preferred(self, action, data):
        """Set the selected email as preferred for the person in context."""
        emailaddress = data['VALIDATED_SELECTED']
        if emailaddress.status != EmailAddressStatus.PREFERRED:
            self.context.setPreferredEmail(emailaddress)
            self.request.response.addInfoNotification(
                "Your contact address has been changed to: %s" % (
                    emailaddress.email))
        self.next_url = self.action_url

    # Actions to do with unvalidated email addresses.

    def validate_action_confirm(self, action, data):
        """Make sure the user selected an email address to confirm."""
        self._validate_selected_address(data, 'UNVALIDATED_SELECTED')
        return self.errors

    @action(_('Confirm'), name='validate', validator=validate_action_confirm)
    def action_confirm(self, action, data):
        """Mail a validation URL to the selected email address."""
        email = data['UNVALIDATED_SELECTED']
        if IEmailAddress.providedBy(email):
            email = email.email
        token = getUtility(ILoginTokenSet).new(
                    self.context, getUtility(ILaunchBag).login, email,
                    LoginTokenType.VALIDATEEMAIL)
        token.sendEmailValidationRequest(self.request.getApplicationURL())
        self.request.response.addInfoNotification(
            "An e-mail message was sent to '%s' with "
            "instructions on how to confirm that "
            "it belongs to you." % email)
        self.next_url = self.action_url

    def validate_action_remove_unvalidated(self, action, data):
        """Make sure the user selected an email address to remove."""
        email = self._validate_selected_address(data, 'UNVALIDATED_SELECTED')
        if email is not None and IEmailAddress.providedBy(email):
            assert self.context.preferredemail.id != email.id
        return self.errors

    @action(_("Remove"), name="remove_unvalidated",
            validator=validate_action_remove_unvalidated)
    def action_remove_unvalidated(self, action, data):
        """Delete the selected (un-validated) email address.

        This selected address can be either on the EmailAddress table
        marked with status NEW, or in the LoginToken table.
        """
        emailaddress = data['UNVALIDATED_SELECTED']
        if IEmailAddress.providedBy(emailaddress):
            emailaddress.destroySelf()
            email = emailaddress.email
        elif isinstance(emailaddress, unicode):
            logintokenset = getUtility(ILoginTokenSet)
            logintokenset.deleteByEmailRequesterAndType(
                emailaddress, self.context, LoginTokenType.VALIDATEEMAIL)
            email = emailaddress
        else:
            raise AssertionError("Selected address was not EmailAddress "
                                 "or Unicode string!")

        self.request.response.addInfoNotification(
            "The email address '%s' has been removed." % email)
        self.next_url = self.action_url

    # Actions to do with new email addresses

    def validate_action_add_email(self, action, data):
        """Make sure the user entered a valid email address.

        The email address must be syntactically valid and must not already
        be in use.
        """
        has_errors = bool(self.validate_widgets(data, ['newemail']))
        if has_errors:
            # We know that 'newemail' is empty.
            return self.errors

        newemail = data['newemail']
        if not valid_email(newemail):
            self.addError(
                "'%s' doesn't seem to be a valid email address." % newemail)
            return self.errors

        email = getUtility(IEmailAddressSet).getByEmail(newemail)
        person = self.context
        if email is not None:
            if email.person == person:
                self.addError(
                    "The email address '%s' is already registered as your "
                    "email address. This can be either because you already "
                    "added this email address before or because our system "
                    "detected it as being yours. If it was detected by our "
                    "system, it's probably shown on this page and is waiting "
                    "to be confirmed as yours." % email.email)
            else:
                owner = email.person
                owner_name = urllib.quote(owner.name)
                merge_url = (
                    '%s/+requestmerge?field.dupeaccount=%s'
                    % (canonical_url(getUtility(IPersonSet)), owner_name))
                self.addError(
                    structured(
                    "The email address '%s' is already registered to "
                    '<a href="%s">%s</a>. If you think that is a '
                    'duplicated account, you can <a href="%s">merge it</a> '
                    "into your account. ",
                    email.email,
                    canonical_url(owner),
                    owner.browsername,
                    merge_url))
        return self.errors

    @action(_("Add"), name="add_email", validator=validate_action_add_email)
    def action_add_email(self, action, data):
        """Register a new email for the person in context."""
        newemail = data['newemail']
        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(
                    self.context, getUtility(ILaunchBag).login, newemail,
                    LoginTokenType.VALIDATEEMAIL)
        token.sendEmailValidationRequest(self.request.getApplicationURL())

        self.request.response.addInfoNotification(
                "A confirmation message has been sent to '%s'. "
                "Follow the instructions in that message to confirm that the "
                "address is yours. "
                "(If the message doesn't arrive in a few minutes, your mail "
                "provider might use 'greylisting', which could delay the "
                "message for up to an hour or two.)" % newemail)
        self.next_url = self.action_url

    # Actions to do with subscription management.

    def validate_action_update_subscriptions(self, action, data):
        """Make sure the user is subscribing using a valid address.

        Valid addresses are the ones presented as options for the mailing
        list widgets.
        """
        names = [w.context.getName() for w in self.mailing_list_widgets]
        self.validate_widgets(data, names)
        return self.errors

    @action(_("Update Subscriptions"), name="update_subscriptions",
            validator=validate_action_update_subscriptions)
    def action_update_subscriptions(self, action, data):
        """Change the user's mailing list subscriptions."""
        mailing_list_set = getUtility(IMailingListSet)
        dirty = False
        prefix_length = len('subscription.')
        for widget in self.mailing_list_widgets:
            mailing_list_name = widget.context.getName()[prefix_length:]
            mailing_list = mailing_list_set.get(mailing_list_name)
            new_value = data[widget.context.getName()]
            old_value = self._mailing_list_subscription_type(mailing_list)
            if IEmailAddress.providedBy(new_value):
                new_value_string = new_value.email
            else:
                new_value_string = new_value
            if new_value_string != old_value:
                dirty = True
                if new_value == "Don't subscribe":
                    # Delete the subscription.
                    mailing_list.unsubscribe(self.context)
                else:
                    if new_value == "Preferred address":
                        # If the user is subscribed but not under any
                        # particular address, her current preferred
                        # address will always be used.
                        new_value = None
                    subscription = mailing_list.getSubscription(self.context)
                    if subscription is None:
                        mailing_list.subscribe(self.context, new_value)
                    else:
                        mailing_list.changeAddress(self.context, new_value)
        if dirty:
            self.request.response.addInfoNotification(
                "Subscriptions updated.")
        self.next_url = self.action_url

    def validate_action_update_autosubscribe_policy(self, action, data):
        """Ensure that the requested auto-subscribe setting is valid."""
        # XXX mars 2008-04-27:
        # This validator appears pointless and untestable, but it is
        # required for LaunchpadFormView to tell apart the three <form>
        # elements on the page.  See bug #223303.

        widget = self.widgets['mailing_list_auto_subscribe_policy']
        self.validate_widgets(data, widget.name)
        return self.errors

    @action(
        _('Update Policy'),
        name="update_autosubscribe_policy",
        validator=validate_action_update_autosubscribe_policy)
    def action_update_autosubscribe_policy(self, action, data):
        newpolicy = data['mailing_list_auto_subscribe_policy']
        self.context.mailing_list_auto_subscribe_policy = newpolicy
        self.request.response.addInfoNotification(
            'Your auto-subscription policy has been updated.')
        self.next_url = self.action_url


class TeamReassignmentView(ObjectReassignmentView):

    ownerOrMaintainerAttr = 'teamowner'
    schema = ITeamReassignment

    def __init__(self, context, request):
        ObjectReassignmentView.__init__(self, context, request)
        self.callback = self._addOwnerAsMember

    @property
    def contextName(self):
        return self.context.browsername

    def _addOwnerAsMember(self, team, oldOwner, newOwner):
        """Add the new and the old owners as administrators of the team.

        When a user creates a new team, he is added as an administrator of
        that team. To be consistent with this, we must make the new owner an
        administrator of the team. This rule is ignored only if the new owner
        is an inactive member of the team, as that means he's not interested
        in being a member. The same applies to the old owner.
        """
        # Both new and old owners won't be added as administrators of the team
        # only if they're inactive members. If they're either active or
        # proposed members they'll be made administrators of the team.
        if newOwner not in team.inactivemembers:
            team.addMember(
                newOwner, reviewer=oldOwner,
                status=TeamMembershipStatus.ADMIN, force_team_add=True)
        if oldOwner not in team.inactivemembers:
            team.addMember(
                oldOwner, reviewer=oldOwner,
                status=TeamMembershipStatus.ADMIN, force_team_add=True)


class PersonLatestQuestionsView(LaunchpadView):
    """View used by the porlet displaying the latest questions made by
    a person.
    """

    @cachedproperty
    def getLatestQuestions(self, quantity=5):
        """Return <quantity> latest questions created for this target. """
        return self.context.searchQuestions(
            participation=QuestionParticipation.OWNER)[:quantity]


class PersonSearchQuestionsView(SearchQuestionsView):
    """View used to search and display questions in which an IPerson is
    involved.
    """

    display_target_column = True

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        return _('Questions involving $name',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        return _('No questions  involving $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class SearchAnsweredQuestionsView(SearchQuestionsView):
    """View used to search and display questions answered by an IPerson."""

    display_target_column = True

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(participation=QuestionParticipation.ANSWERER)

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        return _('Questions answered by $name',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        return _('No questions answered by $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class SearchAssignedQuestionsView(SearchQuestionsView):
    """View used to search and display questions assigned to an IPerson."""

    display_target_column = True

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(participation=QuestionParticipation.ASSIGNEE)

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        return _('Questions assigned to $name',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        return _('No questions assigned to $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class SearchCommentedQuestionsView(SearchQuestionsView):
    """View used to search and show questions commented on by an IPerson."""

    display_target_column = True

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(participation=QuestionParticipation.COMMENTER)

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        return _('Questions commented on by $name ',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        return _('No questions commented on by $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class SearchCreatedQuestionsView(SearchQuestionsView):
    """View used to search and display questions created by an IPerson."""

    display_target_column = True

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(participation=QuestionParticipation.OWNER)

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        return _('Questions asked by $name',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        return _('No questions asked by $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class SearchNeedAttentionQuestionsView(SearchQuestionsView):
    """View used to search and show questions needing an IPerson attention."""

    display_target_column = True

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(needs_attention=True)

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        return _("Questions needing $name's attention",
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        return _("No questions need $name's attention.",
                 mapping=dict(name=self.context.displayname))


class SearchSubscribedQuestionsView(SearchQuestionsView):
    """View used to search and show questions subscribed to by an IPerson."""

    display_target_column = True

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(participation=QuestionParticipation.SUBSCRIBER)

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        return _('Questions $name is subscribed to',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        return _('No questions subscribed to by $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class PersonAnswerContactForView(LaunchpadView):
    """View used to show all the IQuestionTargets that an IPerson is an answer
    contact for.
    """

    @cachedproperty
    def direct_question_targets(self):
        """List of targets that the IPerson is a direct answer contact.

        Return a list of IQuestionTargets sorted alphabetically by title.
        """
        return sorted(
            self.context.getDirectAnswerQuestionTargets(),
            key=attrgetter('title'))

    @cachedproperty
    def team_question_targets(self):
        """List of IQuestionTargets for the context's team membership.

        Sorted alphabetically by title.
        """
        return sorted(
            self.context.getTeamAnswerQuestionTargets(),
            key=attrgetter('title'))

    def showRemoveYourselfLink(self):
        """The link is shown when the page is in the user's own profile."""
        return self.user == self.context


class PersonAnswersMenu(ApplicationMenu):

    usedfor = IPerson
    facet = 'answers'
    links = ['answered', 'assigned', 'created', 'commented', 'need_attention',
             'subscribed', 'answer_contact_for']

    def answer_contact_for(self):
        summary = "Projects for which %s is an answer contact for" % (
            self.context.displayname)
        return Link('+answer-contact-for', 'Answer contact for', summary)

    def answered(self):
        summary = 'Questions answered by %s' % self.context.displayname
        return Link(
            '+answeredquestions', 'Answered', summary, icon='question')

    def assigned(self):
        summary = 'Questions assigned to %s' % self.context.displayname
        return Link(
            '+assignedquestions', 'Assigned', summary, icon='question')

    def created(self):
        summary = 'Questions asked by %s' % self.context.displayname
        return Link('+createdquestions', 'Asked', summary, icon='question')

    def commented(self):
        summary = 'Questions commented on by %s' % (
            self.context.displayname)
        return Link(
            '+commentedquestions', 'Commented', summary, icon='question')

    def need_attention(self):
        summary = 'Questions needing %s attention' % (
            self.context.displayname)
        return Link('+needattentionquestions', 'Need attention', summary,
                    icon='question')

    def subscribed(self):
        text = 'Subscribed'
        summary = 'Questions subscribed to by %s' % (
                self.context.displayname)
        return Link('+subscribedquestions', text, summary, icon='question')


class PersonBranchesView(BranchListingView):
    """View for branch listing for a person."""

    heading_template = 'Bazaar branches related to %(displayname)s'

    def _branches(self, lifecycle_status, show_dormant):
        return getUtility(IBranchSet).getBranchesForPerson(
            self.context, lifecycle_status, self.user, self.sort_by,
            show_dormant)

    @cachedproperty
    def _subscribed_branches(self):
        return set(getUtility(IBranchSet).getBranchesSubscribedByPerson(
            self.context, [], self.user))


class PersonRegisteredBranchesView(BranchListingView):
    """View for branch listing for a person's registered branches."""

    heading_template = 'Bazaar branches registered by %(displayname)s'
    no_sort_by = (BranchListingSort.REGISTRANT,)

    def _branches(self, lifecycle_status, show_dormant):
        return getUtility(IBranchSet).getBranchesRegisteredByPerson(
            self.context, lifecycle_status, self.user, self.sort_by,
            show_dormant)


class PersonOwnedBranchesView(BranchListingView):
    """View for branch listing for a person's owned branches."""

    heading_template = 'Bazaar branches owned by %(displayname)s'
    no_sort_by = (BranchListingSort.REGISTRANT,)

    def _branches(self, lifecycle_status, show_dormant):
        return getUtility(IBranchSet).getBranchesRegisteredByPerson(
            self.context, lifecycle_status, self.user, self.sort_by,
            show_dormant)


class PersonSubscribedBranchesView(BranchListingView):
    """View for branch listing for a person's subscribed branches."""

    heading_template = 'Bazaar branches subscribed to by %(displayname)s'

    def _branches(self, lifecycle_status, show_dormant):
        return getUtility(IBranchSet).getBranchesSubscribedByPerson(
            self.context, lifecycle_status, self.user, self.sort_by,
            show_dormant)


class PersonTeamBranchesView(LaunchpadView):
    """View for team branches portlet."""

    @cachedproperty
    def teams_with_branches(self):
        return [team for team in self.context.teams_participated_in
                if team.branches.count() > 0 and team != self.context]


class PersonOAuthTokensView(LaunchpadView):
    """Where users can see/revoke their non-expired access tokens."""

    def initialize(self):
        # Store the (sorted) list of access tokens that are going to be
        # used in the template.
        self.tokens = sorted(
            self.context.oauth_access_tokens,
            key=lambda token: token.consumer.key)
        if self.request.method == 'POST':
            self.expireToken()

    def expireToken(self):
        """Expire the token with the key contained in the request's form."""
        form = self.request.form
        consumer = getUtility(IOAuthConsumerSet).getByKey(
            form.get('consumer_key'))
        token = consumer.getAccessToken(form.get('token_key'))
        if token is not None:
            token.date_expires = datetime.now(pytz.timezone('UTC'))
            self.request.response.addInfoNotification(
                "Authorization revoked successfully.")
            self.request.response.redirect(canonical_url(self.user))
        else:
            self.request.response.addInfoNotification(
                "Couldn't find authorization given to %s. Maybe it has been "
                "revoked already?" % consumer.key)
