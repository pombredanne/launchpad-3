# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import httplib

from zope.security.proxy import removeSecurityProxy

from lazr.restfulclient.errors import HTTPError

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import (
    PersonVisibility,
    TeamSubscriptionPolicy,
    )
from lp.testing import (
    launchpadlib_for,
    login_person,
    logout,
    TestCaseWithFactory,
    )


class TestTeamLinking(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamLinking, self).setUp()
        self.team_owner = self.factory.makePerson(name='team-owner')
        self.private_team_one = self.factory.makeTeam(
            owner=self.team_owner,
            name='private-team',
            displayname='Private Team',
            visibility=PersonVisibility.PRIVATE)
        self.private_team_two = self.factory.makeTeam(
            owner=self.team_owner,
            name='private-team-two',
            displayname='Private Team Two',
            visibility=PersonVisibility.PRIVATE)

    def test_private_links(self):
        # A private team cannot be linked to another team, private or
        # or otherwise.
        launchpad = launchpadlib_for("test", self.team_owner.name)
        team_one = launchpad.people['private-team']
        team_two = launchpad.people['private-team-two']
        api_error = self.assertRaises(
            HTTPError,
            team_one.addMember,
            person=team_two)
        self.assertIn('Cannot link person', api_error.content)
        self.assertEqual(httplib.FORBIDDEN, api_error.response.status)


class TestTeamJoining(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_restricted_rejects_membership(self):
        # Calling person.join with a team that has a restricted membership
        # subscription policy should raise an HTTP error with BAD_REQUEST
        self.person = self.factory.makePerson(name='test-person')
        self.team = self.factory.makeTeam(name='test-team')
        login_person(self.team.teamowner)
        self.team.subscriptionpolicy = TeamSubscriptionPolicy.RESTRICTED
        logout()

        launchpad = launchpadlib_for("test", self.person)
        person = launchpad.people['test-person']
        api_error = self.assertRaises(
            HTTPError,
            person.join,
            team='test-team')
        self.assertEqual(httplib.BAD_REQUEST, api_error.response.status)

    def test_open_accepts_membership(self):
        # Calling person.join with a team that has an open membership
        # subscription policy should add that that user to the team.
        self.person = self.factory.makePerson(name='test-person')
        self.team = self.factory.makeTeam(name='test-team')
        login_person(self.team.teamowner)
        self.team.subscriptionpolicy = TeamSubscriptionPolicy.OPEN
        logout()

        launchpad = launchpadlib_for("test", self.person)
        test_person = launchpad.people['test-person']
        test_team = launchpad.people['test-team']
        test_person.join(team=test_team.self_link)
        login_person(self.team.teamowner)
        self.assertEqual(
            ['test-team'],
            [membership.team.name
                for membership in self.person.team_memberships])
        logout()
