# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
from canonical.functional import FunctionalTestCase
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.ftests import keys_for_tests 
from canonical.launchpad.interfaces import IGPGHandler
from canonical.launchpad.scripts.keyringtrustanalyser import *
from zope.component import getUtility
from pyme.constants import validity

test_fpr = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
foobar_fpr = '340CA3BB270E2716C9EE0B768E7EB7086C64A8C5'

class TestKeyringTrustAnalyser(FunctionalTestCase):
    def setUp(self):
        """Get a gpghandler and login"""
        FunctionalTestCase.setUp(self)
        login(ANONYMOUS)
        self.gpg_handler = getUtility(IGPGHandler)

    def tearDown(self):
        """Zero out the gpg database"""
        #FIXME RBC: this should be a zope test cleanup thing per SteveA.
        self.gpg_handler.reset_local_state()
        FunctionalTestCase.tearDown(self)

    def _addTrustedKeys(self):
        # Add trusted key with ULTIMATE validity.  This will mark UIDs as
        # valid with a single signature, which is appropriate with the
        # small amount of test data.
        filename = keys_for_tests.test_pubkey_file_from_email(
            'test@canonical.com')
        addTrustedKeyring(filename, validity.ULTIMATE)

    def _addUntrustedKeys(self):
        for ring in keys_for_tests.test_keyrings():
            addOtherKeyring(ring)

    def testAddTrustedKeyring(self):
        """Test addTrustedKeyring"""
        self._addTrustedKeys()

        # get key from keyring
        keys = [key for key in self.gpg_handler.local_keys()
               if key.fingerprint == test_fpr]
        self.assertEqual(len(keys), 1)
        key = keys[0]
        self.assertTrue('test@canonical.com' in key.emails)
        self.assertEqual(key.owner_trust, validity.ULTIMATE)

    def testAddOtherKeyring(self):
        """Test addOtherKeyring"""
        self._addUntrustedKeys()
        fingerprints = set(key.fingerprint
                           for key in self.gpg_handler.local_keys())
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
