# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test IPerson.createNewPPA()"""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import (
    PPACreationError,
    TeamSubscriptionPolicy,
    )
from lp.testing import TestCaseWithFactory
from zope.security.proxy import removeSecurityProxy


class TestCreateNewPPA(TestCaseWithFactory):
    """Test that the IPerson.createNewPPA method behaves as expected."""

    layer = DatabaseFunctionalLayer

    def test_no_acceptance(self):
        person = self.factory.makePerson()
        self.assertRaisesWithContent(
            PPACreationError, 'You must accept the PPA Terms of Service '
            'to enable a PPA.', person.createNewPPA)

    def test_open_team_cannot_create(self):
        team = self.factory.makeTeam()
        removeSecurityProxy(team).subscriptionpolicy = (
            TeamSubscriptionPolicy.OPEN)
        self.assertRaisesWithContent(
            PPACreationError, 'Open teams can not have PPAs.',
            team.createNewPPA, None, None, None, True)

    def test_create_distribution_name(self):
        person = self.factory.makePerson()
        self.assertRaisesWithContent(
            PPACreationError, 'Archives cannot have the same name as '
            'its distribution.', person.createNewPPA,
            'ubuntu', None, None, True)

    def test_create_two_ppas(self):
        person = self.factory.makePerson()
        person.createNewPPA(acceptance=True)
        self.assertRaisesWithContent(
            PPACreationError, "You already have a PPA named 'ppa'.",
            person.createNewPPA, None, None, None, True)

    def test_create_ppa(self):
        person = self.factory.makePerson()
        ppa = person.createNewPPA(acceptance=True)
        self.assertEqual(ppa.name, 'ppa')
