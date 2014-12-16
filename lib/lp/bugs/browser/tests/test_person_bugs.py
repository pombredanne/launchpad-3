# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for person bug views."""

__metaclass__ = type

from lp.app.browser.tales import MenuAPI
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class PersonBugsMenuTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_user(self):
        user = self.factory.makePerson()
        menu_api = MenuAPI(user)
        menu_api._selectedfacetname = 'bugs'
        enabled_links = sorted(
            link.name for link in menu_api.navigation.values()
            if link.enabled)
        expected_links = [
            'affectingbugs', 'assignedbugs', 'commentedbugs',
            'relatedbugs', 'reportedbugs', 'softwarebugs', 'subscribedbugs']
        self.assertEqual(expected_links, enabled_links)

    def test_team(self):
        team = self.factory.makeTeam()
        menu_api = MenuAPI(team)
        menu_api._selectedfacetname = 'bugs'
        enabled_links = sorted(
            link.name for link in menu_api.navigation.values()
            if link.enabled)
        expected_links = [
            'assignedbugs', 'relatedbugs', 'softwarebugs', 'subscribedbugs']
        self.assertEqual(expected_links, enabled_links)
