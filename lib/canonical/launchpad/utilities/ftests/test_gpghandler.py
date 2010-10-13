# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

import gpgme
from zope.component import getUtility

from canonical.launchpad.ftests import (
    ANONYMOUS,
    keys_for_tests,
    login,
    logout,
    )
from canonical.launchpad.interfaces.gpghandler import IGPGHandler
from canonical.testing.layers import LaunchpadFunctionalLayer


class TestImportKeyRing(unittest.TestCase):
    """Tests for keyring imports"""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Get a gpghandler and login"""
        login(ANONYMOUS)
        self.gpg_handler = getUtility(IGPGHandler)
        self.gpg_handler.resetLocalState()

    def tearDown(self):
        """Zero out the gpg database"""
        # XXX Stuart Bishop 2005-10-27:
        # This should be a zope test cleanup thing per SteveA.
        self.gpg_handler.resetLocalState()
        logout()

    def populateKeyring(self):
        for email in keys_for_tests.iter_test_key_emails():
            pubkey = keys_for_tests.test_pubkey_from_email(email)
            self.gpg_handler.importPublicKey(pubkey)

    # This sequence might fit better as a doctest. Hmm.
    def testEmptyGetKeys(self):
        """The initial local key list should be empty."""
        self.assertEqual([], list(self.gpg_handler.localKeys()))

    def testPopulatedGetKeys(self):
        """Import our test keys and check they get imported."""
        self.populateKeyring()

        self.assertNotEqual([], list(self.gpg_handler.localKeys()))
        fingerprints = set(key.fingerprint
                           for key in self.gpg_handler.localKeys())
        self.assertTrue("340CA3BB270E2716C9EE0B768E7EB7086C64A8C5"
                        in fingerprints)
        self.assertTrue("A419AE861E88BC9E04B9C26FBA2B9389DFD20543"
                        in fingerprints)

    def testFilteredGetKeys(self):
        """Check the filtered key lookup mechanism.

        Test filtering by fingerprint, key ID, UID restricted to public
        or secret keyrings.
        """
        self.populateKeyring()
        target_fpr = '340CA3BB270E2716C9EE0B768E7EB7086C64A8C5'

        # Finding a key by its fingerprint.
        filtered_keys = self.gpg_handler.localKeys(target_fpr)
        [key] = filtered_keys
        self.assertEqual(key.fingerprint, target_fpr)

        # Finding a key by its key ID.
        filtered_keys = self.gpg_handler.localKeys(target_fpr[-8:])
        [key] = filtered_keys
        self.assertEqual(key.fingerprint, target_fpr)

        # Multiple results when filtering by email.
        filtered_keys = self.gpg_handler.localKeys('foo.bar@canonical.com')

        filtered_fingerprints = [key.fingerprint for key in filtered_keys]
        self.assertTrue(target_fpr in filtered_fingerprints)
        self.assertTrue(
            'FD311613D941C6DE55737D310E3498675D147547'
            in filtered_fingerprints)

        # Secret keys only filter.
        self.assertEqual(
            list(self.gpg_handler.localKeys(secret=True)), [])

        # Import a secret key and look it up.
        keys_for_tests.import_secret_test_key()
        secret_target_fpr = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'

        filtered_keys = self.gpg_handler.localKeys(secret=True)
        [key] = filtered_keys
        self.assertEqual(key.fingerprint, secret_target_fpr)

        # Combining 'filter' and 'secret'.
        filtered_keys = self.gpg_handler.localKeys(
            filter=secret_target_fpr[-8:], secret=True)
        [key] = filtered_keys
        self.assertEqual(key.fingerprint, secret_target_fpr)

    def test_unicode_filter(self):
        """Using a unicode filter works also.

        XXX michaeln 2010-05-07 bug=576405
        Recent versions of gpgme return unicode fingerprints, but
        at the same time, gpgme.Context().keylist falls over if
        it receives a unicode string.
        """
        self.populateKeyring()

        target_fpr = u'340CA3BB270E2716C9EE0B768E7EB7086C64A8C5'

        # Finding a key by its unicode fingerprint.
        filtered_keys = self.gpg_handler.localKeys(target_fpr)
        [key] = filtered_keys
        self.assertEqual(key.fingerprint, target_fpr)

    def test_non_ascii_filter(self):
        """localKeys should not error if passed non-ascii unicode strings."""
        filtered_keys = self.gpg_handler.localKeys(u'non-ascii \u8463')
        self.failUnlessRaises(StopIteration, filtered_keys.next)

    def testTestkeyrings(self):
        """Do we have the expected test keyring files"""
        self.assertEqual(len(list(keys_for_tests.test_keyrings())), 1)

    def testImportKeyRing(self):
        """Import a sample keyring and check its contents are available."""
        self.testEmptyGetKeys()
        importedkeys = set()
        for ring in keys_for_tests.test_keyrings():
            keys = self.gpg_handler.importKeyringFile(ring)
            importedkeys.update(key.fingerprint for key in keys)

        # check that expected keys are in importedkeys set
        self.assertTrue("340CA3BB270E2716C9EE0B768E7EB7086C64A8C5"
                        in importedkeys)
        self.assertTrue("A419AE861E88BC9E04B9C26FBA2B9389DFD20543"
                        in importedkeys)

        # check that importedkeys are in key ring
        keyring = set(key.fingerprint
                      for key in self.gpg_handler.localKeys())
        self.assertNotEqual(len(keyring), 0)
        self.assertTrue(importedkeys.issubset(keyring))

    def testSetOwnerTrust(self):
        """Import a key and set the ownertrust."""
        self.testEmptyGetKeys()
        for email in keys_for_tests.iter_test_key_emails():
            pubkey = keys_for_tests.test_pubkey_from_email(email)
            self.gpg_handler.importPublicKey(pubkey)

        iterator = self.gpg_handler.localKeys()
        key = iterator.next()
        self.assertEqual(key.owner_trust, gpgme.VALIDITY_UNKNOWN)
        key.setOwnerTrust(gpgme.VALIDITY_FULL)
        self.assertEqual(key.owner_trust, gpgme.VALIDITY_FULL)
        other_iterator = self.gpg_handler.localKeys()
        other_key_instance = other_iterator.next()
        self.assertEqual(key.owner_trust, other_key_instance.owner_trust)

    def testCheckTrustDb(self):
        """Test IGPGHandler.checkTrustDb()"""
        self.testEmptyGetKeys()

        # check trust DB with no keys succeeds
        self.assertEqual(self.gpg_handler.checkTrustDb(), 0)

        # add some keys and check trust DB again
        for ring in keys_for_tests.test_keyrings():
            self.gpg_handler.importKeyringFile(ring)
        self.assertEqual(self.gpg_handler.checkTrustDb(), 0)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == "__main__":
    unittest.main(defaultTest=test_suite())


