# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
import canonical.base
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.ftests import login, ANONYMOUS, logout
from canonical.launchpad.ftests import keys_for_tests
from canonical.launchpad.interfaces import IGPGHandler
from zope.component import getUtility
import gpgme

class TestImportKeyRing(unittest.TestCase):
    """Tests for keyring imports"""
    layer = LaunchpadFunctionalLayer
    def setUp(self):
        """Get a gpghandler and login"""
        login(ANONYMOUS)
        self.gpg_handler = getUtility(IGPGHandler)

    def tearDown(self):
        """Zero out the gpg database"""
        # XXX Stuart Bishop 2005-10-27:
        # This should be a zope test cleanup thing per SteveA.
        self.gpg_handler.resetLocalState()
        logout()

    # This sequence might fit better as a doctest. Hmm.
    def testEmptyGetKeys(self):
        """The initial local key list should be empty."""
        self.assertEqual([], list(self.gpg_handler.localKeys()))

    def testPopulatedGetKeys(self):
        """Import our test keys and check they get imported."""
        self.testEmptyGetKeys()
        for email in keys_for_tests.iter_test_key_emails():
            pubkey = keys_for_tests.test_pubkey_from_email(email)
            self.gpg_handler.importPublicKey(pubkey)
        self.assertNotEqual([], list(self.gpg_handler.localKeys()))
        fingerprints = set(key.fingerprint
                           for key in self.gpg_handler.localKeys())
        self.assertTrue("340CA3BB270E2716C9EE0B768E7EB7086C64A8C5"
                        in fingerprints)
        self.assertTrue("A419AE861E88BC9E04B9C26FBA2B9389DFD20543"
                        in fingerprints)

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


