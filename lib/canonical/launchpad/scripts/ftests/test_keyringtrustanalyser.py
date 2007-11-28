# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
import logging

from canonical.launchpad.ftests import keys_for_tests
from canonical.launchpad.ftests.harness import (
        LaunchpadZopelessTestCase, LaunchpadFunctionalTestCase
        )
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.interfaces import (
    IGPGHandler, IPersonSet, IEmailAddressSet, EmailAddressStatus)
from canonical.launchpad.scripts.keyringtrustanalyser import *
from zope.component import getUtility
import gpgme

test_fpr = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
foobar_fpr = '340CA3BB270E2716C9EE0B768E7EB7086C64A8C5'


class LogCollector(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.records = []
    def emit(self, record):
        self.records.append(self.format(record))


def setupLogger(name='test_keyringtrustanalyser'):
    """Set up the named logger to collect log messages.

    Returns (logger, handler)
    """
    logger = logging.getLogger(name)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.flush()
        handler.close()
    handler = LogCollector()
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger.addHandler(handler)
    return logger, handler


class TestKeyringTrustAnalyser(LaunchpadFunctionalTestCase):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)
        self.login()
        self.gpg_handler = getUtility(IGPGHandler)

    def tearDown(self):
        # XXX stub 2005-10-27: this should be a zope test cleanup
        # thing per SteveA.
        self.gpg_handler.resetLocalState()
        LaunchpadFunctionalTestCase.tearDown(self)

    def _addTrustedKeys(self):
        # Add trusted key with ULTIMATE validity.  This will mark UIDs as
        # valid with a single signature, which is appropriate with the
        # small amount of test data.
        filename = keys_for_tests.test_pubkey_file_from_email(
            'test@canonical.com')
        addTrustedKeyring(filename, gpgme.VALIDITY_ULTIMATE)

    def _addUntrustedKeys(self):
        for ring in keys_for_tests.test_keyrings():
            addOtherKeyring(ring)

    def testAddTrustedKeyring(self):
        """Test addTrustedKeyring"""
        self._addTrustedKeys()

        # get key from keyring
        keys = [key for key in self.gpg_handler.localKeys()
               if key.fingerprint == test_fpr]
        self.assertEqual(len(keys), 1)
        key = keys[0]
        self.assertTrue('test@canonical.com' in key.emails)
        self.assertEqual(key.owner_trust, gpgme.VALIDITY_ULTIMATE)

    def testAddOtherKeyring(self):
        """Test addOtherKeyring"""
        self._addUntrustedKeys()
        fingerprints = set(key.fingerprint
                           for key in self.gpg_handler.localKeys())
        self.assertTrue(test_fpr in fingerprints)
        self.assertTrue(foobar_fpr in fingerprints)

    def testGetValidUids(self):
        """Test getValidUids"""
        self._addTrustedKeys()
        self._addUntrustedKeys()

        # calculate valid UIDs
        validuids = list(getValidUids())

        # test@canonical.com's non-revoked UIDs are valid
        self.assertTrue((test_fpr, 'test@canonical.com') in validuids)
        self.assertTrue((test_fpr, 'sample.person@canonical.com') in validuids)
        self.assertTrue((test_fpr, 'sample.revoked@canonical.com')
                        not in validuids)

        # foo.bar@canonical.com's non-revoked signed UIDs are valid
        self.assertTrue((foobar_fpr, 'foo.bar@canonical.com') in validuids)
        self.assertTrue((foobar_fpr, 'revoked@canonical.com') not in validuids)
        self.assertTrue((foobar_fpr, 'untrusted@canonical.com')
                        not in validuids)

    def testFindEmailClusters(self):
        """Test findEmailClusters"""
        self._addTrustedKeys()
        self._addUntrustedKeys()

        clusters = list(findEmailClusters())

        # test@canonical.com is ultimately trusted, so its non-revoked keys
        # form a cluster
        self.assertTrue(set(['test@canonical.com',
                             'sample.person@canonical.com']) in clusters)

        # foobar has only one signed, non-revoked key
        self.assertTrue(set(['foo.bar@canonical.com']) in clusters)


