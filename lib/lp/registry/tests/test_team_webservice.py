# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from lazr.restfulclient.errors import HTTPError

from canonical.testing import DatabaseFunctionalLayer
from lp.registry.interfaces.person import PersonVisibility
from lp.testing import (
    launchpadlib_for,
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
        self.assertEqual(400, api_error.response.status)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
