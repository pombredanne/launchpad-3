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
    email_address = 'testing.ensure.person@example.com'
    displayname = 'Testing ensurePerson'
    rationale = PersonCreationRationale.SOURCEPACKAGEUPLOAD

    def test_ensurePerson_returns_existing_person(self):
        # IPerson.ensurePerson returns existing person and does not
        # override its details.
        testing_displayname = 'will not be modified'
        testing_person = self.factory.makePerson(
            email=self.email_address, displayname=testing_displayname)

        ensured_person = getUtility(IPersonSet).ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertEquals(testing_person.id, ensured_person.id)
        self.assertIsNot(
            ensured_person.displayname, self.displayname,
            'Person.displayname should not be overridden.')
        self.assertIsNot(
            ensured_person.creation_rationale, self.rationale,
            'Person.creation_rationale should not be overridden.')

    def test_ensurePerson_hides_new_person_email(self):
        # IPersonSet.ensurePerson creates new person with
        # 'hide_email_addresses' set.
        ensured_person = getUtility(IPersonSet).ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertTrue(ensured_person.hide_email_addresses)

    def test_ensurePerson_for_existing_account(self):
        # IPerson.ensurePerson creates missing Person for existing
        # Accounts.
        test_account = self.factory.makeAccount(
            self.displayname, email=self.email_address)
        self.assertIs(None, test_account.preferredemail.person)

        ensured_person = getUtility(IPersonSet).ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertEquals(test_account.id, ensured_person.account.id)
        self.assertTrue(ensured_person.hide_email_addresses)

    def test_ensurePerson_for_existing_account_with_person(self):
        # IPerson.ensurePerson return existing Person for existing
        # Accounts.

        # Create a testing `Account` and a testing `Person` directly,
        # linked. However the `Account` email is not linked to the
        # `Person`. (XXX ?!?!)
        testing_account = self.factory.makeAccount(
            self.displayname, email=self.email_address)
        testing_person = self.factory.makePerson(displayname=self.displayname)
        testing_person.account = testing_account.id
        self.assertIs(
            testing_account.id, testing_account.preferredemail.account.id)
        self.assertIs(None, testing_account.preferredemail.person)

        ensured_person = getUtility(IPersonSet).ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertEquals(testing_person.id, ensured_person.id)



def test_suite():
    return TestLoader().loadTestsFromName(__name__)
