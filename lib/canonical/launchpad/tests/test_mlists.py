# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test mailing list stuff."""

__metaclass__ = type


import os
import errno
import tempfile
import unittest

# Don't use cStringIO in case Unicode leaks through.
from StringIO import StringIO

from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.mlistimport import Importer
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing.layers import DatabaseFunctionalLayer


factory = LaunchpadObjectFactory()

class CapturingLogger(FakeLogger):
    def __init__(self):
        self.io = StringIO()

    def message(self, prefix, *stuff, **kws):
        print >> self.io, prefix, ' '.join(stuff)


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
        # A temporary filename for some of the tests.
        fd, self.filename = tempfile.mkstemp()
        os.close(fd)
        # A capturing logger.
        self.logger = CapturingLogger()

    def tearDown(self):
        try:
            os.remove(self.filename)
        except OSError, error:
            if error.errno != errno.ENOENT:
                raise

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

    def test_extended_import_membership(self):
        # Test the import of a list/team membership, where all email
        # addresses being imported actually exist in Launchpad.
        importer = Importer('aardvarks')
        importer.importAddresses((
            'anne.person@example.com (Anne Person)',
            'Bart Q. Person <bperson@example.org>',
            'cris.person@example.com',
            'dperson@example.org',
            'elly.person@example.com (Elly Q. Person)',
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

    def test_import_from_file(self):
        # Test importing addresses from a file.
        importer = Importer('aardvarks')
        # Write the addresses to import to a file.  Use various
        # combinations of formats supported by parseaddr().
        out_file = open(self.filename, 'w')
        try:
            print >> out_file, 'Anne Person <anne.person@example.com>'
            print >> out_file, 'bart.person@example.com (Bart Q. Person)'
            print >> out_file, 'cperson@example.org'
            print >> out_file, 'dperson@example.org (Dave Person)'
            print >> out_file, 'Elly Q. Person <eperson@example.org'
        finally:
            out_file.close()
        importer.importFromFile(self.filename)
        self.assertEqual(
            sorted(person.name for person in self.team.allmembers),
            [u'anne', u'bart', u'cris', u'dave', u'elly', u'teamowner'])
        self.assertEqual(
            sorted(email.email
                   for email in self.mailing_list.getSubscribedAddresses()),
            [u'anne.person@example.com', u'bart.person@example.com',
             u'cperson@example.org', u'dperson@example.org',
             u'eperson@example.org'])

    def test_import_from_file_with_non_persons(self):
        # Test the import of a list/team membership from a file where
        # not all the email addresses are associated with registered
        # people.
        importer = Importer('aardvarks')
        # Write the addresses to import to a file.  Use various
        # combinations of formats supported by parseaddr().
        out_file = open(self.filename, 'w')
        try:
            print >> out_file, 'Anne Person <anne.person@example.com>'
            print >> out_file, 'bart.person@example.com (Bart Q. Person)'
            print >> out_file, 'cperson@example.org'
            print >> out_file, 'dperson@example.org (Dave Person)'
            print >> out_file, 'Elly Q. Person <eperson@example.org'
            # Non-persons.
            print >> out_file, 'fperson@example.org (Fred Q. Person)'
            print >> out_file, 'Gwen Person <gwen.person@example.com>'
            print >> out_file, 'hperson@example.org'
            print >> out_file, 'iris.person@example.com'
        finally:
            out_file.close()
        importer.importFromFile(self.filename)
        self.assertEqual(
            sorted(person.name for person in self.team.allmembers),
            [u'anne', u'bart', u'cris', u'dave', u'elly', u'teamowner'])
        self.assertEqual(
            sorted(email.email
                   for email in self.mailing_list.getSubscribedAddresses()),
            [u'anne.person@example.com', u'bart.person@example.com',
             u'cperson@example.org', u'dperson@example.org',
             u'eperson@example.org'])

    def test_import_from_file_with_invalid_emails(self):
        # Test importing addresses from a file with invalid emails.
        importer = Importer('aardvarks')
        # Give Anne a new invalid email address.
        factory.makeEmail('anne.x.person@example.net', self.anne,
                          EmailAddressStatus.NEW)
        # Write the addresses to import to a file.  Use various
        # combinations of formats supported by parseaddr().
        out_file = open(self.filename, 'w')
        try:
            print >> out_file, 'Anne Person <anne.x.person@example.net>'
            print >> out_file, 'bart.person@example.com (Bart Q. Person)'
            print >> out_file, 'cperson@example.org'
            print >> out_file, 'dperson@example.org (Dave Person)'
            print >> out_file, 'Elly Q. Person <eperson@example.org'
        finally:
            out_file.close()
        importer.importFromFile(self.filename)
        self.assertEqual(
            sorted(person.name for person in self.team.allmembers),
            [u'bart', u'cris', u'dave', u'elly', u'teamowner'])
        self.assertEqual(
            sorted(email.email
                   for email in self.mailing_list.getSubscribedAddresses()),
            [u'bart.person@example.com',
             u'cperson@example.org', u'dperson@example.org',
             u'eperson@example.org'])

    def test_logging(self):
        # Test that nothing gets logged when all imports are fine.
        importer = Importer('aardvarks')
        importer.importAddresses((
            'anne.person@example.com',
            'bperson@example.org',
            'cris.person@example.com',
            'dperson@example.org',
            'elly.person@example.com',
            ))
        self.assertEqual(self.logger.io.getvalue(), '')

    def test_logging_extended(self):
        # Test that nothing gets logged when all imports are fine.
        importer = Importer('aardvarks', self.logger)
        importer.importAddresses((
            'anne.person@example.com (Anne Person)',
            'Bart Q. Person <bperson@example.org>',
            'cris.person@example.com',
            'dperson@example.org',
            'elly.person@example.com (Elly Q. Person)',
            ))
        self.assertEqual(self.logger.io.getvalue(), '')

    def test_logging_with_non_persons(self):
        # Test that non-persons that were not imported are logged.
        importer = Importer('aardvarks', self.logger)
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
            self.logger.io.getvalue(),
            ('ERROR No person for address: fperson@example.org\n'
             'ERROR No person for address: gwen.person@example.com\n'
             'ERROR No person for address: hperson@example.org\n'))

    def test_logging_with_invalid_emails(self):
        # Test that invalid emails that were not imported are logged.
        importer = Importer('aardvarks', self.logger)
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
            self.logger.io.getvalue(),
            'ERROR No valid email for address: anne.x.person@example.net\n')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

