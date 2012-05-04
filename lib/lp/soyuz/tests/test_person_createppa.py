# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the IPerson.createPPA() method."""

__metaclass__ = type

from lp.registry.errors import PPACreationError
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestCreatePPA(TestCaseWithFactory):
    """Test that the IPerson.createPPA method behaves as expected."""

    layer = DatabaseFunctionalLayer

    def test_default_name(self):
        person = self.factory.makePerson()
        ppa = person.createPPA()
        self.assertEqual(ppa.name, 'ppa')

    def test_private(self):
        with celebrity_logged_in('commercial_admin') as person:
            ppa = person.createPPA(private=True)
            self.assertEqual(True, ppa.private)

    def test_private_without_permission(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            self.assertRaises(
                PPACreationError, person.createPPA, private=True)

    def test_suppress_subscription_notifications(self):
        with celebrity_logged_in('commercial_admin') as person:
            ppa = person.createPPA(suppress_subscription_notifications=True)
            self.assertEqual(True, ppa.suppress_subscription_notifications)

    def test_suppress_without_permission(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            self.assertRaises(
                PPACreationError, person.createPPA,
                suppress_subscription_notifications=True)
