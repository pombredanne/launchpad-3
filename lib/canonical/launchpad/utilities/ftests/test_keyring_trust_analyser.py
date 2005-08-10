# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
import canonical.base
from canonical.functional import FunctionalTestCase
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.ftests import keys_for_tests 
from canonical.launchpad.interfaces import IGPGHandler
from canonical.launchpad.utilities.keyring_trust_analyser import KeyRingTrustAnalyser
from zope.component import getUtility
from pyme.constants import validity

class TestImportKeyRing(FunctionalTestCase):
    """Tests for keyring imports"""

    def setUp(self):
        """Get a gpghandler and login"""
        FunctionalTestCase.setUp(self)
        login(ANONYMOUS)
        self.gpg_handler = getUtility(IGPGHandler)

    def tearDown(self):
        """Zero out the gpg database"""
        #FIXME RBC: this should be a zope test cleanup thing per SteveA.
        self.gpg_handler.reset_local_state()

    # This sequence might fit better as a doctest. Hmm.
    def testEmptyGetKeys(self):
        """The initial local key list should be empty."""
        self.assertEqual([], list(self.gpg_handler.local_keys()))

    def testPopulatedGetKeys(self):
        """Import our test keys and check they get imported."""
        self.testEmptyGetKeys()
        for email in keys_for_tests.iter_test_key_emails():
            pubkey = keys_for_tests.test_pubkey_from_email(email)
            self.gpg_handler.importKey(pubkey)
        self.assertNotEqual([], list(self.gpg_handler.local_keys()))
        iterator = self.gpg_handler.local_keys()
        self.assertEqual(iterator.next().fingerprint,
                         "A419AE861E88BC9E04B9C26FBA2B9389DFD20543")
        self.assertEqual(iterator.next().fingerprint, 
                         "340CA3BB270E2716C9EE0B768E7EB7086C64A8C5")

    def testTestkeyrings(self):
        """Do we have the expected test keyring files"""
        self.assertEqual(len(list(keys_for_tests.test_keyrings())), 1)

    def testImportKeyRing(self):
        """Import a sample keyring and check its contents are available."""
        self.testEmptyGetKeys()
        for ring in keys_for_tests.test_keyrings():
            keys = self.gpg_handler.importKeyringFile(ring)
            
        self.assertNotEqual([], list(self.gpg_handler.local_keys()))
        iterator = iter(keys)
        self.assertEqual (iterator.next().fingerprint, 
                          "340CA3BB270E2716C9EE0B768E7EB7086C64A8C5")
        self.assertEqual (iterator.next().fingerprint,
                          "A419AE861E88BC9E04B9C26FBA2B9389DFD20543")

    def testSetOwnertrust(self):
        """Import a key and set the ownertrust."""
        self.testEmptyGetKeys()
        for email in keys_for_tests.iter_test_key_emails():
            pubkey = keys_for_tests.test_pubkey_from_email(email)
            self.gpg_handler.importKey(pubkey)

        iterator = self.gpg_handler.local_keys()
        key = iterator.next()
        self.assertEqual(key.owner_trust, validity.UNKNOWN)
        key.owner_trust = validity.FULL
        self.assertEqual(key.owner_trust, validity.FULL)
        other_iterator = self.gpg_handler.local_keys()
        other_key_instance = other_iterator.next()
        self.assertEqual(key.owner_trust, other_key_instance.owner_trust)

# this is what we want to end up with.
# result = []
# handler=getUtility (IGPGHandler)
# ubuntu = handler.import_key_ring (path_to_ubuntu_keyring)
# debian = handler.import_key_ring (path_to_debian_keyring)
# for key in ubuntu:
#   key.set_ownertrust (GPGME_VALIDITY_MARGINAL)
# for key in debian:
#   key.set_ownertrust (GPGME_VALIDITY_MARGINAL)
# scc = handler.import_key_ring (path_to_scc)
# for key in scc:
#   uid = key.uids
#   while uid is not None:
#     if validity > GPGME_VALIDITY_MARGINAL:
#       result.append ((key, uid->email))

def test_suite():
    loader=unittest.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

if __name__ == "__main__":
    unittest.main(defaultTest=test_suite())


