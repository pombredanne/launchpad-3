# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import re
import subprocess
import unittest
from datetime import datetime, timedelta

import pytz

from zope.component import getUtility

from canonical.database.sqlbase import (
    flush_database_caches, flush_database_updates, cursor)
from canonical.launchpad.database import TeamMembership
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import (
    IPersonSet, ITeamMembershipSet, TeamMembershipStatus)
from canonical.testing import LaunchpadFunctionalLayer


class TestTeamMembershipSet(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

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
        now = datetime.now(pytz.timezone('UTC'))
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
            membership.date_proposed <= datetime.now(pytz.timezone('UTC')))
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
        now = datetime.now(pytz.timezone('UTC'))
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


class TestTeamMembership(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def test_indirect_members_are_kicked_when_kicking_team(self):
        """Indirect members are kicked when the team in which they are a
        direct member is kicked.

        Create a team hierarchy with 5 teams and one person (no-priv) as
        member of the last team in the chain.
            team1
               team2
                  team3
                     team4
                        team5
                           no-priv

        Then kick the latest team (team5) from team4 and check that neither
        no-priv nor team5 are indirect members of any other teams.
        """
        login('mark@hbd.com')
        person_set = getUtility(IPersonSet)
        sabdfl = person_set.getByName('sabdfl')
        no_priv = person_set.getByName('no-priv')
        team1 = person_set.newTeam(sabdfl, 'team1', 'team1')
        team2 = person_set.newTeam(sabdfl, 'team2', 'team2')
        team3 = person_set.newTeam(sabdfl, 'team3', 'team3')
        team4 = person_set.newTeam(sabdfl, 'team4', 'team4')
        team5 = person_set.newTeam(sabdfl, 'team5', 'team5')
        team5.addMember(no_priv, sabdfl)
        self.failUnless(no_priv in team5.activemembers)
        team1.addMember(team2, sabdfl, force_team_add=True)
        team2.addMember(team3, sabdfl, force_team_add=True)
        team3.addMember(team4, sabdfl, force_team_add=True)
        team4.addMember(team5, sabdfl, force_team_add=True)
        self.failUnless(team3 in team2.activemembers)
        self.failUnless(team4 in team3.activemembers)
        self.failUnless(team5 in team4.activemembers)
        self.failUnless(no_priv in team4.allmembers)
        self.failUnless(no_priv in team3.allmembers)
        self.failUnless(no_priv in team2.allmembers)
        self.failUnless(no_priv in team1.allmembers)
        team4.setMembershipData(
            team5, TeamMembershipStatus.DEACTIVATED, sabdfl)
        flush_database_updates()
        self.failIf(team5 in team4.allmembers)
        self.failIf(team5 in team3.allmembers)
        self.failIf(team5 in team2.allmembers)
        self.failIf(team5 in team1.allmembers)
        self.failIf(no_priv in team4.allmembers)
        self.failIf(no_priv in team3.allmembers)
        self.failIf(no_priv in team2.allmembers)
        self.failIf(no_priv in team1.allmembers)

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


class TestTeamMembershipSetStatus(unittest.TestCase):
    """Test the behaviour of TeamMembership's setStatus()."""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        self.foobar = getUtility(IPersonSet).getByName('name16')
        self.no_priv = getUtility(IPersonSet).getByName('no-priv')
        self.ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
        self.admins = getUtility(IPersonSet).getByName('admins')

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
                tm.date_proposed <= datetime.now(pytz.timezone('UTC')))
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
                tm.date_acknowledged <= datetime.now(pytz.timezone('UTC')))
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
                    tm.date_reviewed <= datetime.now(pytz.timezone('UTC')))

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
        now = datetime.now(pytz.timezone('UTC'))
        self.failUnless(tm.datejoined <= now)

        # We now set the status to deactivated and change datejoined to a
        # date in the past just so that we can easily show it's not changed
        # again by setStatus().
        one_minute_ago = now - timedelta(minutes=1)
        tm.setStatus(TeamMembershipStatus.DEACTIVATED, self.foobar)
        tm.datejoined = one_minute_ago
        tm.setStatus(TeamMembershipStatus.APPROVED, self.foobar)
        self.failUnless(tm.datejoined <= one_minute_ago)


class TestCheckTeamParticipationScript(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def _runScript(self):
        process = subprocess.Popen(
            'cronscripts/check-teamparticipation.py', shell=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        (out, err) = process.communicate()
        self.assertEqual(process.returncode, 0, (out, err))
        return out, err

    def test_no_output_if_no_invalid_entries(self):
        """No output if there's no invalid teamparticipation entries."""
        out, err = self._runScript()
        self.assertEqual((out, err), ('', ''))

    def test_report_invalid_teamparticipation_entries(self):
        """The script reports invalid TeamParticipation entries.

        As well as missing self-participation.
        """
        cur = cursor()
        # Create a new entry in the Person table and update its
        # TeamParticipation so that the person is a participant in a team
        # (without being a member) and the person is not a member of itself.
        cur.execute("""
            INSERT INTO
                Person (id, name, displayname, openid_identifier,
                        creation_rationale)
                VALUES (9999, 'zzzzz', 'zzzzzz', 'zzzzzzzzzzz', 1);
            UPDATE TeamParticipation
                SET team = (
                    SELECT id FROM Person WHERE teamowner IS NOT NULL limit 1)
                WHERE person = 9999;
            """)
        import transaction
        transaction.commit()

        out, err = self._runScript()
        self.assertEqual(err, '', (out, err))
        self.failUnless(
            re.search('Invalid TeamParticipation entry for zzzzz', out),
            (out, err))
        self.failUnless(
            re.search('not members of themselves:.*zzzzz.*', out),
            (out, err))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

