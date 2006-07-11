# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys
import unittest

from zope.component import getUtility
from canonical.launchpad.interfaces import IPersonSet, IEmailAddressSet
from canonical.launchpad.scripts import sftracker

from canonical.functional import ZopelessLayer
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.librarian.ftests.harness import LibrarianTestSetup


class PersonMappingTestCase(unittest.TestCase):

    layer = ZopelessLayer

    def setUp(self):
        self.zopeless = LaunchpadZopelessTestSetup()
        self.zopeless.setUp()

    def tearDown(self):
        self.zopeless.tearDown()

    def test_create_person(self):
        # Test that person creation works
        person = getUtility(IPersonSet).getByEmail('foo@users.sourceforge.net')
        self.assertEqual(person, None)

        importer = sftracker.TrackerImporter(None)
        person = importer.person('foo')
        self.assertNotEqual(person, None)
        self.assertEqual(person.guessedemails.count(), 1)
        self.assertEqual(person.guessedemails[0].email,
                         'foo@users.sourceforge.net')

    def test_find_existing_person(self):
        person = getUtility(IPersonSet).getByEmail('foo@users.sourceforge.net')
        self.assertEqual(person, None)
        person = getUtility(IPersonSet).ensurePerson(
            'foo@users.sourceforge.net', None)
        self.assertNotEqual(person, None)

        importer = sftracker.TrackerImporter(None)
        self.assertEqual(importer.person('foo'), person)

    def test_nobody_person(self):
        # Test that TrackerImporter.person() returns None where appropriate
        importer = sftracker.TrackerImporter(None)
        self.assertEqual(importer.person(None), None)
        self.assertEqual(importer.person(''), None)
        self.assertEqual(importer.person('nobody'), None)

    def test_verify_new_person(self):
        importer = sftracker.TrackerImporter(None, verify_users=True)
        person = importer.person('foo')
        self.assertNotEqual(person, None)
        self.assertNotEqual(person.preferredemail, None)
        self.assertEqual(person.preferredemail.email,
                         'foo@users.sourceforge.net')

    def test_verify_existing_person(self):
        person = getUtility(IPersonSet).ensurePerson(
            'foo@users.sourceforge.net', None)
        self.assertEqual(person.preferredemail, None)

        importer = sftracker.TrackerImporter(None, verify_users=True)
        person = importer.person('foo')
        self.assertNotEqual(person.preferredemail, None)
        self.assertEqual(person.preferredemail.email,
                         'foo@users.sourceforge.net')

    def test_verify_doesnt_clobber_preferred_email(self):
        person = getUtility(IPersonSet).ensurePerson(
            'foo@users.sourceforge.net', None)
        email = getUtility(IEmailAddressSet).new('foo@example.com', person.id)
        person.setPreferredEmail(email)
        self.assertEqual(person.preferredemail.email, 'foo@example.com')

        importer = sftracker.TrackerImporter(None, verify_users=True)
        person = importer.person('foo')
        self.assertNotEqual(person.preferredemail, None)
        self.assertEqual(person.preferredemail.email, 'foo@example.com')

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
