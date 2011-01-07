# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import re
import subprocess
from unittest import (
    TestCase,
    TestLoader,
    )

import pytz
from zope.component import getUtility

from canonical.database.sqlbase import (
    cursor,
    flush_database_caches,
    flush_database_updates,
    sqlvalues,
    )
from canonical.launchpad.ftests import (
    login,
    login_person,
    )
from canonical.launchpad.testing.systemdocs import (
    default_optionflags,
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import (
    IPersonSet,
    TeamSubscriptionPolicy,
    )
from lp.registry.interfaces.teammembership import (
    CyclicalTeamMembershipError,
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.registry.model.teammembership import TeamMembership
from lp.testing import TestCaseWithFactory


class TestTeamMembershipSet(TestCase):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        login('test@canonical.com')
        self.membershipset = getUtility(ITeamMembershipSet)
        self.personset = getUtility(IPersonSet)

    def test_membership_creation(self):
        marilize = self.personset.getByName('marilize')
        ubuntu_team = self.personset.getByName('ubuntu-team')
        membership = self.membershipset.new(
            marilize, ubuntu_team, TeamMembershipStatus.APPROVED, marilize)
        self.assertEqual(
            membership,
            self.membershipset.getByPersonAndTeam(marilize, ubuntu_team))
        self.assertEqual(membership.status, TeamMembershipStatus.APPROVED)

    def test_active_membership_creation_stores_proponent_and_reviewer(self):
        """Memberships created in any active state have the reviewer stored.

        The date_joined, reviewer_comment, date_reviewed and attributes
        related to the proponent are also stored, but everything related to
        acknowledger will be left empty.
        """
        marilize = self.personset.getByName('marilize')
        ubuntu_team = self.personset.getByName('ubuntu-team')
        membership = self.membershipset.new(
            marilize, ubuntu_team, TeamMembershipStatus.APPROVED,
            ubuntu_team.teamowner, comment="I like her")
        self.assertEqual(ubuntu_team.teamowner, membership.proposed_by)
        self.assertEqual(membership.proponent_comment, "I like her")
        now = datetime.now(pytz.UTC)
        self.failUnless(membership.date_proposed <= now)
        self.failUnless(membership.datejoined <= now)
        self.assertEqual(ubuntu_team.teamowner, membership.reviewed_by)
        self.assertEqual(membership.reviewer_comment, "I like her")
        self.failUnless(membership.date_reviewed <= now)
        self.assertEqual(membership.acknowledged_by, None)

    def test_membership_creation_stores_proponent(self):
        """Memberships created in the proposed state have proponent stored.

        The proponent_comment and date_proposed are also stored, but
        everything related to reviewer and acknowledger will be left empty.
        """
        marilize = self.personset.getByName('marilize')
        ubuntu_team = self.personset.getByName('ubuntu-team')
        membership = self.membershipset.new(
            marilize, ubuntu_team, TeamMembershipStatus.PROPOSED, marilize,
            comment="I'd like to join")
        self.assertEqual(marilize, membership.proposed_by)
        self.assertEqual(membership.proponent_comment, "I'd like to join")
        self.failUnless(
            membership.date_proposed <= datetime.now(pytz.UTC))
        self.assertEqual(membership.reviewed_by, None)
        self.assertEqual(membership.acknowledged_by, None)

    def test_admin_membership_creation(self):
        ubuntu_team = self.personset.getByName('ubuntu-team')
        no_priv = self.personset.getByName('no-priv')
        membership = self.membershipset.new(
            no_priv, ubuntu_team, TeamMembershipStatus.ADMIN, no_priv)
        self.assertEqual(
            membership,
            self.membershipset.getByPersonAndTeam(no_priv, ubuntu_team))
        self.assertEqual(membership.status, TeamMembershipStatus.ADMIN)

    def test_handleMembershipsExpiringToday(self):
        # Create a couple new teams, with one being a member of the other and
        # make Sample Person an approved member of both teams.
        login('foo.bar@canonical.com')
        foobar = self.personset.getByName('name16')
        sample_person = self.personset.getByName('name12')
        ubuntu_dev = self.personset.newTeam(
            foobar, 'ubuntu-dev', 'Ubuntu Developers')
        motu = self.personset.newTeam(foobar, 'motu', 'Ubuntu MOTU')
        ubuntu_dev.addMember(motu, foobar, force_team_add=True)
        ubuntu_dev.addMember(sample_person, foobar)
        motu.addMember(sample_person, foobar)

        # Now we need to cheat and set the expiration date of both memberships
        # manually because otherwise we would only be allowed to set an
        # expiration date in the future.
        now = datetime.now(pytz.UTC)
        from zope.security.proxy import removeSecurityProxy
        sample_person_on_motu = removeSecurityProxy(
            self.membershipset.getByPersonAndTeam(sample_person, motu))
        sample_person_on_motu.dateexpires = now
        sample_person_on_ubuntu_dev = removeSecurityProxy(
            self.membershipset.getByPersonAndTeam(sample_person, ubuntu_dev))
        sample_person_on_ubuntu_dev.dateexpires = now
        flush_database_updates()
        self.assertEqual(
            sample_person_on_ubuntu_dev.status, TeamMembershipStatus.APPROVED)
        self.assertEqual(
            sample_person_on_motu.status, TeamMembershipStatus.APPROVED)

        self.membershipset.handleMembershipsExpiringToday(foobar)
        flush_database_caches()

        # Now Sample Person is not direct nor indirect member of ubuntu-dev
        # or motu.
        self.assertEqual(
            sample_person_on_ubuntu_dev.status, TeamMembershipStatus.EXPIRED)
        self.failIf(sample_person.inTeam(ubuntu_dev))
        self.assertEqual(
            sample_person_on_motu.status, TeamMembershipStatus.EXPIRED)
        self.failIf(sample_person.inTeam(motu))


class TeamParticipationTestCase(TestCaseWithFactory):
    """Tests for team participation using 5 teams."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TeamParticipationTestCase, self).setUp()
        login('foo.bar@canonical.com')
        person_set = getUtility(IPersonSet)
        self.foo_bar = person_set.getByEmail('foo.bar@canonical.com')
        self.no_priv = person_set.getByName('no-priv')
        self.team1 = person_set.newTeam(self.foo_bar, 'team1', 'team1')
        self.team2 = person_set.newTeam(self.foo_bar, 'team2', 'team2')
        self.team3 = person_set.newTeam(self.foo_bar, 'team3', 'team3')
        self.team4 = person_set.newTeam(self.foo_bar, 'team4', 'team4')
        self.team5 = person_set.newTeam(self.foo_bar, 'team5', 'team5')

    def assertParticipantsEquals(self, participant_names, team):
        """Assert that the participants names in team are the expected ones.
        """
        self.assertEquals(
            sorted(participant_names),
            sorted([participant.name for participant in team.allmembers]))


class TestTeamParticipationHierarchy(TeamParticipationTestCase):
    """Participation management tests using 5 nested teams.

    Create a team hierarchy with 5 teams and one person (no-priv) as
    member of the last team in the chain.
        team1
           team2
              team3
                 team4
                    team5
                       no-priv
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Setup the team hierarchy."""
        super(TestTeamParticipationHierarchy, self).setUp()
        self.team5.addMember(self.no_priv, self.foo_bar)
        self.team1.addMember(self.team2, self.foo_bar, force_team_add=True)
        self.team2.addMember(self.team3, self.foo_bar, force_team_add=True)
        self.team3.addMember(self.team4, self.foo_bar, force_team_add=True)
        self.team4.addMember(self.team5, self.foo_bar, force_team_add=True)

    def testTeamParticipationSetUp(self):
        """Make sure that the TeamParticipation are sane after setUp."""
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team2', 'team3', 'team4', 'team5'],
            self.team1)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team3', 'team4', 'team5'], self.team2)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team4', 'team5'], self.team3)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team5'], self.team4)
        self.assertParticipantsEquals(
            ['name16', 'no-priv'], self.team5)

    def testSevereHierarchyByRemovingTeam3FromTeam2(self):
        """Make sure that the participations is updated correctly when
        the hierarchy is severed in the two.

        This is similar to what was experienced in bug 261915.
        """
        self.team2.setMembershipData(
            self.team3, TeamMembershipStatus.DEACTIVATED, self.foo_bar)
        self.assertParticipantsEquals(['name16', 'team2'], self.team1)
        self.assertParticipantsEquals(['name16'], self.team2)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team4', 'team5'], self.team3)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team5'], self.team4)
        self.assertParticipantsEquals(['name16', 'no-priv'], self.team5)

    def testRemovingLeafTeam(self):
        """Make sure that participations are updated correctly when removing
        the leaf team.
        """
        self.team4.setMembershipData(
            self.team5, TeamMembershipStatus.DEACTIVATED, self.foo_bar)
        self.assertParticipantsEquals(
            ['name16', 'team2', 'team3', 'team4'], self.team1)
        self.assertParticipantsEquals(
            ['name16', 'team3', 'team4'], self.team2)
        self.assertParticipantsEquals(['name16', 'team4'], self.team3)
        self.assertParticipantsEquals(['name16'], self.team4)
        self.assertParticipantsEquals(['name16', 'no-priv'], self.team5)


class TestTeamParticipationTree(TeamParticipationTestCase):
    """Participation management tests using 5 nested teams

    Create a team hierarchy looking like this:
        team1
           team2
              team5
              team3
                 team4
                    team5
                       no-priv
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Setup the team hierarchy."""
        super(TestTeamParticipationTree, self).setUp()
        self.team5.addMember(self.no_priv, self.foo_bar)
        self.team1.addMember(self.team2, self.foo_bar, force_team_add=True)
        self.team2.addMember(self.team3, self.foo_bar, force_team_add=True)
        self.team2.addMember(self.team5, self.foo_bar, force_team_add=True)
        self.team3.addMember(self.team4, self.foo_bar, force_team_add=True)
        self.team4.addMember(self.team5, self.foo_bar, force_team_add=True)

    def tearDown(self):
        super(TestTeamParticipationTree, self).tearDown()
        self.layer.force_dirty_database()

    def testTeamParticipationSetUp(self):
        """Make sure that the TeamParticipation are sane after setUp."""
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team2', 'team3', 'team4', 'team5'],
            self.team1)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team3', 'team4', 'team5'], self.team2)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team4', 'team5'], self.team3)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team5'], self.team4)
        self.assertParticipantsEquals(
            ['name16', 'no-priv'], self.team5)

    def testRemoveTeam3FromTeam2(self):
        self.team2.setMembershipData(
            self.team3, TeamMembershipStatus.DEACTIVATED, self.foo_bar)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team2', 'team5'], self.team1)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team5'], self.team2)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team4', 'team5'], self.team3)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team5'], self.team4)
        self.assertParticipantsEquals(['name16', 'no-priv'], self.team5)

    def testRemoveTeam5FromTeam4(self):
        self.team4.setMembershipData(
            self.team5, TeamMembershipStatus.DEACTIVATED, self.foo_bar)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team2', 'team3', 'team4', 'team5'],
            self.team1)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team3', 'team4', 'team5'], self.team2)
        self.assertParticipantsEquals(
            ['name16', 'team4'], self.team3)
        self.assertParticipantsEquals(['name16'], self.team4)
        self.assertParticipantsEquals(['name16', 'no-priv'], self.team5)


class TestParticipationCleanup(TeamParticipationTestCase):
    """Test deletion of a member from a team with many superteams.
    Create a team hierarchy looking like this:
        team1
           team2
              team3
                 team4
                    team5
                       no-priv
    """

    def setUp(self):
        """Setup the team hierarchy."""
        super(TestParticipationCleanup, self).setUp()
        self.team1.addMember(self.team2, self.foo_bar, force_team_add=True)
        self.team2.addMember(self.team3, self.foo_bar, force_team_add=True)
        self.team3.addMember(self.team4, self.foo_bar, force_team_add=True)
        self.team4.addMember(self.team5, self.foo_bar, force_team_add=True)
        self.team5.addMember(self.no_priv, self.foo_bar)

    def testMemberRemoval(self):
        """Remove the member from the last team.

        The number of db queries should be constant not O(depth).
        """
        self.assertStatementCount(
            7,
            self.team5.setMembershipData, self.no_priv,
            TeamMembershipStatus.DEACTIVATED, self.team5.teamowner)


class TestTeamParticipationMesh(TeamParticipationTestCase):
    """Participation management tests using two roots and some duplicated
    branches.

    Create a team hierarchy looking like this:
        team1    /--team6
            team2        \
             |  team3    |
             \--- team4-/
                     team5
                       no-priv
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Setup the team hierarchy."""
        super(TestTeamParticipationMesh, self).setUp()
        self.team6 = getUtility(IPersonSet).newTeam(
            self.foo_bar, 'team6', 'team6')
        self.team5.addMember(self.no_priv, self.foo_bar)
        self.team1.addMember(self.team2, self.foo_bar, force_team_add=True)
        self.team2.addMember(self.team3, self.foo_bar, force_team_add=True)
        self.team2.addMember(self.team4, self.foo_bar, force_team_add=True)
        self.team3.addMember(self.team4, self.foo_bar, force_team_add=True)
        self.team4.addMember(self.team5, self.foo_bar, force_team_add=True)
        self.team6.addMember(self.team2, self.foo_bar, force_team_add=True)
        self.team6.addMember(self.team4, self.foo_bar, force_team_add=True)

    def tearDown(self):
        super(TestTeamParticipationMesh, self).tearDown()
        self.layer.force_dirty_database()

    def testTeamParticipationSetUp(self):
        """Make sure that the TeamParticipation are sane after setUp."""
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team2', 'team3', 'team4', 'team5'],
            self.team1)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team3', 'team4', 'team5'], self.team2)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team4', 'team5'], self.team3)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team5'], self.team4)
        self.assertParticipantsEquals(['name16', 'no-priv'], self.team5)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team2', 'team3', 'team4', 'team5'],
            self.team6)

    def testRemoveTeam3FromTeam2(self):
        self.team2.setMembershipData(
            self.team3, TeamMembershipStatus.DEACTIVATED, self.foo_bar)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team2', 'team4', 'team5'], self.team1)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team4', 'team5'], self.team2)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team4', 'team5'], self.team3)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team5'], self.team4)
        self.assertParticipantsEquals(['name16', 'no-priv'], self.team5)
        self.assertParticipantsEquals(
            ['name16', 'no-priv', 'team2', 'team4', 'team5'], self.team6)

    def testRemoveTeam5FromTeam4(self):
        self.team4.setMembershipData(
            self.team5, TeamMembershipStatus.DEACTIVATED, self.foo_bar)
        self.assertParticipantsEquals(
            ['name16', 'team2', 'team3', 'team4'], self.team1)
        self.assertParticipantsEquals(
            ['name16', 'team3', 'team4'], self.team2)
        self.assertParticipantsEquals(['name16', 'team4'], self.team3)
        self.assertParticipantsEquals(['name16'], self.team4)
        self.assertParticipantsEquals(['name16', 'no-priv'], self.team5)
        self.assertParticipantsEquals(
            ['name16', 'team2', 'team3', 'team4'], self.team6)


class TestTeamMembership(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_teams_not_kicked_from_themselves_bug_248498(self):
        """The self-participation of a team must not be removed.

        Performing the following steps would cause a team's self-participation
        to be removed, but it shouldn't.

            1. propose team A as a member of team B
            2. propose team B as a member of team A
            3. approve team A as a member of team B
            4. decline team B as a member of team A

        This test will make sure that doesn't happen in the future.
        """
        login('test@canonical.com')
        person = self.factory.makePerson()
        login_person(person) # Now login with the future owner of the teams.
        teamA = self.factory.makeTeam(
            person, subscription_policy=TeamSubscriptionPolicy.MODERATED)
        teamB = self.factory.makeTeam(
            person, subscription_policy=TeamSubscriptionPolicy.MODERATED)
        self.failUnless(
            teamA.inTeam(teamA), "teamA is not a participant of itself")
        self.failUnless(
            teamB.inTeam(teamB), "teamB is not a participant of itself")

        teamA.join(teamB, requester=person)
        teamB.join(teamA, requester=person)
        teamB.setMembershipData(teamA, TeamMembershipStatus.APPROVED, person)
        teamA.setMembershipData(teamB, TeamMembershipStatus.DECLINED, person)

        self.failUnless(teamA.hasParticipationEntryFor(teamA),
                        "teamA is not a participant of itself")
        self.failUnless(teamB.hasParticipationEntryFor(teamB),
                        "teamB is not a participant of itself")

    def test_membership_status_changes_are_immediately_flushed_to_db(self):
        """Any changes to a membership status must be imediately flushed.

        Sometimes we may change multiple team memberships in the same
        transaction (e.g. when expiring memberships). If there are multiple
        memberships for a given member changed in this way, we need to
        ensure each change is flushed to the database so that subsequent ones
        operate on the correct data.
        """
        login('foo.bar@canonical.com')
        tm = TeamMembership.selectFirstBy(
            status=TeamMembershipStatus.APPROVED, orderBy='id')
        tm.setStatus(TeamMembershipStatus.DEACTIVATED,
                     getUtility(IPersonSet).getByName('name16'))
        # Bypass SQLObject to make sure the update was really flushed to the
        # database.
        cur = cursor()
        cur.execute("SELECT status FROM teammembership WHERE id = %d" % tm.id)
        [new_status] = cur.fetchone()
        self.assertEqual(new_status, TeamMembershipStatus.DEACTIVATED.value)


class TestTeamMembershipSetStatus(TestCaseWithFactory):
    """Test the behaviour of TeamMembership's setStatus()."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamMembershipSetStatus, self).setUp()
        login('foo.bar@canonical.com')
        self.foobar = getUtility(IPersonSet).getByName('name16')
        self.no_priv = getUtility(IPersonSet).getByName('no-priv')
        self.ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
        self.admins = getUtility(IPersonSet).getByName('admins')
        # Create a bunch of arbitrary teams to use in the tests.
        self.team1 = self.factory.makeTeam(self.foobar)
        self.team2 = self.factory.makeTeam(self.foobar)
        self.team3 = self.factory.makeTeam(self.foobar)

    def test_proponent_is_stored(self):
        for status in [TeamMembershipStatus.DEACTIVATED,
                       TeamMembershipStatus.EXPIRED,
                       TeamMembershipStatus.DECLINED]:
            tm = TeamMembership(
                person=self.no_priv, team=self.ubuntu_team, status=status)
            self.failIf(
                tm.proposed_by, "There can be no proponent at this point.")
            self.failIf(
                tm.date_proposed, "There can be no proposed date this point.")
            self.failIf(tm.proponent_comment,
                        "There can be no proponent comment at this point.")
            tm.setStatus(
                TeamMembershipStatus.PROPOSED, self.foobar,
                "Did it 'cause I can")
            self.failUnlessEqual(tm.proposed_by, self.foobar)
            self.failUnlessEqual(tm.proponent_comment, "Did it 'cause I can")
            self.failUnless(
                tm.date_proposed <= datetime.now(pytz.UTC))
            # Destroy the membership so that we can create another in a
            # different state.
            tm.destroySelf()

    def test_acknowledger_is_stored(self):
        for status in [TeamMembershipStatus.APPROVED,
                       TeamMembershipStatus.INVITATION_DECLINED]:
            tm = TeamMembership(
                person=self.admins, team=self.ubuntu_team,
                status=TeamMembershipStatus.INVITED)
            self.failIf(
                tm.acknowledged_by,
                "There can be no acknowledger at this point.")
            self.failIf(
                tm.date_acknowledged,
                "There can be no accepted date this point.")
            self.failIf(tm.acknowledger_comment,
                        "There can be no acknowledger comment at this point.")
            tm.setStatus(status, self.foobar, "Did it 'cause I can")
            self.failUnlessEqual(tm.acknowledged_by, self.foobar)
            self.failUnlessEqual(
                tm.acknowledger_comment, "Did it 'cause I can")
            self.failUnless(
                tm.date_acknowledged <= datetime.now(pytz.UTC))
            # Destroy the membership so that we can create another in a
            # different state.
            tm.destroySelf()

    def test_reviewer_is_stored(self):
        transitions_mapping = {
            TeamMembershipStatus.DEACTIVATED: [TeamMembershipStatus.APPROVED],
            TeamMembershipStatus.EXPIRED: [TeamMembershipStatus.APPROVED],
            TeamMembershipStatus.PROPOSED: [
                TeamMembershipStatus.APPROVED, TeamMembershipStatus.DECLINED],
            TeamMembershipStatus.DECLINED: [TeamMembershipStatus.APPROVED],
            TeamMembershipStatus.INVITATION_DECLINED: [
                TeamMembershipStatus.APPROVED]}
        for status, new_statuses in transitions_mapping.items():
            for new_status in new_statuses:
                tm = TeamMembership(
                    person=self.no_priv, team=self.ubuntu_team, status=status)
                self.failIf(
                    tm.reviewed_by,
                    "There can be no approver at this point.")
                self.failIf(
                    tm.date_reviewed,
                    "There can be no approved date this point.")
                self.failIf(
                    tm.reviewer_comment,
                    "There can be no approver comment at this point.")
                tm.setStatus(new_status, self.foobar, "Did it 'cause I can")
                self.failUnlessEqual(tm.reviewed_by, self.foobar)
                self.failUnlessEqual(
                    tm.reviewer_comment, "Did it 'cause I can")
                self.failUnless(
                    tm.date_reviewed <= datetime.now(pytz.UTC))

                # Destroy the membership so that we can create another in a
                # different state.
                tm.destroySelf()

    def test_datejoined(self):
        """TeamMembership.datejoined stores the date in which this membership
        was made active for the first time.
        """
        tm = TeamMembership(
            person=self.no_priv, team=self.ubuntu_team,
            status=TeamMembershipStatus.PROPOSED)
        self.failIf(
            tm.datejoined, "There can be no datejoined at this point.")
        tm.setStatus(TeamMembershipStatus.APPROVED, self.foobar)
        now = datetime.now(pytz.UTC)
        self.failUnless(tm.datejoined <= now)

        # We now set the status to deactivated and change datejoined to a
        # date in the past just so that we can easily show it's not changed
        # again by setStatus().
        one_minute_ago = now - timedelta(minutes=1)
        tm.setStatus(TeamMembershipStatus.DEACTIVATED, self.foobar)
        tm.datejoined = one_minute_ago
        tm.setStatus(TeamMembershipStatus.APPROVED, self.foobar)
        self.failUnless(tm.datejoined <= one_minute_ago)

    def test_no_cyclical_membership_allowed(self):
        """No status change can create cyclical memberships."""
        # Invite team2 as member of team1 and team1 as member of team2. This
        # is not a problem because that won't make any team an active member
        # of the other.
        self.team1.addMember(self.team2, self.no_priv)
        self.team2.addMember(self.team1, self.no_priv)
        team1_on_team2 = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        team2_on_team1 = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team2, self.team1)
        self.failUnlessEqual(
            team1_on_team2.status, TeamMembershipStatus.INVITED)
        self.failUnlessEqual(
            team2_on_team1.status, TeamMembershipStatus.INVITED)

        # Now make team1 an active member of team2.  From this point onwards,
        # team2 cannot be made an active member of team1.
        team1_on_team2.setStatus(TeamMembershipStatus.APPROVED, self.foobar)
        flush_database_updates()
        self.failUnlessEqual(
            team1_on_team2.status, TeamMembershipStatus.APPROVED)
        self.assertRaises(
            CyclicalTeamMembershipError, team2_on_team1.setStatus,
            TeamMembershipStatus.APPROVED, self.foobar)
        self.failUnlessEqual(
            team2_on_team1.status, TeamMembershipStatus.INVITED)

        # It is possible to change the state of team2's membership on team1
        # to another inactive state, though.
        team2_on_team1.setStatus(
            TeamMembershipStatus.INVITATION_DECLINED, self.foobar)
        self.failUnlessEqual(
            team2_on_team1.status, TeamMembershipStatus.INVITATION_DECLINED)

    def test_no_cyclical_participation_allowed(self):
        """No status change can create cyclical participation."""
        # Invite team1 as a member of team3 and forcibly add team2 as member
        # of team1 and team3 as member of team2.
        self.team3.addMember(self.team1, self.no_priv)
        self.team1.addMember(self.team2, self.foobar, force_team_add=True)
        self.team2.addMember(self.team3, self.foobar, force_team_add=True)

        # Since team2 is a member of team1 and team3 is a member of team2, we
        # can't make team1 a member of team3.
        team1_on_team3 = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team3)
        self.assertRaises(
            CyclicalTeamMembershipError, team1_on_team3.setStatus,
            TeamMembershipStatus.APPROVED, self.foobar)

    def test_invited_member_can_be_made_admin(self):
        self.team2.addMember(self.team1, self.no_priv)
        team1_on_team2 = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.INVITED)
        team1_on_team2.setStatus(TeamMembershipStatus.ADMIN, self.foobar)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.ADMIN)

    def test_deactivated_member_can_be_made_admin(self):
        self.team2.addMember(self.team1, self.foobar, force_team_add=True)
        team1_on_team2 = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.APPROVED)
        team1_on_team2.setStatus(
            TeamMembershipStatus.DEACTIVATED, self.foobar)
        self.assertEqual(
            team1_on_team2.status, TeamMembershipStatus.DEACTIVATED)
        team1_on_team2.setStatus(TeamMembershipStatus.ADMIN, self.foobar)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.ADMIN)

    def test_expired_member_can_be_made_admin(self):
        self.team2.addMember(self.team1, self.foobar, force_team_add=True)
        team1_on_team2 = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.APPROVED)
        team1_on_team2.setStatus(TeamMembershipStatus.EXPIRED, self.foobar)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.EXPIRED)
        team1_on_team2.setStatus(TeamMembershipStatus.ADMIN, self.foobar)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.ADMIN)

    def test_declined_member_can_be_made_admin(self):
        self.team2.subscriptionpolicy = TeamSubscriptionPolicy.MODERATED
        self.team1.join(self.team2, requester=self.foobar)
        team1_on_team2 = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.PROPOSED)
        team1_on_team2.setStatus(TeamMembershipStatus.DECLINED, self.foobar)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.DECLINED)
        team1_on_team2.setStatus(TeamMembershipStatus.ADMIN, self.foobar)
        self.assertEqual(team1_on_team2.status, TeamMembershipStatus.ADMIN)

    def test_invited_member_can_be_declined(self):
        # A team can decline an invited member.
        self.team2.addMember(self.team1, self.no_priv)
        tm = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        tm.setStatus(
            TeamMembershipStatus.INVITATION_DECLINED, self.team2.teamowner)
        self.assertEqual(TeamMembershipStatus.INVITATION_DECLINED, tm.status)

    def test_retractTeamMembership_invited(self):
        # A team can retract a membership invitation.
        self.team2.addMember(self.team1, self.no_priv)
        self.team1.retractTeamMembership(self.team2, self.team1.teamowner)
        tm = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        self.assertEqual(TeamMembershipStatus.INVITATION_DECLINED, tm.status)

    def test_retractTeamMembership_proposed(self):
        # A team can retract the proposed membership in a team.
        self.team2.subscriptionpolicy = TeamSubscriptionPolicy.MODERATED
        self.team1.join(self.team2, self.team1.teamowner)
        self.team1.retractTeamMembership(self.team2, self.team1.teamowner)
        tm = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        self.assertEqual(TeamMembershipStatus.DECLINED, tm.status)

    def test_retractTeamMembership_active(self):
        # A team can retract the membership in a team.
        self.team1.join(self.team2, self.team1.teamowner)
        self.team1.retractTeamMembership(self.team2, self.team1.teamowner)
        tm = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        self.assertEqual(TeamMembershipStatus.DEACTIVATED, tm.status)

    def test_retractTeamMembership_admin(self):
        # A team can retract the membership in a team.
        self.team1.join(self.team2, self.team1.teamowner)
        tm = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            self.team1, self.team2)
        tm.setStatus(TeamMembershipStatus.ADMIN, self.team2.teamowner)
        self.team1.retractTeamMembership(self.team2, self.team1.teamowner)
        self.assertEqual(TeamMembershipStatus.DEACTIVATED, tm.status)


