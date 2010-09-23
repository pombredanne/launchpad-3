# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestTeamLinking(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.private_team_one = self.factory.makeTeam(
            name='private team',
            displayname='Private Team',
            visiblity=PersonVisibility.PRIVATE)
        self.private_team_two = self.factory.makeTeam(
            name='private team two',
            displayname='Private Team Two',
            visiblity=PersonVisibility.PRIVATE)
        self.public_team_one = self.factory.makeTeam(
            name='team one',
            displayname='Team One',
            visiblity=PersonVisibility.PRIVATE)
        self.public_team_two = self.factory.makeTeam(
            name='team two',
            displayname='Team Two',
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def test_private_links(self):
        # A private team cannot be linked to another team, private or
        # or otherwise.
        login(self.private_team_one.teamowner)
        self.webservice.post('/~%s' % self.private_team_two)
        # special sauce?

class TestPersonRepresentation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('guilherme.salgado@canonical.com ')
        self.person = self.factory.makePerson(
            name='test-person', displayname='Test Person')
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def test_GET_xhtml_representation(self):
        # Remove the security proxy because IPerson.name is protected.
        person_name = removeSecurityProxy(self.person).name
        response = self.webservice.get(
            '/~%s' % person_name, 'application/xhtml+xml')

        self.assertEqual(response.status, 200)

        rendered_comment = response.body
        self.assertEquals(
            rendered_comment,
            '<a href="/~test-person" class="sprite person">Test Person</a>')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
