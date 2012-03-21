# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

from testtools.matchers import (
    LessThan,
    MatchesStructure,
    )

import transaction
from zope.component import getUtility
from zope.interface.exceptions import Invalid
from zope.security.proxy import removeSecurityProxy

from lp.blueprints.enums import SpecificationPriority
from lp.registry.enums import PersonTransferJobType
from lp.registry.errors import (
    JoinNotAllowed,
    TeamSubscriptionPolicyError,
    )
from lp.registry.interfaces.mailinglist import MailingListStatus
from lp.registry.interfaces.person import (
    CLOSED_TEAM_POLICY,
    IPersonSet,
    ITeamPublic,
    OPEN_TEAM_POLICY,
    PersonVisibility,
    TeamMembershipRenewalPolicy,
    TeamSubscriptionPolicy,
    )
from lp.registry.interfaces.teammembership import TeamMembershipStatus
from lp.registry.model.distributionsourcepackage import (
    DistributionSourcePackage,
    )
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import GenericWorkItem
from lp.registry.model.persontransferjob import PersonTransferJob
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.sourcepackage import SourcePackage
from lp.services.database.sqlbase import flush_database_caches
from lp.services.database.lpstorm import IMasterStore
from lp.services.identity.interfaces.emailaddress import IEmailAddressSet
from lp.services.identity.model.emailaddress import EmailAddress
from lp.services.webapp.publisher import canonical_url
from lp.soyuz.enums import ArchiveStatus
from lp.testing import (
    login_celebrity,
    login_person,
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    FunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount


class TestTeamContactAddress(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def getAllEmailAddresses(self):
        transaction.commit()
        all_addresses = self.store.find(
            EmailAddress, EmailAddress.personID == self.team.id)
        return [address for address in all_addresses.order_by('email')]

    def createMailingListAndGetAddress(self):
        mailing_list = self.factory.makeMailingList(
            self.team, self.team.teamowner)
        return getUtility(IEmailAddressSet).getByEmail(
                mailing_list.address)

    def setUp(self):
        super(TestTeamContactAddress, self).setUp()

        self.team = self.factory.makeTeam(name='alpha')
        self.address = self.factory.makeEmail('team@noplace.org', self.team)
        self.store = IMasterStore(self.address)

    def test_setContactAddress_from_none(self):
        self.team.setContactAddress(self.address)
        self.assertEqual(self.address, self.team.preferredemail)
        self.assertEqual([self.address], self.getAllEmailAddresses())

    def test_setContactAddress_to_none(self):
        self.team.setContactAddress(self.address)
        self.team.setContactAddress(None)
        self.assertEqual(None, self.team.preferredemail)
        self.assertEqual([], self.getAllEmailAddresses())

    def test_setContactAddress_to_new_address(self):
        self.team.setContactAddress(self.address)
        new_address = self.factory.makeEmail('new@noplace.org', self.team)
        self.team.setContactAddress(new_address)
        self.assertEqual(new_address, self.team.preferredemail)
        self.assertEqual([new_address], self.getAllEmailAddresses())

    def test_setContactAddress_to_mailing_list(self):
        self.team.setContactAddress(self.address)
        list_address = self.createMailingListAndGetAddress()
        self.team.setContactAddress(list_address)
        self.assertEqual(list_address, self.team.preferredemail)
        self.assertEqual([list_address], self.getAllEmailAddresses())

    def test_setContactAddress_from_mailing_list(self):
        list_address = self.createMailingListAndGetAddress()
        self.team.setContactAddress(list_address)
        new_address = self.factory.makeEmail('new@noplace.org', self.team)
        self.team.setContactAddress(new_address)
        self.assertEqual(new_address, self.team.preferredemail)
        self.assertEqual(
            [list_address, new_address], self.getAllEmailAddresses())

    def test_setContactAddress_from_mailing_list_to_none(self):
        list_address = self.createMailingListAndGetAddress()
        self.team.setContactAddress(list_address)
        self.team.setContactAddress(None)
        self.assertEqual(None, self.team.preferredemail)
        self.assertEqual([list_address], self.getAllEmailAddresses())

    def test_setContactAddress_with_purged_mailing_list_to_none(self):
        # Purging a mailing list will delete the list address, but this was
        # not always the case. The address will be deleted if it still exists.
        self.createMailingListAndGetAddress()
        naked_mailing_list = removeSecurityProxy(self.team.mailing_list)
        naked_mailing_list.status = MailingListStatus.PURGED
        self.team.setContactAddress(None)
        self.assertEqual(None, self.team.preferredemail)
        self.assertEqual([], self.getAllEmailAddresses())

    def test_setContactAddress_after_purged_mailing_list_and_rename(self):
        # This is the rare case where a list is purged for a team rename,
        # then the contact address is set/unset sometime afterwards.
        # The old mailing list address belongs the team, but not the list.
        # 1. Create then purge a mailing list.
        self.createMailingListAndGetAddress()
        mailing_list = self.team.mailing_list
        mailing_list.deactivate()
        mailing_list.transitionToStatus(MailingListStatus.INACTIVE)
        mailing_list.purge()
        transaction.commit()
        # 2. Rename the team.
        login_celebrity('admin')
        self.team.name = 'beta'
        login_person(self.team.teamowner)
        # 3. Set the contact address.
        self.team.setContactAddress(None)
        self.assertEqual(None, self.team.preferredemail)
        self.assertEqual([], self.getAllEmailAddresses())


class TestTeamGetTeamAdminsEmailAddresses(TestCaseWithFactory):
    """Test the rules of IPerson.getTeamAdminsEmailAddresses()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamGetTeamAdminsEmailAddresses, self).setUp()
        self.team = self.factory.makeTeam(name='finch')
        login_celebrity('admin')

    def test_admin_is_user(self):
        # The team owner is a user and admin who provides the email address.
        email = self.team.teamowner.preferredemail.email
        self.assertEqual([email], self.team.getTeamAdminsEmailAddresses())

    def test_no_admins(self):
        # A team without admins has no email addresses.
        self.team.teamowner.leave(self.team)
        self.assertEqual([], self.team.getTeamAdminsEmailAddresses())

    def test_admins_are_users_with_preferred_email_addresses(self):
        # The team's admins are users, and they provide the email addresses.
        admin = self.factory.makePerson()
        self.team.addMember(admin, self.team.teamowner)
        for membership in self.team.member_memberships:
            membership.setStatus(
                TeamMembershipStatus.ADMIN, self.team.teamowner)
        email_1 = self.team.teamowner.preferredemail.email
        email_2 = admin.preferredemail.email
        self.assertEqual(
            [email_1, email_2], self.team.getTeamAdminsEmailAddresses())

    def setUpAdminingTeam(self, team):
        """Return a new team set as the admin of the provided team."""
        admin_team = self.factory.makeTeam()
        admin_member = self.factory.makePerson()
        admin_team.addMember(admin_member, admin_team.teamowner)
        team.addMember(
            admin_team, team.teamowner, force_team_add=True)
        for membership in team.member_memberships:
            membership.setStatus(
                TeamMembershipStatus.ADMIN, admin_team.teamowner)
        approved_member = self.factory.makePerson()
        team.addMember(approved_member, team.teamowner)
        team.teamowner.leave(team)
        return admin_team

    def test_admins_are_teams_with_preferred_email_addresses(self):
        # The team's admin is a team with a contact address.
        admin_team = self.setUpAdminingTeam(self.team)
        admin_team.setContactAddress(
            self.factory.makeEmail('team@eg.dom', admin_team))
        self.assertEqual(
            ['team@eg.dom'], self.team.getTeamAdminsEmailAddresses())

    def test_admins_are_teams_without_preferred_email_addresses(self):
        # The team's admin is a team without a contact address.
        # The admin team members provide the email addresses.
        admin_team = self.setUpAdminingTeam(self.team)
        emails = sorted(
            m.preferredemail.email for m in admin_team.activemembers)
        self.assertEqual(
            emails, self.team.getTeamAdminsEmailAddresses())


class TestDefaultRenewalPeriodIsRequiredForSomeTeams(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDefaultRenewalPeriodIsRequiredForSomeTeams, self).setUp()
        self.team = self.factory.makeTeam()
        login_person(self.team.teamowner)

    def assertInvalid(self, policy, period):
        self.team.renewal_policy = policy
        self.team.defaultrenewalperiod = period
        self.assertRaises(Invalid, ITeamPublic.validateInvariants, self.team)

    def assertValid(self, policy, period):
        self.team.renewal_policy = policy
        self.team.defaultrenewalperiod = period
        ITeamPublic.validateInvariants(self.team)

    def test_policy_automatic_period_none(self):
        # Automatic policy cannot have a none day period.
        self.assertInvalid(
            TeamMembershipRenewalPolicy.AUTOMATIC, None)

    def test_policy_ondemand_period_none(self):
        # Ondemand policy cannot have a none day period.
        self.assertInvalid(
            TeamMembershipRenewalPolicy.ONDEMAND, None)

    def test_policy_none_period_none(self):
        # None policy can have a None day period.
        self.assertValid(
            TeamMembershipRenewalPolicy.NONE, None)

    def test_policy_requres_period_below_minimum(self):
        # Automatic and ondemand policy cannot have a zero day period.
        self.assertInvalid(
            TeamMembershipRenewalPolicy.AUTOMATIC, 0)

    def test_policy_requres_period_minimum(self):
        # Automatic and ondemand policy can have a 1 day period.
        self.assertValid(
            TeamMembershipRenewalPolicy.AUTOMATIC, 1)

    def test_policy_requres_period_maximum(self):
        # Automatic and ondemand policy cannot have a 3650 day max value.
        self.assertValid(
            TeamMembershipRenewalPolicy.AUTOMATIC, 3650)

    def test_policy_requres_period_over_maximum(self):
        # Automatic and ondemand policy cannot have a 3650 day max value.
        self.assertInvalid(
            TeamMembershipRenewalPolicy.AUTOMATIC, 3651)


class TestDefaultMembershipPeriod(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDefaultMembershipPeriod, self).setUp()
        self.team = self.factory.makeTeam()
        login_person(self.team.teamowner)

    def test_default_membership_period_over_maximum(self):
        self.assertRaises(
            Invalid, ITeamPublic['defaultmembershipperiod'].validate, 3651)

    def test_default_membership_period_none(self):
        ITeamPublic['defaultmembershipperiod'].validate(None)

    def test_default_membership_period_zero(self):
        ITeamPublic['defaultmembershipperiod'].validate(0)

    def test_default_membership_period_maximum(self):
        ITeamPublic['defaultmembershipperiod'].validate(3650)


class TestTeamSubscriptionPolicyError(TestCaseWithFactory):
    """Test `TeamSubscriptionPolicyError` messages."""

    layer = FunctionalLayer

    def test_default_message(self):
        error = TeamSubscriptionPolicyError()
        self.assertEqual('Team Subscription Policy Error', error.message)

    def test_str(self):
        # The string is the error message.
        error = TeamSubscriptionPolicyError('a message')
        self.assertEqual('a message', str(error))

    def test_doc(self):
        # The doc() method returns the message.  It is called when rendering
        # an error in the UI. eg structure error.
        error = TeamSubscriptionPolicyError('a message')
        self.assertEqual('a message', error.doc())


class TeamSubscriptionPolicyBase(TestCaseWithFactory):
    """`TeamSubsciptionPolicyChoice` base test class."""

    layer = DatabaseFunctionalLayer
    POLICY = None

    def setUpTeams(self, other_policy=None):
        if other_policy is None:
            other_policy = self.POLICY
        self.team = self.factory.makeTeam(subscription_policy=self.POLICY)
        self.other_team = self.factory.makeTeam(
            subscription_policy=other_policy, owner=self.team.teamowner)
        self.field = ITeamPublic['subscriptionpolicy'].bind(self.team)
        login_person(self.team.teamowner)


class TestTeamSubscriptionPolicyChoiceCommon(TeamSubscriptionPolicyBase):
    """Test `TeamSubsciptionPolicyChoice` constraints."""

    # Any policy will work here, so we'll just pick one.
    POLICY = TeamSubscriptionPolicy.MODERATED

    def test___getTeam_with_team(self):
        # _getTeam returns the context team for team updates.
        self.setUpTeams()
        self.assertEqual(self.team, self.field._getTeam())

    def test___getTeam_with_person_set(self):
        # _getTeam returns the context person set for team creation.
        person_set = getUtility(IPersonSet)
        field = ITeamPublic['subscriptionpolicy'].bind(person_set)
        self.assertEqual(None, field._getTeam())


class TestTeamSubscriptionPolicyChoiceModerated(TeamSubscriptionPolicyBase):
    """Test `TeamSubsciptionPolicyChoice` Moderated constraints."""

    POLICY = TeamSubscriptionPolicy.MODERATED

    def test_closed_team_with_closed_super_team_cannot_become_open(self):
        # The team cannot compromise the membership of the super team
        # by becoming open. The user must remove his team from the super team
        # first.
        self.setUpTeams()
        self.other_team.addMember(self.team, self.team.teamowner)
        self.assertFalse(
            self.field.constraint(TeamSubscriptionPolicy.OPEN))
        self.assertRaises(
            TeamSubscriptionPolicyError, self.field.validate,
            TeamSubscriptionPolicy.OPEN)

    def test_closed_team_with_open_super_team_can_become_open(self):
        # The team can become open if its super teams are open.
        self.setUpTeams(other_policy=TeamSubscriptionPolicy.OPEN)
        self.other_team.addMember(self.team, self.team.teamowner)
        self.assertTrue(
            self.field.constraint(TeamSubscriptionPolicy.OPEN))
        self.assertEqual(
            None, self.field.validate(TeamSubscriptionPolicy.OPEN))

    def test_closed_team_can_change_to_another_closed_policy(self):
        # A closed team can change between the two closed polcies.
        self.setUpTeams()
        self.team.addMember(self.other_team, self.team.teamowner)
        super_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED,
            owner=self.team.teamowner)
        super_team.addMember(self.team, self.team.teamowner)
        self.assertTrue(
            self.field.constraint(TeamSubscriptionPolicy.RESTRICTED))
        self.assertEqual(
            None, self.field.validate(TeamSubscriptionPolicy.RESTRICTED))

    def test_closed_team_with_active_ppas_cannot_become_open(self):
        # The team cannot become open if it has PPA because it compromises the
        # the control of who can upload.
        self.setUpTeams()
        self.team.createPPA()
        self.assertFalse(
            self.field.constraint(TeamSubscriptionPolicy.OPEN))
        self.assertRaises(
            TeamSubscriptionPolicyError, self.field.validate,
            TeamSubscriptionPolicy.OPEN)

    def test_closed_team_without_active_ppas_can_become_open(self):
        # The team can become if it has deleted PPAs.
        self.setUpTeams(other_policy=TeamSubscriptionPolicy.MODERATED)
        ppa = self.team.createPPA()
        ppa.delete(self.team.teamowner)
        removeSecurityProxy(ppa).status = ArchiveStatus.DELETED
        self.assertTrue(
            self.field.constraint(TeamSubscriptionPolicy.OPEN))
        self.assertEqual(
            None, self.field.validate(TeamSubscriptionPolicy.OPEN))

    def test_closed_team_with_private_bugs_cannot_become_open(self):
        # The team cannot become open if it is subscribed to private bugs.
        self.setUpTeams()
        bug = self.factory.makeBug(owner=self.team.teamowner, private=True)
        with person_logged_in(self.team.teamowner):
            bug.subscribe(self.team, self.team.teamowner)
        self.assertFalse(
            self.field.constraint(TeamSubscriptionPolicy.OPEN))
        self.assertRaises(
            TeamSubscriptionPolicyError, self.field.validate,
            TeamSubscriptionPolicy.OPEN)

    def test_closed_team_with_private_bugs_assigned_cannot_become_open(self):
        # The team cannot become open if it is assigned private bugs.
        self.setUpTeams()
        bug = self.factory.makeBug(owner=self.team.teamowner, private=True)
        with person_logged_in(self.team.teamowner):
            bug.default_bugtask.transitionToAssignee(self.team)
        self.assertFalse(
            self.field.constraint(TeamSubscriptionPolicy.OPEN))
        self.assertRaises(
            TeamSubscriptionPolicyError, self.field.validate,
            TeamSubscriptionPolicy.OPEN)

    def test_closed_team_owning_a_pillar_cannot_become_open(self):
        # The team cannot become open if it owns a pillar.
        self.setUpTeams()
        self.factory.makeProduct(owner=self.team)
        self.assertFalse(
            self.field.constraint(TeamSubscriptionPolicy.OPEN))
        self.assertRaises(
            TeamSubscriptionPolicyError, self.field.validate,
            TeamSubscriptionPolicy.OPEN)

    def test_closed_team_security_contact_cannot_become_open(self):
        # The team cannot become open if it is a security contact.
        self.setUpTeams()
        self.factory.makeProduct(security_contact=self.team)
        self.assertFalse(
            self.field.constraint(TeamSubscriptionPolicy.OPEN))
        self.assertRaises(
            TeamSubscriptionPolicyError, self.field.validate,
            TeamSubscriptionPolicy.OPEN)


class TestTeamSubscriptionPolicyChoiceRestrcted(
                                   TestTeamSubscriptionPolicyChoiceModerated):
    """Test `TeamSubsciptionPolicyChoice` Restricted constraints."""

    POLICY = TeamSubscriptionPolicy.RESTRICTED


class TestTeamSubscriptionPolicyChoiceOpen(TeamSubscriptionPolicyBase):
    """Test `TeamSubsciptionPolicyChoice` Open constraints."""

    POLICY = TeamSubscriptionPolicy.OPEN

    def test_open_team_with_open_sub_team_cannot_become_closed(self):
        # The team cannot become closed if its membership will be
        # compromised by an open subteam. The user must remove the subteam
        # first
        self.setUpTeams()
        self.team.addMember(self.other_team, self.team.teamowner)
        self.assertFalse(
            self.field.constraint(TeamSubscriptionPolicy.MODERATED))
        self.assertRaises(
            TeamSubscriptionPolicyError, self.field.validate,
            TeamSubscriptionPolicy.MODERATED)

    def test_open_team_with_closed_sub_team_can_become_closed(self):
        # The team can become closed.
        self.setUpTeams(other_policy=TeamSubscriptionPolicy.MODERATED)
        self.team.addMember(self.other_team, self.team.teamowner)
        self.assertTrue(
            self.field.constraint(TeamSubscriptionPolicy.MODERATED))
        self.assertEqual(
            None, self.field.validate(TeamSubscriptionPolicy.MODERATED))


class TestTeamSubscriptionPolicyChoiceDelegated(
                                        TestTeamSubscriptionPolicyChoiceOpen):
    """Test `TeamSubsciptionPolicyChoice` Delegated constraints."""

    POLICY = TeamSubscriptionPolicy.DELEGATED


class TestTeamSubscriptionPolicyValidator(TestCaseWithFactory):
    # Test that the subscription policy storm validator stops bad transitions.

    layer = DatabaseFunctionalLayer

    def test_illegal_transition_to_open_subscription(self):
        # Check that TeamSubscriptionPolicyError is raised when an attempt is
        # made to set an illegal open subscription policy on a team.
        team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
        team.createPPA()
        for policy in OPEN_TEAM_POLICY:
            self.assertRaises(
                TeamSubscriptionPolicyError,
                removeSecurityProxy(team).__setattr__,
                "subscriptionpolicy", policy)

    def test_illegal_transition_to_closed_subscription(self):
        # Check that TeamSubscriptionPolicyError is raised when an attempt is
        # made to set an illegal closed subscription policy on a team.
        team = self.factory.makeTeam()
        other_team = self.factory.makeTeam(
            owner=team.teamowner,
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        with person_logged_in(team.teamowner):
            team.addMember(
                other_team, team.teamowner, force_team_add=True)

        for policy in CLOSED_TEAM_POLICY:
            self.assertRaises(
                TeamSubscriptionPolicyError,
                removeSecurityProxy(team).__setattr__,
                "subscriptionpolicy", policy)


class TestVisibilityConsistencyWarning(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestVisibilityConsistencyWarning, self).setUp()
        self.team = self.factory.makeTeam()
        login_celebrity('admin')

    def test_no_warning_for_PersonTransferJob(self):
        # An entry in the PersonTransferJob table does not cause a warning.
        member = self.factory.makePerson()
        metadata = ('some', 'arbitrary', 'metadata')
        PersonTransferJob(
            member, self.team,
            PersonTransferJobType.MEMBERSHIP_NOTIFICATION, metadata)
        self.assertEqual(
            None,
            self.team.visibilityConsistencyWarning(PersonVisibility.PRIVATE))


class TestPersonJoinTeam(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_join_restricted_team_error(self):
        # Calling join with a Restricted team raises an error.
        team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
        user = self.factory.makePerson()
        login_person(user)
        self.assertRaises(JoinNotAllowed, user.join, team, user)

    def test_join_moderated_team_proposed(self):
        # Joining a Moderated team creates a Proposed TeamMembership.
        team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        user = self.factory.makePerson()
        login_person(user)
        user.join(team, user)
        users = list(team.proposedmembers)
        self.assertEqual(1, len(users))
        self.assertEqual(user, users[0])

    def test_join_delegated_team_proposed(self):
        # Joining a Delegated team creates a Proposed TeamMembership.
        team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.DELEGATED)
        user = self.factory.makePerson()
        login_person(user)
        user.join(team, user)
        users = list(team.proposedmembers)
        self.assertEqual(1, len(users))
        self.assertEqual(user, users[0])

    def test_join_open_team_appoved(self):
        # Joining an Open team creates an Approved TeamMembership.
        team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        user = self.factory.makePerson()
        login_person(user)
        user.join(team, user)
        members = list(team.approvedmembers)
        self.assertEqual(1, len(members))
        self.assertEqual(user, members[0])


class Test_getSpecificationWorkItemsDueBefore(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(Test_getSpecificationWorkItemsDueBefore, self).setUp()
        # We remove the security proxy from our team because we'll be testing
        # some internal methods.
        self.team = removeSecurityProxy(self.factory.makeTeam())
        today = datetime.today().date()
        next_month = today + timedelta(days=30)
        next_year = today + timedelta(days=366)
        self.current_milestone = self.factory.makeMilestone(
            dateexpected=next_month)
        self.product = self.current_milestone.product
        self.future_milestone = self.factory.makeMilestone(
            dateexpected=next_year, product=self.product)

    def test_basic(self):
        assigned_spec = self.factory.makeSpecification(
            assignee=self.team.teamowner, milestone=self.current_milestone,
            product=self.product)
        # Create a workitem with no explicit assignee/milestone. This way it
        # will inherit the ones from the spec it belongs to.
        workitem = self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=assigned_spec)

        # Create a workitem with somebody who's not a member of our team as
        # the assignee. This workitem must not be in the list returned by
        # _getSpecificationWorkItemsDueBefore().
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 2', specification=assigned_spec,
            assignee=self.factory.makePerson())

        # Create a workitem targeted to a milestone too far in the future.
        # This workitem must not be in the list returned by
        # _getSpecificationWorkItemsDueBefore().
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 3', specification=assigned_spec,
            milestone=self.future_milestone)

        workitems = self.team._getSpecificationWorkItemsDueBefore(
            self.current_milestone.dateexpected)

        self.assertEqual(
            [(workitem, self.current_milestone)], list(workitems))

    def test_skips_workitems_with_milestone_in_the_past(self):
        today = datetime.today().date()
        milestone = self.factory.makeMilestone(
            dateexpected=today - timedelta(days=1))
        spec = self.factory.makeSpecification(
            assignee=self.team.teamowner, milestone=milestone,
            product=milestone.product)
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=spec)

        workitems = self.team._getSpecificationWorkItemsDueBefore(today)

        self.assertEqual([], list(workitems))

    def test_includes_workitems_from_future_spec(self):
        assigned_spec = self.factory.makeSpecification(
            assignee=self.team.teamowner, milestone=self.future_milestone,
            product=self.product)
        # This workitem inherits the spec's milestone and that's too far in
        # the future so it won't be in the returned list.
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=assigned_spec)
        # This one, on the other hand, is explicitly targeted to the current
        # milestone, so it is included in the returned list even though its
        # spec is targeted to the future milestone.
        workitem = self.factory.makeSpecificationWorkItem(
            title=u'workitem 2', specification=assigned_spec,
            milestone=self.current_milestone)

        workitems = self.team._getSpecificationWorkItemsDueBefore(
            self.current_milestone.dateexpected)

        self.assertEqual(
            [(workitem, self.current_milestone)], list(workitems))

    def test_includes_workitems_from_foreign_spec(self):
        # This spec is assigned to a person who's not a member of our team, so
        # only the workitems that are explicitly assigned to a member of our
        # team will be in the returned list.
        foreign_spec = self.factory.makeSpecification(
            assignee=self.factory.makePerson(),
            milestone=self.current_milestone, product=self.product)
        # This one is not explicitly assigned to anyone, so it inherits the
        # assignee of its spec and hence is not in the returned list.
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=foreign_spec)

        # This one, on the other hand, is explicitly assigned to the a member
        # of our team, so it is included in the returned list even though its
        # spec is not assigned to a member of our team.
        workitem = self.factory.makeSpecificationWorkItem(
            title=u'workitem 2', specification=foreign_spec,
            assignee=self.team.teamowner)

        workitems = self.team._getSpecificationWorkItemsDueBefore(
            self.current_milestone.dateexpected)

        self.assertEqual(
            [(workitem, self.current_milestone)], list(workitems))


class Test_getBugTasksDueBefore(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(Test_getBugTasksDueBefore, self).setUp()
        # We remove the security proxy from our team because we'll be testing
        # some internal methods.
        self.team = removeSecurityProxy(self.factory.makeTeam())
        self.today = datetime.today().date()

    def _assignBugTaskToTeamOwner(self, bugtask):
        removeSecurityProxy(bugtask).assignee = self.team.teamowner

    def test_basic(self):
        milestone = self.factory.makeMilestone(dateexpected=self.today)
        # This bug is assigned to a team member and targeted to a milestone
        # whose due date is before the cutoff date we pass in, so it will be
        # included in the return of _getBugTasksDueBefore().
        milestoned_bug = self.factory.makeBug(milestone=milestone)
        self._assignBugTaskToTeamOwner(milestoned_bug.bugtasks[0])
        # This one is assigned to a team member but not milestoned, so it is
        # not included in the return of _getBugTasksDueBefore().
        non_milestoned_bug = self.factory.makeBug()
        self._assignBugTaskToTeamOwner(non_milestoned_bug.bugtasks[0])
        # This one is milestoned but not assigned to a team member, so it is
        # not included in the return of _getBugTasksDueBefore() either.
        non_assigned_bug = self.factory.makeBug()
        self._assignBugTaskToTeamOwner(non_assigned_bug.bugtasks[0])

        bugtasks = list(self.team._getBugTasksDueBefore(
            self.today + timedelta(days=1), user=None))

        self.assertEqual(1, len(bugtasks))
        self.assertEqual(milestoned_bug.bugtasks[0], bugtasks[0])

    def test_skips_tasks_targeted_to_old_milestones(self):
        past_milestone = self.factory.makeMilestone(
            dateexpected=self.today - timedelta(days=1))
        bug = self.factory.makeBug(milestone=past_milestone)
        self._assignBugTaskToTeamOwner(bug.bugtasks[0])

        bugtasks = list(self.team._getBugTasksDueBefore(
            self.today + timedelta(days=1), user=None))

        self.assertEqual(0, len(bugtasks))

    def test_skips_private_bugs_the_user_is_not_allowed_to_see(self):
        milestone = self.factory.makeMilestone(dateexpected=self.today)
        private_bug = removeSecurityProxy(
            self.factory.makeBug(milestone=milestone, private=True))
        self._assignBugTaskToTeamOwner(private_bug.bugtasks[0])
        private_bug2 = removeSecurityProxy(
            self.factory.makeBug(milestone=milestone, private=True))
        self._assignBugTaskToTeamOwner(private_bug2.bugtasks[0])

        bugtasks = list(self.team._getBugTasksDueBefore(
            self.today + timedelta(days=1),
            removeSecurityProxy(private_bug2).owner))

        self.assertEqual(private_bug2.bugtasks, bugtasks)

    def test_skips_distroseries_task_that_is_a_conjoined_master(self):
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        milestone = self.factory.makeMilestone(
            distroseries=distroseries, dateexpected=self.today)
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, sourcepackagename=sourcepackagename)
        bug = self.factory.makeBug(
            milestone=milestone, sourcepackagename=sourcepackagename,
            distribution=distroseries.distribution)
        package = distroseries.getSourcePackage(sourcepackagename.name)
        removeSecurityProxy(bug).addTask(bug.owner, package)
        self.assertEqual(2, len(bug.bugtasks))
        slave, master = bug.bugtasks
        self._assignBugTaskToTeamOwner(master)
        self.assertEqual(None, master.conjoined_master)
        self.assertEqual(master, slave.conjoined_master)
        self.assertEqual(slave.milestone, master.milestone)
        self.assertEqual(slave.assignee, master.assignee)

        bugtasks = list(self.team._getBugTasksDueBefore(
            self.today + timedelta(days=1), user=None))

        self.assertEqual([slave], bugtasks)

    def test_skips_productseries_task_that_is_a_conjoined_master(self):
        milestone = self.factory.makeMilestone(dateexpected=self.today)
        removeSecurityProxy(milestone.product).development_focus = (
            milestone.productseries)
        bug = self.factory.makeBug(
            series=milestone.productseries, milestone=milestone)
        self.assertEqual(2, len(bug.bugtasks))
        slave, master = bug.bugtasks

        # This will cause the assignee to propagate to the other bugtask as
        # well since they're conjoined.
        self._assignBugTaskToTeamOwner(slave)
        self.assertEqual(master, slave.conjoined_master)
        self.assertEqual(slave.milestone, master.milestone)
        self.assertEqual(slave.assignee, master.assignee)

        bugtasks = list(self.team._getBugTasksDueBefore(
            self.today + timedelta(days=1), user=None))

        self.assertEqual([slave], bugtasks)


class Test_getWorkItemsDueBefore(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(Test_getWorkItemsDueBefore, self).setUp()
        self.today = datetime.today().date()
        current_milestone = self.factory.makeMilestone(
            dateexpected=self.today)
        self.current_milestone = current_milestone
        self.future_milestone = self.factory.makeMilestone(
            product=current_milestone.product,
            dateexpected=datetime(2060, 1, 1))
        self.team = self.factory.makeTeam()

    def test_basic(self):
        # TODO: just create a bugtask and a WI to check the return value of
        # the method.
        pass

    def test_foreign_container(self):
        # This spec is targeted to a person who's not a member of our team, so
        # only those workitems that are explicitly assigned to a member of our
        # team will be returned.
        spec = self.factory.makeSpecification(
            product=self.current_milestone.product,
            milestone=self.current_milestone,
            assignee=self.factory.makePerson())
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=spec)
        workitem = self.factory.makeSpecificationWorkItem(
            title=u'workitem 2', specification=spec,
            assignee=self.team.teamowner)

        workitems = self.team.getWorkItemsDueBefore(
            self.current_milestone.dateexpected)

        self.assertEqual(
            [self.current_milestone.dateexpected], workitems.keys())
        containers = workitems[self.current_milestone.dateexpected]
        self.assertEqual(1, len(containers))
        [container] = containers
        self.assertEqual(1, len(container.items))
        self.assertEqual(workitem.title, container.items[0].title)
        self.assertTrue(container.is_foreign)

    def test_future_container(self):
        spec = self.factory.makeSpecification(
            product=self.current_milestone.product,
            assignee=self.team.teamowner)
        # This workitem is targeted to a future milestone so it won't be in
        # our results below.
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=spec,
            milestone=self.future_milestone)
        current_wi = self.factory.makeSpecificationWorkItem(
            title=u'workitem 2', specification=spec,
            milestone=self.current_milestone)

        workitems = self.team.getWorkItemsDueBefore(
            self.current_milestone.dateexpected)

        self.assertEqual(
            [self.current_milestone.dateexpected], workitems.keys())
        containers = workitems[self.current_milestone.dateexpected]
        self.assertEqual(1, len(containers))
        [container] = containers
        self.assertEqual(1, len(container.items))
        self.assertEqual(current_wi.title, container.items[0].title)
        self.assertTrue(container.is_future)

    def test_query_counts(self):
        self._createWorkItems()
        dateexpected = self.current_milestone.dateexpected
        flush_database_caches()
        with StormStatementRecorder() as recorder:
            containers = self.team.getWorkItemsDueBefore(dateexpected)
        # One query to get all team members;
        # One to get all SpecWorkItems;
        # One to get all BugTasks.
        # And one to get the current series of a distribution
        # (Distribution.currentseries) to decide whether or not
        # the bug is part of a conjoined relationship. The code that executes
        # this query runs for every distroseriespackage bugtask but since
        # .currentseries is a cached property and there's a single
        # distribution with bugs in production, this will not cause an extra
        # DB query every time it runs.
        self.assertThat(recorder, HasQueryCount(LessThan(5)))

        with StormStatementRecorder() as recorder:
            for date, containers in containers.items():
                for container in containers:
                    for item in container.items:
                        item.assignee
                        canonical_url(item.assignee)
                        item.status
                        item.priority
                        canonical_url(item.target)
        self.assertThat(recorder, HasQueryCount(LessThan(1)))

    def _createWorkItems(self):
        """Create a bunch of SpecificationWorkItems and BugTasks.

        BE CAREFUL! Using this will make your tests hard to follow because it
        creates a lot of objects and it is not trivial to check that they're
        all returned by getWorkItemsDueBefore() because the objects created
        here are burried two levels deep on the hierarchy returned there.

        This is meant to be used in a test that checks the number of DB
        queries issued by getWorkItemsDueBefore() does not grow according to
        the number of returned objects.
        """
        team = self.team
        current_milestone = self.current_milestone
        future_milestone = self.future_milestone

        # Create a spec assigned to a member of our team and targeted to the
        # current milestone. Also creates a workitem with no explicit
        # assignee/milestone.
        assigned_spec = self.factory.makeSpecification(
            assignee=team.teamowner, milestone=current_milestone,
            product=current_milestone.product)
        self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_assigned_spec', specification=assigned_spec)

        # Create a spec assigned to a member of our team but targeted to a
        # future milestone, together with a workitem targeted to the current
        # milestone.
        future_spec = self.factory.makeSpecification(
            milestone=future_milestone, product=future_milestone.product,
            priority=SpecificationPriority.HIGH, assignee=team.teamowner)
        self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_future_spec assigned to team member',
            specification=future_spec, milestone=current_milestone)

        # Create a spec assigned to nobody and targeted to the current
        # milestone, together with a workitem explicitly assigned to a member
        # of our team.
        foreign_spec = self.factory.makeSpecification(
            milestone=current_milestone, product=current_milestone.product)
        self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_foreign_spec assigned to team member',
            specification=foreign_spec, assignee=team.teamowner)

        # Create a bug targeted to the current milestone and assign it to a
        # member of our team.
        bugtask = self.factory.makeBug(
            milestone=current_milestone).bugtasks[0]
        removeSecurityProxy(bugtask).assignee = team.teamowner

        # Create a BugTask whose target is a ProductSeries
        bugtask2 = self.factory.makeBug(
            series=current_milestone.productseries).bugtasks[1]
        self.assertIsInstance(bugtask2.target, ProductSeries)
        removeSecurityProxy(bugtask2).assignee = team.teamowner
        removeSecurityProxy(bugtask2).milestone = current_milestone

        # Create a BugTask whose target is a DistroSeries
        current_distro_milestone = self.factory.makeMilestone(
            distribution=self.factory.makeDistribution(),
            dateexpected=self.today)
        bugtask3 = self.factory.makeBug(
            series=current_distro_milestone.distroseries).bugtasks[1]
        self.assertIsInstance(bugtask3.target, DistroSeries)
        removeSecurityProxy(bugtask3).assignee = team.teamowner
        removeSecurityProxy(bugtask3).milestone = current_distro_milestone

        # Create a bug with two conjoined BugTasks whose target is a SourcePackage
        distroseries = current_distro_milestone.distroseries
        sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, sourcepackagename=sourcepackagename)
        bug = self.factory.makeBug(
            milestone=current_distro_milestone,
            sourcepackagename=sourcepackagename,
            distribution=distroseries.distribution)
        slave_task = bug.bugtasks[0]
        package = distroseries.getSourcePackage(sourcepackagename.name)
        master_task = removeSecurityProxy(bug).addTask(bug.owner, package)
        self.assertIsInstance(master_task.target, SourcePackage)
        self.assertIsInstance(slave_task.target, DistributionSourcePackage)
        removeSecurityProxy(master_task).assignee = team.teamowner
        removeSecurityProxy(master_task).milestone = current_distro_milestone
