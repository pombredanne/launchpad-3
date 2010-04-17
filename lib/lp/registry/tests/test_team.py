# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type

import transaction
from unittest import TestLoader

from storm.store import Store

from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory, login_person, logout


class TestTeamContactAddress(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def getAllEmailAddresses(self):
        transaction.commit()
        all_addresses = self.store.find(
            EmailAddress, EmailAddress.personID == self.team.id)
        return [address for address in all_addresses.order_by('email')]

    def setUp(self):
        super(TestTeamContactAddress, self).setUp()
        self.team = self.factory.makeTeam()
        self.address = self.factory.makeEmail('team@noplace.org', self.team)
        self.store = IMasterStore(self.address)

    def test_setContactAddress_from_none(self):
        self.team.setContactAddress(self.address)
        self.assertEqual(self.address, self.team.preferredemail)
        self.assertEqual([self.address], self.getAllEmailAddresses())

    def test_setContactAddress_to_none(self):
        self.team.setContactAddress(self.address)
        self.team.setContactAddress(None)
        self.assertEqual(None, self.team.preferredemail)
        self.assertEqual([], self.getAllEmailAddresses())

    def test_setContactAddress_to_new_address(self):
        old_address = self.factory.makeEmail('old@noplace.org', self.team)
        self.team.setContactAddress(old_address)
        self.assertEqual(old_address, self.team.preferredemail)
        self.assertEqual([old_address], self.getAllEmailAddresses())

        self.address = self.factory.makeEmail('team@noplace.org', self.team)
        self.team.setContactAddress(self.address)
        self.assertEqual(self.address, self.team.preferredemail)
        self.assertEqual([self.address], self.getAllEmailAddresses())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
