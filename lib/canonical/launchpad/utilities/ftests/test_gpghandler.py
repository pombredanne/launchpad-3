# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from calendar import timegm
from datetime import (
    datetime,
    timedelta,
    )
from math import floor
import os
from time import time

from pytz import UTC
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import (
    ANONYMOUS,
    keys_for_tests,
    login,
    logout,
    )
from canonical.launchpad.interfaces.gpghandler import (
    GPGKeyDoesNotExistOnServer,
    GPGKeyTemporarilyNotFoundError,
    IGPGHandler,
    )
from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
from canonical.lazr.timeout import (
    get_default_timeout_function,
    set_default_timeout_function,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCase
from lp.testing.keyserver import KeyServerTac


class TestImportKeyRing(TestCase):
    """Tests for keyring imports"""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Get a gpghandler and login"""
        super(TestImportKeyRing, self).setUp()
        login(ANONYMOUS)
        self.gpg_handler = getUtility(IGPGHandler)
        self.gpg_handler.resetLocalState()

    def tearDown(self):
        """Zero out the gpg database"""
        # XXX Stuart Bishop 2005-10-27:
        # This should be a zope test cleanup thing per SteveA.
        self.gpg_handler.resetLocalState()
        logout()
        super(TestImportKeyRing, self).tearDown()

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

    def testHomeDirectoryJob(self):
        """Does the job to touch the home work."""
        gpghandler = getUtility(IGPGHandler)
        naked_gpghandler = removeSecurityProxy(gpghandler)

        # Get a list of all the files in the home directory.
        files_to_check = [os.path.join(naked_gpghandler.home, f)
            for f in os.listdir(naked_gpghandler.home)]
        files_to_check.append(naked_gpghandler.home)
        self.assertTrue(len(files_to_check) > 1)

        # Set the last modified times to 12 hours ago
        nowless12 = (datetime.now(UTC) - timedelta(hours=12)).utctimetuple()
        lm_time = timegm(nowless12)
        for fname in files_to_check:
            os.utime(fname, (lm_time, lm_time))

        # Touch the files and re-check the last modified times have been
        # updated to "now".
        now = floor(time())
        gpghandler.touchConfigurationDirectory()
        for fname in files_to_check:
            self.assertTrue(now <= floor(os.path.getmtime(fname)))

    def test_retrieveKey_raises_GPGKeyDoesNotExistOnServer(self):
        # GPGHandler.retrieveKey() raises GPGKeyDoesNotExistOnServer
        # when called for a key that does not exist on the key server.
        self.useFixture(KeyServerTac())
        gpghandler = getUtility(IGPGHandler)
        self.assertRaises(
            GPGKeyDoesNotExistOnServer, gpghandler.retrieveKey,
            'non-existent-fp')

    def test_retrieveKey_raises_GPGKeyTemporarilyNotFoundError_for_timeout(
        self):
        # If the keyserver responds too slowly, GPGHandler.retrieveKey()
        # raises GPGKeyTemporarilyNotFoundError.
        self.useFixture(KeyServerTac())
        old_timeout_function = get_default_timeout_function()
        set_default_timeout_function(lambda: 0.01)
        try:
            gpghandler = getUtility(IGPGHandler)
            self.assertRaises(
                GPGKeyTemporarilyNotFoundError, gpghandler.retrieveKey,
                'non-existent-fp')
            # An OOPS report is generated for the timeout.
            error_utility = ErrorReportingUtility()
            error_report = error_utility.getLastOopsReport()
            self.assertEqual('TimeoutError', error_report.type)
            self.assertEqual('timeout exceeded.', error_report.value)
        finally:
            set_default_timeout_function(old_timeout_function)
