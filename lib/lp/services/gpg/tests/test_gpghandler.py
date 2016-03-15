# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import subprocess

import gpgme
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.services.gpg.interfaces import (
    GPGKeyDoesNotExistOnServer,
    GPGKeyTemporarilyNotFoundError,
    IGPGHandler,
    )
from lp.services.log.logger import BufferLogger
from lp.services.timeout import (
    get_default_timeout_function,
    set_default_timeout_function,
    )
from lp.testing import (
    ANONYMOUS,
    login,
    logout,
    TestCase,
    )
from lp.testing.gpgkeys import (
    import_secret_test_key,
    iter_test_key_emails,
    test_keyrings,
    test_pubkey_from_email,
    )
from lp.testing.keyserver import KeyServerTac
from lp.testing.layers import LaunchpadFunctionalLayer


class TestGPGHandler(TestCase):
    """Unit tests for the GPG handler."""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Get a gpghandler and login"""
        super(TestGPGHandler, self).setUp()
        login(ANONYMOUS)
        self.gpg_handler = getUtility(IGPGHandler)
        self.gpg_handler.resetLocalState()

    def tearDown(self):
        """Zero out the gpg database"""
        # XXX Stuart Bishop 2005-10-27:
        # This should be a zope test cleanup thing per SteveA.
        self.gpg_handler.resetLocalState()
        logout()
        super(TestGPGHandler, self).tearDown()

    def populateKeyring(self):
        for email in iter_test_key_emails():
            pubkey = test_pubkey_from_email(email)
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
        import_secret_test_key()
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
        self.assertEqual(len(list(test_keyrings())), 1)

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
            error_report = self.oopses[-1]
            self.assertEqual('TimeoutError', error_report['type'])
            self.assertEqual('timeout exceeded.', error_report['value'])
        finally:
            set_default_timeout_function(old_timeout_function)

    def test_uploadPublicKey_suppress_in_config(self):
        self.useFixture(KeyServerTac())
        logger = BufferLogger()
        self.pushConfig("gpghandler", upload_keys=False)
        self.populateKeyring()
        fingerprint = list(self.gpg_handler.localKeys())[0].fingerprint
        self.gpg_handler.uploadPublicKey(fingerprint, logger=logger)
        self.assertEqual(
            "INFO Not submitting key to keyserver "
            "(disabled in configuration).\n", logger.getLogBuffer())
        self.assertRaises(
            GPGKeyDoesNotExistOnServer,
            removeSecurityProxy(self.gpg_handler)._getPubKey, fingerprint)

    def test_signContent_uses_sha512_digests(self):
        secret_keys = [
            ("ppa-sample@canonical.com.sec", ""),       # 1024R
            ("ppa-sample-4096@canonical.com.sec", ""),  # 4096R
            ]
        for key_name, password in secret_keys:
            self.gpg_handler.resetLocalState()
            secret_key = import_secret_test_key(key_name)
            content = "abc\n"
            signed_content = self.gpg_handler.signContent(
                content, secret_key.fingerprint, password)
            signature = self.gpg_handler.getVerifiedSignature(signed_content)
            self.assertEqual(content, signature.plain_data)
            self.assertEqual(secret_key.fingerprint, signature.fingerprint)
            # pygpgme doesn't tell us the hash algorithm used for a verified
            # signature, so we have to do this by hand.  Sending --status-fd
            # output to stdout is a bit dodgy, but at least with --quiet
            # it's OK for test purposes and it simplifies subprocess
            # plumbing.
            with open(os.devnull, "w") as devnull:
                gpg_proc = subprocess.Popen(
                    ["gpg", "--quiet", "--status-fd", "1", "--verify"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=devnull, universal_newlines=True)
            status = gpg_proc.communicate(signed_content)[0].splitlines()
            validsig_prefix = "[GNUPG:] VALIDSIG "
            [validsig_line] = [
                line for line in status if line.startswith(validsig_prefix)]
            validsig_tokens = validsig_line[len(validsig_prefix):].split()
            self.assertEqual(gpgme.MD_SHA512, int(validsig_tokens[7]))
