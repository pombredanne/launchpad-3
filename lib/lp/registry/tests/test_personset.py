# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type

from unittest import TestLoader

import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.registry.model.person import PersonSet
from lp.registry.interfaces.mailinglistsubscription import (
    MailingListAutoSubscribePolicy)
from lp.registry.interfaces.person import (
    PersonCreationRationale, IPersonSet)
from lp.testing import (
    ANONYMOUS, TestCaseWithFactory, login, login_person, logout)

from canonical.database.sqlbase import cursor
from canonical.launchpad.testing.databasehelpers import (
    remove_all_sample_data_branches)
from canonical.testing import DatabaseFunctionalLayer


class TestPersonSetBranchCounts(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.person_set = getUtility(IPersonSet)

    def test_no_branches(self):
        """Initially there should be no branches."""
        self.assertEqual(0, self.person_set.getPeopleWithBranches().count())

    def test_five_branches(self):
        branches = [self.factory.makeAnyBranch() for x in range(5)]
        # Each branch has a different product, so any individual product
        # will return one branch.
        self.assertEqual(5, self.person_set.getPeopleWithBranches().count())
        self.assertEqual(1, self.person_set.getPeopleWithBranches(
                branches[0].product).count())


class TestPersonSetEnsurePerson(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer
    email_address = 'testing.ensure.person@example.com'
    displayname = 'Testing ensurePerson'
    rationale = PersonCreationRationale.SOURCEPACKAGEUPLOAD

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.person_set = getUtility(IPersonSet)

    def test_ensurePerson_returns_existing_person(self):
        # IPerson.ensurePerson returns existing person and does not
        # override its details.
        testing_displayname = 'will not be modified'
        testing_person = self.factory.makePerson(
            email=self.email_address, displayname=testing_displayname)

        ensured_person = self.person_set.ensurePerson(
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
        ensured_person = self.person_set.ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertTrue(ensured_person.hide_email_addresses)

    def test_ensurePerson_for_existing_account(self):
        # IPerson.ensurePerson creates missing Person for existing
        # Accounts.
        test_account = self.factory.makeAccount(
            self.displayname, email=self.email_address)
        self.assertIs(None, test_account.preferredemail.person)

        ensured_person = self.person_set.ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertEquals(test_account.id, ensured_person.account.id)
        self.assertTrue(ensured_person.hide_email_addresses)

    def test_ensurePerson_for_existing_account_with_person(self):
        # IPerson.ensurePerson return existing Person for existing
        # Accounts and additionally bounds the account email to the
        # Person in question.

        # Create a testing `Account` and a testing `Person` directly,
        # linked.
        testing_account = self.factory.makeAccount(
            self.displayname, email=self.email_address)
        testing_person = removeSecurityProxy(
            testing_account).createPerson(self.rationale)
        self.assertEqual(
            testing_person, testing_account.preferredemail.person)

        # Since there's an existing Person for the given email address,
        # IPersonSet.ensurePerson() will just return it.
        ensured_person = self.person_set.ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertEqual(testing_person, ensured_person)


class TestPersonSetMerge(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        # Use the unsecured PersonSet so that private methods can be tested.
        self.person_set = PersonSet()
        self.from_person = self.factory.makePerson()
        self.to_person = self.factory.makePerson()
        self.cur = cursor()

    def test__mergeMailingListSubscriptions_no_subscriptions(self):
        self.person_set._mergeMailingListSubscriptions(
            self.cur, self.from_person.id, self.to_person.id)
        self.assertEqual(0, self.cur.rowcount)

    def test__mergeMailingListSubscriptions_with_subscriptions(self):
        naked_person = removeSecurityProxy(self.from_person)
        naked_person.mailing_list_auto_subscribe_policy = (
            MailingListAutoSubscribePolicy.ALWAYS)
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'test-mailinglist', 'team-owner')
        login_person(self.team.teamowner)
        self.team.addMember(self.from_person, reviewer=self.team.teamowner)
        logout()
        transaction.commit()
        self.person_set._mergeMailingListSubscriptions(
            self.cur, self.from_person.id, self.to_person.id)
        self.assertEqual(1, self.cur.rowcount)


class TestPersonSetGetOrCreateByOpenIDIdentifier(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSetGetOrCreateByOpenIDIdentifier, self).setUp()
        self.agent = self.factory.makePerson(name='software-center-agent')
        login_person(self.agent)

    def test_only_for_agent_celebrity(self):
        # Only the software center agent can use this method.
        person_set = getUtility(IPersonSet)
        other_person = self.factory.makePerson()
        login_person(other_person)

        self.assertRaises(
            Unauthorized, getattr, person_set,
            'getOrCreateByOpenIDIdentifier')

        login(ANONYMOUS)
        self.assertRaises(
            Unauthorized, getattr, person_set,
            'getOrCreateByOpenIDIdentifier')

    def test_existing_person(self):
        person = self.factory.makePerson()
        openid_ident = removeSecurityProxy(person.account).openid_identifier

        result = getUtility(IPersonSet).getOrCreateByOpenIDIdentifier(
            self.agent, openid_ident, 'a@b.com')
        self.assertEqual(person, result)

    def test_existing_account_no_person(self):
        # A person is created with the correct rationale.
        account = self.factory.makeAccount('purchaser')
        openid_ident = removeSecurityProxy(account).openid_identifier

        person = getUtility(IPersonSet).getOrCreateByOpenIDIdentifier(
            self.agent, openid_ident, 'a@b.com')
        self.assertEqual(account, person.account)
        # The person is created with the correct rationale, creation
        # comment, registrant, appropriate display name and is not active.
        self.assertEqual(
            "when purchasing an application via Software Center.",
            person.creation_comment)
        self.assertEqual(
            PersonCreationRationale.SOFTWARE_CENTER_PURCHASE,
            person.creation_rationale)
        self.assertEqual(self.agent, person.registrant)

        # Is there some way we can ensure the person *isn't* valid?
        # The validpersoncacheview gives either email address != pref,
        # or account status (but we can't change that if it existed) or
        # unlink email_address.person (leaving email_address.account)?
        self.assertFalse(person.is_valid_person)

    def test_no_account_or_email(self):
        # A valid identifier can be used to create an account.
        person = getUtility(IPersonSet).getOrCreateByOpenIDIdentifier(
            self.agent, "openid-identifier", 'a@b.com')

        self.assertEqual(
            "openid-identifier",
            removeSecurityProxy(person.account).openid_identifier)
        self.assertEqual(self.agent, person.registrant)
        self.assertFalse(person.is_valid_person)

    def test_no_account_existing_email(self):
        other_account = self.factory.makeAccount('test', email='a@b.com')
        self.assertRaises(
            Exception, getUtility(IPersonSet).getOrCreateByOpenIDIdentifier,
            self.agent, "openid-identifier", 'a@b.com')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
