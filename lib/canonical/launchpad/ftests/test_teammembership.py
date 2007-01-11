# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.interfaces import IPersonSet, ITeamMembershipSet
from canonical.lp.dbschema import TeamMembershipStatus


class TestTeamMembershipSet(LaunchpadFunctionalTestCase):

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)
        login('test@canonical.com')
        self.membershipset = getUtility(ITeamMembershipSet)
        self.personset = getUtility(IPersonSet)

    def test_membership_creation(self):
        marilize = self.personset.getByName('marilize')
        ubuntu_team = self.personset.getByName('ubuntu-team')
        membership = self.membershipset.new(
            marilize, ubuntu_team, TeamMembershipStatus.APPROVED)
        self.failUnless(
            membership == self.membershipset.getByPersonAndTeam(marilize,
                                                                ubuntu_team))
        self.failUnless(membership.status == TeamMembershipStatus.APPROVED)

    def test_admin_membership_creation(self):
        ubuntu_team = self.personset.getByName('ubuntu-team')
        no_priv = self.personset.getByName('no-priv')
        membership = self.membershipset.new(
            no_priv, ubuntu_team, TeamMembershipStatus.ADMIN)
        self.failUnless(
            membership == self.membershipset.getByPersonAndTeam(no_priv,
                                                                ubuntu_team))
        self.failUnless(membership.status == TeamMembershipStatus.ADMIN)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

