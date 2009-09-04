# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type

from unittest import TestLoader

from zope.component import getUtility

from lp.registry.model.person import PersonSet
from lp.registry.interfaces.person import (
    PersonCreationRationale, IPersonSet)
from lp.testing import TestCaseWithFactory
from canonical.launchpad.testing.databasehelpers import (
    remove_all_sample_data_branches)
from canonical.testing import LaunchpadFunctionalLayer


class TestPersonSetBranchCounts(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()

    def test_no_branches(self):
        """Initially there should be no branches."""
        self.assertEqual(0, PersonSet().getPeopleWithBranches().count())

    def test_five_branches(self):
        branches = [self.factory.makeAnyBranch() for x in range(5)]
        # Each branch has a different product, so any individual product
        # will return one branch.
        self.assertEqual(5, PersonSet().getPeopleWithBranches().count())
        self.assertEqual(1, PersonSet().getPeopleWithBranches(
                branches[0].product).count())


class TestPersonSetEnsurePerson(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_ensurePerson_for_existing_account(self):
        # Check if IPerson.ensurePerson can create missing Person
        # for existing Accounts and it will have 'hide_email_addresses'
        # set to True.
        email_address = 'sso-test@canonical.com'
        account = self.factory.makeAccount(
            'testing account', email=email_address)
        person = getUtility(IPersonSet).ensurePerson(
            email_address, 'Testing person',
            PersonCreationRationale.SOURCEPACKAGEUPLOAD)
        self.assertEquals(account.id, person.account.id)
        self.assertTrue(person.hide_email_addresses)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
