# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type

import transaction
from zope.component import getUtility
from zope.interface.exceptions import Invalid
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    FunctionalLayer,
    )
from lp.registry.enum import PersonTransferJobType
from lp.registry.errors import (
    JoinNotAllowed,
    TeamSubscriptionPolicyError,
    )
from lp.registry.interfaces.mailinglist import MailingListStatus
from lp.registry.interfaces.person import (
    IPersonSet,
    ITeamPublic,
    PersonVisibility,
    TeamMembershipRenewalPolicy,
    TeamSubscriptionPolicy,
    )
from lp.registry.model.persontransferjob import PersonTransferJob
from lp.soyuz.enums import ArchiveStatus
from lp.testing import (
    login_celebrity,
    login_person,
    TestCaseWithFactory,
    )


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

    def test_setContactAddress_after_purged_mailing_list_and_rename(self):
        # This is the rare case where a list is purged for a team rename,
        # then the contact address is set/unset sometime afterwards.
        # The old mailing list address belongs the the team, but not the list.
        # 1. Create then purge a mailing list.
        list_address = self.createMailingListAndGetAddress()
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
        person_transfer_job = PersonTransferJob(
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


class TestMembershipManagement(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_deactivateAllMembers_cleans_up_teamparticipation_deactivated(
            self):
        superteam = self.factory.makeTeam(name='super')
        targetteam = self.factory.makeTeam(name='target')
        login_celebrity('admin')
        targetteam.join(superteam, targetteam.teamowner)

        # Now we create a deactivated link for the target team's teamowner.
        targetteam.teamowner.join(superteam, targetteam.teamowner)
        targetteam.teamowner.leave(superteam)

        self.assertEqual(
                sorted([superteam, targetteam]),
                sorted([team for team in
                    targetteam.teamowner.teams_participated_in]))
        targetteam.deactivateAllMembers(
            comment='test',
            reviewer=targetteam.teamowner)
        self.assertEqual(
            [],
            sorted([team for team in
                targetteam.teamowner.teams_participated_in]))

    def test_deactivateAllMembers_cleans_up_teamparticipation_teamowner(self):
        superteam = self.factory.makeTeam(name='super')
        targetteam = self.factory.makeTeam(name='target')
        login_celebrity('admin')
        targetteam.join(superteam, targetteam.teamowner)
        self.assertEqual(
                sorted([superteam, targetteam]),
                sorted([team for team
                            in targetteam.teamowner.teams_participated_in]))
        targetteam.deactivateAllMembers(
            comment='test',
            reviewer=targetteam.teamowner)
        self.assertEqual(
            [],
            sorted([team for team
                in targetteam.teamowner.teams_participated_in]))

    def test_deactivateAllMembers_cleans_up_team_participation(self):
        superteam = self.factory.makeTeam(name='super')
        sharedteam = self.factory.makeTeam(name='shared')
        anotherteam = self.factory.makeTeam(name='another')
        targetteam = self.factory.makeTeam(name='target')
        person = self.factory.makePerson()
        login_celebrity('admin')
        person.join(targetteam)
        person.join(sharedteam)
        person.join(anotherteam)
        targetteam.join(superteam, targetteam.teamowner)
        targetteam.join(sharedteam, targetteam.teamowner)
        self.assertTrue(superteam in person.teams_participated_in)
        targetteam.deactivateAllMembers(
            comment='test',
            reviewer=targetteam.teamowner)
        self.assertEqual(
            sorted([sharedteam, anotherteam]),
            sorted([team for team in person.teams_participated_in]))
