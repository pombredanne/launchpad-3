# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from datetime import datetime

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
            marilize, ubuntu_team, TeamMembershipStatus.APPROVED)
        self.assertEqual(
            membership,
            self.membershipset.getByPersonAndTeam(marilize, ubuntu_team))
        self.assertEqual(membership.status, TeamMembershipStatus.APPROVED)

    def test_admin_membership_creation(self):
        ubuntu_team = self.personset.getByName('ubuntu-team')
        no_priv = self.personset.getByName('no-priv')
        membership = self.membershipset.new(
            no_priv, ubuntu_team, TeamMembershipStatus.ADMIN)
        self.assertEqual(
            membership,
            self.membershipset.getByPersonAndTeam(no_priv, ubuntu_team))
        self.assertEqual(membership.status, TeamMembershipStatus.ADMIN)

    def test_handleMembershipsExpiringToday(self):
        # Create a couple new teams, with one being a member of the other and
        # make Sample Person an approved member of both teams.
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

