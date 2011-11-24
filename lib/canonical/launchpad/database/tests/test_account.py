# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `Account` objects."""

__metaclass__ = type
__all__ = []

from testtools.testcase import ExpectedException
import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces.account import (
    AccountCreationRationale,
    IAccountSet,
    )
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import (
    IPerson,
    PersonCreationRationale,
    )
from lp.testing import TestCaseWithFactory


class CreatePersonTests(TestCaseWithFactory):
    """Tests for `IAccount.createPerson`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(CreatePersonTests, self).setUp(user='admin@canonical.com')

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

    def test_createPerson_uses_name(self):
        # A optional user name can be provided. Normally the name is
        # generated from the email address.
        account = self.factory.makeAccount("Test Account")
        person = account.createPerson(
            PersonCreationRationale.UNKNOWN, name="sam.bell")
        self.failUnlessEqual("sam.bell", person.name)

    def test_createPerson_uses_comment(self):
        # An optional creation comment can be provided.
        account = self.factory.makeAccount("Test Account")
        person = account.createPerson(
            PersonCreationRationale.UNKNOWN,
            comment="when importing He-3 from the Moon")
        self.failUnlessEqual(
            "when importing He-3 from the Moon",
            person.creation_comment)

    def test_getByEmail_non_ascii_bytes(self):
        """Lookups for non-ascii addresses should raise LookupError.

        This tests the case where input is a bytestring.
        """
        with ExpectedException(LookupError, r"'SaraS\\xe1nchez@cocolee.net'"):
            getUtility(IAccountSet).getByEmail('SaraS\xe1nchez@cocolee.net')

    def test_getByEmail_non_ascii_unicode(self):
        """Lookups for non-ascii addresses should raise LookupError.

        This tests the case where input is a unicode string.
        """
        with ExpectedException(LookupError, r"u'SaraS\\xe1nchez@.*.net'"):
            getUtility(IAccountSet).getByEmail(u'SaraS\xe1nchez@cocolee.net')


class EmailManagementTests(TestCaseWithFactory):
    """Test email account management interfaces for `IAccount`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(EmailManagementTests, self).setUp(user='admin@canonical.com')

    def test_setPreferredEmail(self):
        # Setting a new preferred email marks the old one as VALIDATED.
        account = self.factory.makeAccount("Test Account")
        first_email = account.preferredemail
        second_email = self.factory.makeEmail(
            "second-email@example.org", None, account,
            EmailAddressStatus.VALIDATED)
        transaction.commit()
        account.setPreferredEmail(second_email)
        transaction.commit()
        self.assertEqual(account.preferredemail, second_email)
        self.assertEqual(second_email.status, EmailAddressStatus.PREFERRED)
        self.assertEqual(first_email.status, EmailAddressStatus.VALIDATED)

    def test_setPreferredEmail_None(self):
        # Setting the preferred email to None sets the old preferred
        # email to VALIDATED.
        account = self.factory.makeAccount("Test Account")
        email = account.preferredemail
        transaction.commit()
        account.setPreferredEmail(None)
        transaction.commit()
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
        transaction.commit()
        account.validateAndEnsurePreferredEmail(new_email)
        transaction.commit()
        self.assertEqual(new_email.status, EmailAddressStatus.VALIDATED)

    def test_validateAndEsnurePreferredEmail_no_preferred(self):
        # validateAndEnsurePreferredEmail() sets the new email as
        # preferred if there was no preferred email.
        account = self.factory.makeAccount("Test Account")
        account.setPreferredEmail(None)
        new_email = self.factory.makeEmail(
            "new-email@example.org", None, account,
            EmailAddressStatus.NEW)
        transaction.commit()
        account.validateAndEnsurePreferredEmail(new_email)
        transaction.commit()
        self.assertEqual(new_email.status, EmailAddressStatus.PREFERRED)

    def test_validated_emails(self):
        account = self.factory.makeAccount("Test Account")
        self.factory.makeEmail(
            "new-email@example.org", None, account,
            EmailAddressStatus.NEW)
        validated_email = self.factory.makeEmail(
            "validated-email@example.org", None, account,
            EmailAddressStatus.VALIDATED)
        self.factory.makeEmail(
            "old@example.org", None, account,
            EmailAddressStatus.OLD)
        transaction.commit()
        self.assertContentEqual(account.validated_emails, [validated_email])

    def test_guessed_emails(self):
        account = self.factory.makeAccount("Test Account")
        new_email = self.factory.makeEmail(
            "new-email@example.org", None, account,
            EmailAddressStatus.NEW)
        self.factory.makeEmail(
            "validated-email@example.org", None, account,
            EmailAddressStatus.VALIDATED)
        self.factory.makeEmail(
            "old@example.org", None, account,
            EmailAddressStatus.OLD)
        transaction.commit()
        self.assertContentEqual(account.guessed_emails, [new_email])
