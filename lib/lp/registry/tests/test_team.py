# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

from testtools.matchers import LessThan

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
from lp.registry.model.persontransferjob import PersonTransferJob
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


class TestTeamWorkItems(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def _createWorkItems(self):
        next_date = datetime(2050, 1, 1)
        current_milestone = self.factory.makeMilestone(
            dateexpected=next_date)
        self.current_milestone = current_milestone
        future_milestone = self.factory.makeMilestone(
            product=current_milestone.product,
            dateexpected=datetime(2060, 1, 1))
        self.team = team = self.factory.makeTeam()
        assigned_spec = self.factory.makeSpecification(
            assignee=team.teamowner, milestone=current_milestone,
            product=current_milestone.product)
        workitem_from_assigned_spec = self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_assigned_spec', specification=assigned_spec)
        second_workitem_from_assigned_spec = (
            self.factory.makeSpecificationWorkItem(
                title=u'second workitem_from_assigned_spec',
                specification=assigned_spec))
        future_spec = self.factory.makeSpecification(
            milestone=future_milestone, product=future_milestone.product,
            priority=SpecificationPriority.HIGH)
        workitem_from_future_spec = self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_future_spec not assigned to team member',
            specification=future_spec, milestone=current_milestone)
        assigned_workitem_from_future_spec = (
            self.factory.makeSpecificationWorkItem(
                title=u'workitem_from_future_spec assigned to team member',
                specification=future_spec, milestone=current_milestone,
                assignee=team.teamowner))
        foreign_spec = self.factory.makeSpecification(
            milestone=current_milestone, product=current_milestone.product)
        workitem_from_foreign_spec = self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_foreign_spec not assigned to team member',
            specification=foreign_spec)
        assigned_workitem_from_foreign_spec = (
            self.factory.makeSpecificationWorkItem(
                title=u'workitem_from_foreign_spec assigned to team member',
                specification=foreign_spec, assignee=team.teamowner))

        bug = self.factory.makeBug(milestone=current_milestone)
        removeSecurityProxy(bug.bugtasks[0]).assignee = team.teamowner

        # Create a BugTask whose target is a ProductSeries
        bug2 = self.factory.makeBug(series=current_milestone.productseries)
        # The call above created 2 BugTasks (one for the product and one for
        # the productseries), but we only care about the second one (for the
        # PS) so we'll set the milestone/assignee just for it.
        removeSecurityProxy(bug2.bugtasks[1]).assignee = team.teamowner
        removeSecurityProxy(bug2.bugtasks[1]).milestone = current_milestone

        # Create a BugTask whose target is a DistroSeries
        current_distro_milestone = self.factory.makeMilestone(
            distribution=self.factory.makeDistribution(),
            dateexpected=next_date)
        bug3 = self.factory.makeBug(
            series=current_distro_milestone.distroseries)
        # The call above created 2 BugTasks (one for the distro and one for
        # the distroseries), but we only care about the second one (for the
        # DS) so we'll set the milestone/assignee just for it.
        removeSecurityProxy(bug3.bugtasks[1]).assignee = team.teamowner
        removeSecurityProxy(bug3.bugtasks[1]).milestone = current_distro_milestone

        # Create a BugTask whose target is a DistributionSourcePackage
        sourcepackage = self.factory.makeSourcePackage(
            distroseries=current_distro_milestone.distroseries)
        bug4 = self.factory.makeBug()
        nomination = self.factory.makeBugNomination(bug4, sourcepackage)
        removeSecurityProxy(nomination).approve(
            current_distro_milestone.distribution.owner)
        removeSecurityProxy(bug4.bugtasks[1]).assignee = team.teamowner
        removeSecurityProxy(bug4.bugtasks[1]).milestone = current_distro_milestone

    def test_query_counts(self):
        self._createWorkItems()
        dateexpected = self.current_milestone.dateexpected
        flush_database_caches()
        with StormStatementRecorder() as recorder:
            containers = self.team.getWorkItemsDueBefore(dateexpected)
        # One query to get all team members;
        # One to get all SpecWorkItems;
        # One to get all BugTasks.
        self.assertThat(recorder, HasQueryCount(LessThan(4)))

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

    # XXX: This test should die and be replaced with more specific tests that
    # just assert that some specific bug/wi is returned, like the ones below.
    def test_getWorkItems(self):
        self._createWorkItems()

        work_items = removeSecurityProxy(self.team).getWorkItemsDueBefore(
            self.current_milestone.dateexpected)

        # Instead of seeing meaningless failures while we experiment I thought
        # it'd be better to just print a reasonable representation of the
        # return value of the method.
        for date, containers in work_items.items():
            print date
            for container in containers:
                print "\tWork items from %s:" % container.label
                print "\t\t%s" % ", ".join(str(item) for item in container.items)

    def test_getWorkItems_with_private_bugs(self):
        # TODO: bugs the user is not allowed to see must not be included here.
        pass

    def test_getWorkItems_for_distroseriessourcepackage_bugtask(self):
        team = self.factory.makeTeam()
        today = datetime.today().date()
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        milestone = self.factory.makeMilestone(
            distroseries=distroseries, dateexpected=today)
        bug = self.factory.makeBug(
            milestone=milestone, sourcepackagename=sourcepackagename)
        self.assertEqual(1, len(bug.bugtasks))
        task = bug.bugtasks[0]
        removeSecurityProxy(task).assignee = team.teamowner

        workitems = team.getWorkItemsDueBefore(today + timedelta(days=1))

        self.assertEqual(1, len(workitems[today]))
        self.assertEqual(1, len(workitems[today][0].items))
        self.assertEqual(task.title, workitems[today][0].items[0].title)

    def test_getWorkItems_skips_conjoined_slaves(self):
        team = self.factory.makeTeam()
        today = datetime.today().date()
        milestone = self.factory.makeMilestone(dateexpected=today)
        removeSecurityProxy(milestone.product).development_focus = (
            milestone.productseries)
        bug = self.factory.makeBug(
            series=milestone.productseries, milestone=milestone)
        self.assertEqual(2, len(bug.bugtasks))
        task1, task2 = bug.bugtasks

        # This will cause the assignee to propagate to the other bugtask as
        # well since they're conjoined.
        removeSecurityProxy(task1).assignee = team.teamowner
        self.assertIsNot(task1.conjoined_master, None)

        self.assertEqual(task1.milestone, task2.milestone)
        self.assertEqual(task1.assignee, task2.assignee)

        workitems = team.getWorkItemsDueBefore(today + timedelta(days=1))

        # There's a single work item container returned and that container
        # contains a single work item.
        self.assertEqual([today], workitems.keys())
        self.assertEqual(1, len(workitems[today]))
        self.assertEqual(1, len(workitems[today][0].items))
        # That work item represents task2. task1 is not included because
        # it's the conjoined slave.
        self.assertEqual(task2.title, workitems[today][0].items[0].title)
