# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for `Account` objects."""

__metaclass__ = type

import unittest

import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces.account import (
    AccountCreationRationale, IAccountSet)
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.person import (
    IPerson, PersonCreationRationale)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class AccountTests(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(AccountTests, self).setUp(user='admin@canonical.com')

    def test_createPerson(self):
        account = self.factory.makeAccount("Test Account")
        # Account has no person.
        self.assertEqual(IPerson(account, None), None)
        self.assertEqual(account.preferredemail.person, None)

        person = account.createPerson(PersonCreationRationale.UNKNOWN)
        transaction.commit()
        self.assertNotEqual(person, None)
        self.assertEqual(person.account, account)
        self.assertEqual(IPerson(account), person)
        self.assertEqual(account.preferredemail.person, person)

        # Trying to create a person for an account with a person fails.
        self.assertRaises(AssertionError, account.createPerson,
                          PersonCreationRationale.UNKNOWN)

    def test_createPerson_requires_email(self):
        # It isn't possible to create a person for an account with no
        # preferred email address.
        account = getUtility(IAccountSet).new(
            AccountCreationRationale.UNKNOWN, "Test Account")
        self.assertEqual(account.preferredemail, None)
        self.assertRaises(AssertionError, account.createPerson,
                          PersonCreationRationale.UNKNOWN)

    def test_createPerson_sets_EmailAddress_person(self):
        # All email addresses for the account are associated with the
        # new person
        account = self.factory.makeAccount("Test Account")
        valid_email = self.factory.makeEmail(
            "validated@example.org", None, account,
            EmailAddressStatus.VALIDATED)
        new_email = self.factory.makeEmail(
            "new@example.org", None, account,
            EmailAddressStatus.NEW)
        old_email = self.factory.makeEmail(
            "old@example.org", None, account,
            EmailAddressStatus.OLD)

        person = account.createPerson(PersonCreationRationale.UNKNOWN)
        transaction.commit()
        self.assertEqual(valid_email.person, person)
        self.assertEqual(new_email.person, person)
        self.assertEqual(old_email.person, person)

    def test_setPreferredEmail(self):
        # Setting a new preferred email marks the old one as VALIDATED.
        account = self.factory.makeAccount("Test Account")
        first_email = account.preferredemail
        second_email = self.factory.makeEmail(
            "second-email@example.org", None, account,
            EmailAddressStatus.VALIDATED)
        account.setPreferredEmail(second_email)
        self.assertEqual(account.preferredemail, second_email)
        self.assertEqual(second_email.status, EmailAddressStatus.PREFERRED)
        self.assertEqual(first_email.status, EmailAddressStatus.VALIDATED)

    def test_setPreferredEmail_None(self):
        # Setting the preferred email to None sets the old preferred
        # email to VALIDATED.
        account = self.factory.makeAccount("Test Account")
        email = account.preferredemail
        account.setPreferredEmail(None)
        self.assertEqual(account.preferredemail, None)
        self.assertEqual(email.status, EmailAddressStatus.VALIDATED)

    def test_validateAndEnsurePreferredEmail(self):
        # validateAndEnsurePreferredEmail() sets the email status to
        # VALIDATED if there is no existing preferred email.
        account = self.factory.makeAccount("Test Account")
        self.assertNotEqual(account.preferredemail, None)
        new_email = self.factory.makeEmail(
            "new-email@example.org", None, account,
            EmailAddressStatus.NEW)
        account.validateAndEnsurePreferredEmail(new_email)
        self.assertEqual(new_email.status, EmailAddressStatus.VALIDATED)

    def test_validateAndEsnurePreferredEmail_no_preferred(self):
        # validateAndEnsurePreferredEmail() sets the new email as
        # preferred if there was no preferred email.
        account = self.factory.makeAccount("Test Account")
        account.setPreferredEmail(None)
        new_email = self.factory.makeEmail(
            "new-email@example.org", None, account,
            EmailAddressStatus.NEW)
        account.validateAndEnsurePreferredEmail(new_email)
        self.assertEqual(new_email.status, EmailAddressStatus.PREFERRED)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

