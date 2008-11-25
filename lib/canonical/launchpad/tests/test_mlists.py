# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test mailing list stuff."""

__metaclass__ = type

import unittest

from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.scripts.mlistimport import Importer
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing.layers import DatabaseFunctionalLayer


factory = LaunchpadObjectFactory()


class TestMailingListImports(unittest.TestCase):
    """Test mailing list imports."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Create a team and a mailing list for the team to test.
        login('foo.bar@canonical.com')
        self.anne = factory.makePersonByName('Anne')
        self.bart = factory.makePersonByName('Bart')
        self.cris = factory.makePersonByName('Cris')
        self.dave = factory.makePersonByName('Dave')
        self.elly = factory.makePersonByName('Elly')
        self.teamowner = factory.makePersonByName('Teamowner')
        self.team, self.mailing_list = factory.makeTeamAndMailingList(
            'aardvarks', 'teamowner')

    def test_simple_import_membership(self):
        # Test the import of a list/team membership, where all email
        # addresses being imported actually exist in Launchpad.
        importer = Importer('aardvarks')
        importer.importAddresses((
            'anne.person@example.com',
            'bperson@example.org',
            'cris.person@example.com',
            'dperson@example.org',
            'elly.person@example.com',
            ))
        self.assertEqual(
            sorted(person.name for person in self.team.allmembers),
            [u'anne', u'bart', u'cris', u'dave', u'elly', u'teamowner'])
        self.assertEqual(
            sorted(email.email
                   for email in self.mailing_list.getSubscribedAddresses()),
            [u'anne.person@example.com', u'bperson@example.org',
             u'cris.person@example.com', u'dperson@example.org',
             u'elly.person@example.com'])

    def test_import_with_non_persons(self):
        # Test the import of a list/team membership where not all the
        # email addresses are associated with registered people.
        importer = Importer('aardvarks')
        importer.importAddresses((
            'anne.person@example.com',
            'bperson@example.org',
            'cris.person@example.com',
            'dperson@example.org',
            'elly.person@example.com',
            # Non-persons.
            'fperson@example.org',
            'gwen.person@example.com',
            'hperson@example.org',
            ))
        self.assertEqual(
            sorted(person.name for person in self.team.allmembers),
            [u'anne', u'bart', u'cris', u'dave', u'elly', u'teamowner'])
        self.assertEqual(
            sorted(email.email
                   for email in self.mailing_list.getSubscribedAddresses()),
            [u'anne.person@example.com', u'bperson@example.org',
             u'cris.person@example.com', u'dperson@example.org',
             u'elly.person@example.com'])

    def test_import_with_invalid_emails(self):
        # Test the import of a list/team membership where all the
        # emails are associated with valid people, but not all of the
        # email addresses are validated.
        importer = Importer('aardvarks')
        # Give Anne a new invalid email address.
        factory.makeEmail('anne.x.person@example.net', self.anne,
                          EmailAddressStatus.NEW)
        importer.importAddresses((
            # Import Anne's alternative address.
            'anne.x.person@example.net',
            'bperson@example.org',
            'cris.person@example.com',
            'dperson@example.org',
            'elly.person@example.com',
            ))
        self.assertEqual(
            sorted(person.name for person in self.team.allmembers),
            [u'bart', u'cris', u'dave', u'elly', u'teamowner'])
        self.assertEqual(
            sorted(email.email
                   for email in self.mailing_list.getSubscribedAddresses()),
            [u'bperson@example.org',
             u'cris.person@example.com', u'dperson@example.org',
             u'elly.person@example.com'])
        


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