class TestMergeClusters(LaunchpadZopelessTestCase):
    """Tests of the mergeClusters() routine."""

    def _getEmails(self, person):
        emailset = getUtility(IEmailAddressSet)
        return set(address.email for address in emailset.getByPerson(person))

    def testNullMerge(self):
        """Test that a merge with an empty sequence of clusters works"""
        mergeClusters([])

    def testMergeOneAccountNoNewEmails(self):
        """Test that merging a single email address does not affect an
        account.
        """
        person = getUtility(IPersonSet).getByEmail('test@canonical.com')
        emails = self._getEmails(person)
        self.assertTrue('test@canonical.com' in emails)
        self.assertEqual(person.merged, None)

        mergeClusters([set(['test@canonical.com'])])
        self.assertEqual(person.merged, None)
        self.assertEqual(self._getEmails(person), emails)

    def testMergeOneAccountAddEmails(self):
        """Test that merging a cluster containing new email addresses adds
        those emails.
        """
        personset = getUtility(IPersonSet)
        emailset = getUtility(IEmailAddressSet)

        person = personset.getByEmail('test@canonical.com')
        self.assertEqual(person.merged, None)
        # make sure newemail doesn't exist
        self.assertEqual(personset.getByEmail('newemail@canonical.com'), None)

        mergeClusters([set(['test@canonical.com', 'newemail@canonical.com'])])
        self.assertEqual(person.merged, None)
        emails = self._getEmails(person)

        # both email addresses associated with account ...
        self.assertTrue('test@canonical.com' in emails)
        self.assertTrue('newemail@canonical.com' in emails)

        address = emailset.getByEmail('newemail@canonical.com')
        self.assertEqual(address.email, 'newemail@canonical.com')
        self.assertEqual(address.person, person)
        self.assertEqual(address.status, EmailAddressStatus.NEW)

    def testMergeUnvalidatedAccountWithValidated(self):
        """Test merging an unvalidated account with a validated account."""
        personset = getUtility(IPersonSet)

        validated_person = personset.getByEmail('test@canonical.com')
        unvalidated_person = personset.getByEmail(
            'christian.reis@ubuntulinux.com')

        allemails = self._getEmails(validated_person)
        allemails.update(self._getEmails(unvalidated_person))

        self.assertNotEqual(validated_person, unvalidated_person)

        self.assertNotEqual(validated_person.preferredemail, None)
        self.assertEqual(unvalidated_person.preferredemail, None)

        self.assertEqual(validated_person.merged, None)
        self.assertEqual(unvalidated_person.merged, None)

        mergeClusters([set(['test@canonical.com',
                            'christian.reis@ubuntulinux.com'])])

        # unvalidated person has been merged into the validated person
        self.assertEqual(validated_person.merged, None)
        self.assertEqual(unvalidated_person.merged, validated_person)

        # all email addresses are now associated with the valid person
        self.assertEqual(self._getEmails(validated_person), allemails)
        self.assertEqual(self._getEmails(unvalidated_person), set())

    def testMergeTwoValidatedAccounts(self):
        """Test merging of two validated accounts.  This should do
        nothing, since both accounts are in use.
        """
        personset = getUtility(IPersonSet)

        person1 = personset.getByEmail('test@canonical.com')
        person2 = personset.getByEmail('foo.bar@canonical.com')
        self.assertNotEqual(person1, person2)

        self.assertNotEqual(person1.preferredemail, None)
        self.assertNotEqual(person2.preferredemail, None)

        self.assertEqual(person1.merged, None)
        self.assertEqual(person2.merged, None)

        logger, collector = setupLogger()
        mergeClusters([set(['test@canonical.com', 'foo.bar@canonical.com'])],
                      logger=logger)

        self.assertEqual(person1.merged, None)
        self.assertEqual(person2.merged, None)

        messages = collector.records
        self.assertNotEqual(messages, [])
        self.assertTrue(messages[0].startswith('WARNING:Multiple validated '
                                               'user accounts'))

    def testMergeTwoUnvalidatedAccounts(self):
        """Test merging of two unvalidated accounts.  This will pick
        one account and merge the others into it (since none of the
        accounts have been used, there is no need to favour one over
        the other).
        """
        personset = getUtility(IPersonSet)

        person1 = personset.getByEmail('christian.reis@ubuntulinux.com')
        person2 = personset.getByEmail('martin.pitt@canonical.com')

        allemails = self._getEmails(person1)
        allemails.update(self._getEmails(person2))

        self.assertEqual(person1.preferredemail, None)
        self.assertEqual(person2.preferredemail, None)

        self.assertEqual(person1.merged, None)
        self.assertEqual(person2.merged, None)

        mergeClusters([set(['christian.reis@ubuntulinux.com',
                            'martin.pitt@canonical.com'])])

        # since we don't know which account will be merged, swap
        # person1 and person2 if person1 was merged into person2.
        if person1.merged is not None:
            person1, person2 = person2, person1

        # one account is merged into the other
        self.assertEqual(person1.merged, None)
        self.assertEqual(person2.merged, person1)

        self.assertEqual(self._getEmails(person1), allemails)
        self.assertEqual(self._getEmails(person2), set())

    def testMergeUnknownEmail(self):
        """Merging a cluster of unknown emails creates an account."""
        personset = getUtility(IPersonSet)

        self.assertEqual(personset.getByEmail('newemail@canonical.com'), None)

        mergeClusters([set(['newemail@canonical.com'])])

        person = personset.getByEmail('newemail@canonical.com')
        self.assertNotEqual(person, None)
        self.assertEqual(person.preferredemail, None)
        self.assertTrue('newemail@canonical.com' in self._getEmails(person))


def test_suite():
    loader=unittest.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

if __name__ == "__main__":
    unittest.main(defaultTest=test_suite())