class TestCheckTeamParticipationScript(TestCase):
    layer = DatabaseFunctionalLayer

    def _runScript(self, expected_returncode=0):
        process = subprocess.Popen(
            'cronscripts/check-teamparticipation.py', shell=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        (out, err) = process.communicate()
        self.assertEqual(process.returncode, expected_returncode, (out, err))
        return out, err

    def test_no_output_if_no_invalid_entries(self):
        """No output if there's no invalid teamparticipation entries."""
        out, err = self._runScript()
        self.assertEqual((out, err), ('', ''))

    def test_report_invalid_teamparticipation_entries(self):
        """The script reports missing/spurious TeamParticipation entries.

        As well as missing self-participation.
        """
        cur = cursor()
        # Create a new entry in the Person table and change its
        # self-participation entry, making that person a participant in a team
        # where it should not be as well as making that person not a member of
        # itself (as everybody should be).
        cur.execute("""
            INSERT INTO
                Person (id, name, displayname, creation_rationale)
                VALUES (9999, 'zzzzz', 'zzzzzz', 1);
            UPDATE TeamParticipation
                SET team = (
                    SELECT id
                    FROM Person
                    WHERE teamowner IS NOT NULL
                    ORDER BY name
                    LIMIT 1)
                WHERE person = 9999;
            """)
        # Now add the new person as a member of another team but don't create
        # the relevant TeamParticipation for that person on that team.
        cur.execute("""
            INSERT INTO
                TeamMembership (person, team, status)
                VALUES (9999,
                    (SELECT id
                        FROM Person
                        WHERE teamowner IS NOT NULL
                        ORDER BY name desc
                        LIMIT 1),
                    %s);
            """ % sqlvalues(TeamMembershipStatus.APPROVED))
        import transaction
        transaction.commit()

        out, err = self._runScript()
        self.assertEqual(out, '', (out, err))
        self.failUnless(
            re.search('missing TeamParticipation entries for zzzzz', err),
            (out, err))
        self.failUnless(
            re.search('spurious TeamParticipation entries for zzzzz', err),
            (out, err))
        self.failUnless(
            re.search('not members of themselves:.*zzzzz.*', err),
            (out, err))

    def test_report_circular_team_references(self):
        """The script reports circular references between teams.

        If that happens, though, the script will have to report the circular
        references and exit, to avoid an infinite loop when checking for
        missing/spurious TeamParticipation entries.
        """
        # Create two new teams and make them members of each other.
        cursor().execute("""
            INSERT INTO
                Person (id, name, displayname, teamowner)
                VALUES (9998, 'test-team1', 'team1', 1);
            INSERT INTO
                Person (id, name, displayname, teamowner)
                VALUES (9997, 'test-team2', 'team2', 1);
            INSERT INTO
                TeamMembership (person, team, status)
                VALUES (9998, 9997, %(approved)s);
            INSERT INTO
                TeamParticipation (person, team)
                VALUES (9998, 9997);
            INSERT INTO
                TeamMembership (person, team, status)
                VALUES (9997, 9998, %(approved)s);
            INSERT INTO
                TeamParticipation (person, team)
                VALUES (9997, 9998);
            """ % sqlvalues(approved=TeamMembershipStatus.APPROVED))
        import transaction
        transaction.commit()
        out, err = self._runScript(expected_returncode=1)
        self.assertEqual(out, '', (out, err))
        self.failUnless(
            re.search('Circular references found', err), (out, err))


def test_suite():
    suite = TestLoader().loadTestsFromName(__name__)
    bug_249185 = LayeredDocFileSuite(
        'bug-249185.txt', optionflags=default_optionflags,
        layer=DatabaseFunctionalLayer, setUp=setUp, tearDown=tearDown)
    suite.addTest(bug_249185)
    return suite
