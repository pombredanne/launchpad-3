# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.database import teammembership
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
        orig_flush_db_updates = teammembership.flush_database_updates
        self.flush_db_updates_called = False
        def fake_flush_db_updates():
            orig_flush_db_updates()
            self.flush_db_updates_called = True
        teammembership.flush_database_updates = fake_flush_db_updates
        try:
            tm = teammembership.TeamMembership.selectFirstBy(
                status=TeamMembershipStatus.APPROVED, orderBy='id')
            tm.setStatus(TeamMembershipStatus.DEACTIVATED,
                         getUtility(IPersonSet).getByName('name16'))
        finally:
            teammembership.flush_database_updates = orig_flush_db_updates
        self.failUnless(self.flush_db_updates_called)
        self.failIf(tm.person in tm.team.activemembers)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

