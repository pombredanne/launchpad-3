# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for RevisionAuthors."""

__metaclass__ = type

import transaction
from unittest import TestCase, TestLoader

from canonical.config import config
from canonical.launchpad.database.revision import RevisionAuthor, RevisionSet
from canonical.launchpad.interfaces import (
    EmailAddressStatus, IPersonSet)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer

from zope.component import getUtility


class TestRevisionEmailExtraction(TestCase):
    """When a RevisionAuthor is created, the email address is extracted.

    This email address is stored in another field in order to be easily
    matched to user's email addresses.  This is primarily used when a user
    has newly validated an email address, and we want to see if any of
    the existing revision author's have the matching email address.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)

    def test_email_extracted_from_name(self):
        # Check that a valid email address is extracted from the name.
        name = '"Harry Potter" <harry@canonical.com>'
        author = RevisionSet()._createRevisionAuthor(name)
        self.assertEqual(name, author.name)
        self.assertEqual('harry@canonical.com', author.email)
        self.assertEqual(None, author.person)

    def test_email_extracted_from_name_alternate(self):
        # Check that a valid email address is extracted from the name.
        name = 'harry@canonical.com (Harry Potter)'
        author = RevisionSet()._createRevisionAuthor(name)
        self.assertEqual(name, author.name)
        self.assertEqual('harry@canonical.com', author.email)
        self.assertEqual(None, author.person)

    def test_bad_email_not_set(self):
        # Check that a name that doesn't have an email address, doesn't set
        # one.
        name = 'Harry Potter'
        author = RevisionSet()._createRevisionAuthor(name)
        self.assertEqual(name, author.name)
        self.assertEqual(None, author.email)
        self.assertEqual(None, author.person)


class MakeHarryTestCase(TestCase):
    """A base class for test cases that need to make harry."""

    layer = LaunchpadZopelessLayer

    def _makeHarry(self, email_address_status=None):
        factory = LaunchpadObjectFactory()
        return factory.makePerson(
            email='harry@canonical.com',
            name='harry',
            email_address_status=email_address_status)


class TestRevisionAuthorMatching(MakeHarryTestCase):
    """Only a validated email address will make a link to a person.

    Email addresses that are NEW are not validated, and so do not cause
    the link to be formed between the RevisionAuthor and the Person.

    OLD email addresses are also linked as they were once VALIDATED
    and revisions may be old.
    """

    def _createRevisionAuthor(self):
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
        return RevisionSet()._createRevisionAuthor(
            '"Harry Potter" <harry@canonical.com>')

    def test_new_harry_not_linked(self):
        # Check a NEW email address is not used to link.
        harry = self._makeHarry(EmailAddressStatus.NEW)
        author = self._createRevisionAuthor()
        self.assertEqual('harry@canonical.com', author.email)
        self.assertEqual(None, author.person)

    def test_validated_harry_linked(self):
        # Check a VALIDATED email address is used to link.
        harry = self._makeHarry(EmailAddressStatus.VALIDATED)
        author = self._createRevisionAuthor()
        # Reget harry as the SQLObject cache has been flushed on
        # transaction boundary.
        harry = getUtility(IPersonSet).getByName('harry')
        self.assertEqual('harry@canonical.com', author.email)
        self.assertEqual(harry, author.person)

    def test_old_harry_linked(self):
        # Check a OLD email address is used to link.
        harry = self._makeHarry(EmailAddressStatus.OLD)
        author = self._createRevisionAuthor()
        # Reget harry as the SQLObject cache has been flushed on
        # transaction boundary.
        harry = getUtility(IPersonSet).getByName('harry')
        self.assertEqual('harry@canonical.com', author.email)
        self.assertEqual(harry, author.person)

    def test_preferred_harry_linked(self):
        # Check a PREFERRED email address is used to link.
        harry = self._makeHarry(EmailAddressStatus.PREFERRED)
        author = self._createRevisionAuthor()
        # Reget harry as the SQLObject cache has been flushed on
        # transaction boundary.
        harry = getUtility(IPersonSet).getByName('harry')
        self.assertEqual('harry@canonical.com', author.email)
        self.assertEqual(harry, author.person)


class TestNewlyValidatedEmailsLinkRevisionAuthors(MakeHarryTestCase):

    def setUp(self):
        # Create a revision author that doesn't have a user yet.
        launchpad_dbuser = config.launchpad.dbuser
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
        self.author = RevisionSet()._createRevisionAuthor(
            '"Harry Potter" <harry@canonical.com>')
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(launchpad_dbuser)
        # Reget the revision author as we have crossed a transaction boundary.
        self.author = RevisionAuthor.byName(self.author.name)

    def test_validated_email_updates(self):
        # A newly validated email for a user.
        self.assertEqual(None, self.author.person,
                         'No author should be initially set.')
        harry = self._makeHarry(EmailAddressStatus.NEW)
        # Since the email address is initially new, there should still be
        # no link.
        self.assertEqual(None, self.author.person,
                         'No author should be set yet.')
        email = harry.guessedemails[0]
        harry.validateAndEnsurePreferredEmail(email)
        # The link is now made.
        self.assertEqual(harry, self.author.person,
                         'Harry should now be the author.')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
