# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type

import transaction

from zope.component import getUtility

from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.testing import DatabaseFunctionalLayer

from lp.registry.interfaces.mailinglist import MailingListStatus
from lp.testing import login_celebrity, login_person, TestCaseWithFactory


class TestTeamContactAddress(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def getAllEmailAddresses(self):
        transaction.commit()
        all_addresses = self.store.find(
            EmailAddress, EmailAddress.personID == self.team.id)
        return [address for address in all_addresses.order_by('email')]

    def createMailingListAndGetAddress(self):
        mailing_list = self.factory.makeMailingList(
            self.team, self.team.teamowner)
        return getUtility(IEmailAddressSet).getByEmail(
                mailing_list.address)

    def setUp(self):
        super(TestTeamContactAddress, self).setUp()
        self.team = self.factory.makeTeam(name='alpha')
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
        self.team.setContactAddress(self.address)
        new_address = self.factory.makeEmail('new@noplace.org', self.team)
        self.team.setContactAddress(new_address)
        self.assertEqual(new_address, self.team.preferredemail)
        self.assertEqual([new_address], self.getAllEmailAddresses())

    def test_setContactAddress_to_mailing_list(self):
        self.team.setContactAddress(self.address)
        list_address = self.createMailingListAndGetAddress()
        self.team.setContactAddress(list_address)
        self.assertEqual(list_address, self.team.preferredemail)
        self.assertEqual([list_address], self.getAllEmailAddresses())

    def test_setContactAddress_from_mailing_list(self):
        list_address = self.createMailingListAndGetAddress()
        self.team.setContactAddress(list_address)
        new_address = self.factory.makeEmail('new@noplace.org', self.team)
        self.team.setContactAddress(new_address)
        self.assertEqual(new_address, self.team.preferredemail)
        self.assertEqual(
            [list_address, new_address], self.getAllEmailAddresses())

    def test_setContactAddress_from_mailing_list_to_none(self):
        list_address = self.createMailingListAndGetAddress()
        self.team.setContactAddress(list_address)
        self.team.setContactAddress(None)
        self.assertEqual(None, self.team.preferredemail)
        self.assertEqual([list_address], self.getAllEmailAddresses())

    def test_setContactAddress_after_purged_mailing_list_and_rename(self):
        # This is the rare case where a list is purged for a team rename,
        # then the contact address is set/unset sometime afterwards.
        # The old mailing list address belongs the the team, but not the list.
        # 1. Create then purge a mailing list.
        list_address = self.createMailingListAndGetAddress()
        mailing_list = self.team.mailing_list
        mailing_list.deactivate()
        mailing_list.transitionToStatus(MailingListStatus.INACTIVE)
        mailing_list.purge()
        transaction.commit()
        # 2. Rename the team.
        login_celebrity('admin')
        self.team.name = 'beta'
        login_person(self.team.teamowner)
        # 3. Set the contact address.
        self.team.setContactAddress(None)
        self.assertEqual(None, self.team.preferredemail)
        self.assertEqual([], self.getAllEmailAddresses())
