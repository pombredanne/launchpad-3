# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import random
import string

from testtools.matchers import (
    Contains,
    ContainsDict,
    Equals,
    HasLength,
    Not,
    raises,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.services.config.fixture import (
    ConfigFixture,
    ConfigUseFixture,
    )
from lp.services.gpg.handler import GPGClient
from lp.services.gpg.interfaces import (
    GPGKeyAlgorithm,
    GPGKeyDoesNotExistOnServer,
    GPGKeyTemporarilyNotFoundError,
    GPGServiceException,
    IGPGClient,
    IGPGHandler,
    )
from lp.services.log.logger import BufferLogger
from lp.services.openid.model.openididentifier import OpenIdIdentifier
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
from lp.testing.factory import BareLaunchpadObjectFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.gpgkeys import (
    import_secret_test_key,
    iter_test_key_emails,
    test_keyrings,
    test_pubkey_from_email,
    )
from lp.testing.gpgservice import GPGKeyServiceFixture
from lp.testing.keyserver import KeyServerTac
from lp.testing.layers import (
    GPGServiceLayer,
    LaunchpadFunctionalLayer,
    ZopelessDatabaseLayer,
    )


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


class GPGServiceZopelessLayer(ZopelessDatabaseLayer, GPGServiceLayer):
    """A layer specifically for running the IGPGClient utility tests."""

    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass


class GPGClientTests(TestCase):

    layer = GPGServiceZopelessLayer

    def setUp(self):
        super(GPGClientTests, self).setUp()
        self.factory = BareLaunchpadObjectFactory()

    def test_can_get_utility(self):
        client = getUtility(IGPGClient)
        self.assertIsNot(None, client)

    def get_random_owner_id_string(self):
        """Get a random string that's representative of the owner id scheme."""
        candidates = string.ascii_lowercase + string.digits
        openid_id = ''.join((random.choice(candidates) for i in range(6)))
        return 'http://testopenid.dev/+id/' + openid_id

    def test_get_key_for_user_with_sampledata(self):
        client = getUtility(IGPGClient)
        data = client.getKeysForOwner('name16_oid')
        self.assertThat(data, ContainsDict({'keys': HasLength(1)}))

    def test_get_key_for_unknown_user(self):
        client = getUtility(IGPGClient)
        user = self.get_random_owner_id_string()
        data = client.getKeysForOwner(user)
        self.assertThat(data, ContainsDict({'keys': HasLength(0)}))

    def test_register_non_callable_raises_TypeError(self):
        client = getUtility(IGPGClient)
        self.assertThat(
            lambda: client.registerWriteHook("not a callable"),
            raises(TypeError))

    def test_unregister_with_unregistered_hook_raises_ValueError(self):
        client = getUtility(IGPGClient)
        self.assertThat(
            lambda: client.unregisterWriteHook("not registered"),
            raises(ValueError))

    def test_can_unregister_registered_write_hook(self):
        client = getUtility(IGPGClient)
        hook = FakeMethod()
        client.registerWriteHook(hook)
        client.unregisterWriteHook(hook)

        self.assertThat(
            lambda: client.unregisterWriteHook(hook),
            raises(ValueError))

    def test_can_add_new_fingerprint_for_user(self):
        self.useFixture(KeyServerTac())
        client = getUtility(IGPGClient)
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        user = self.get_random_owner_id_string()
        client.addKeyForOwner(user, fingerprint)
        data = client.getKeysForOwner(user)
        self.assertThat(data, ContainsDict({'keys': HasLength(1)}))
        keys = data['keys']
        self.assertThat(
            keys[0],
            ContainsDict({
                'fingerprint': Equals(fingerprint),
                'enabled': Equals(True)
            }))

    def test_adding_fingerprint_notifies_writes(self):
        self.useFixture(KeyServerTac())
        client = getUtility(IGPGClient)
        hook = FakeMethod()
        client.registerWriteHook(hook)
        self.addCleanup(client.unregisterWriteHook, hook)
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        user = self.get_random_owner_id_string()
        client.addKeyForOwner(user, fingerprint)

        self.assertThat(hook.call_count, Equals(1))

    def test_adding_invalid_fingerprint_raises_ValueError(self):
        client = getUtility(IGPGClient)
        self.assertThat(
            lambda: client.addKeyForOwner(self.get_random_owner_id_string(), ''),
            raises(ValueError("Invalid fingerprint: ''.")))

    def test_adding_duplicate_fingerprint_raises_GPGServiceException(self):
        self.useFixture(KeyServerTac())
        client = getUtility(IGPGClient)
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        user_one = self.get_random_owner_id_string()
        user_two = self.get_random_owner_id_string()
        client.addKeyForOwner(user_one, fingerprint)
        self.assertThat(
            lambda: client.addKeyForOwner(user_two, fingerprint),
            raises(GPGServiceException("Error: Fingerprint already in database.")))

    def test_disabling_active_key(self):
        client = getUtility(IGPGClient)
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        user = self.get_random_owner_id_string()
        client.addKeyForOwner(user, fingerprint)
        client.disableKeyForOwner(user, fingerprint)
        data = client.getKeysForOwner(user)

        self.assertThat(data, ContainsDict({'keys': HasLength(1)}))
        keys = data['keys']
        self.assertThat(keys[0], ContainsDict({'enabled': Equals(False)}))

    def test_disabling_key_notifies_writes(self):
        client = getUtility(IGPGClient)
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        user = self.get_random_owner_id_string()
        client.addKeyForOwner(user, fingerprint)

        hook = FakeMethod()
        client.registerWriteHook(hook)
        self.addCleanup(client.unregisterWriteHook, hook)
        client.disableKeyForOwner(user, fingerprint)
        self.assertThat(hook.call_count, Equals(1))

    def test_disabling_invalid_fingerprint_raises_ValueError(self):
        client = getUtility(IGPGClient)
        self.assertThat(
            lambda: client.disableKeyForOwner(self.get_random_owner_id_string(), ''),
            raises(ValueError("Invalid fingerprint: ''."))
        )

    def test_can_get_key_by_fingerprint(self):
        client = getUtility(IGPGClient)
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        user = self.get_random_owner_id_string()
        client.addKeyForOwner(user, fingerprint)

        key = client.getKeyByFingerprint(fingerprint)
        self.assertThat(
            key, ContainsDict({'owner': Equals(user),
                               'fingerprint': Equals(fingerprint)}))

    def test_get_missing_key_by_fingerprint(self):
        client = getUtility(IGPGClient)
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        self.assertIsNone(client.getKeyByFingerprint(fingerprint))

    def test_get_key_with_bad_fingerprint_raises_ValueError(self):
        client = getUtility(IGPGClient)
        self.assertThat(lambda: client.getKeyByFingerprint('bad fingerprint'),
                        raises(ValueError))

    def test_can_add_IGPGKey_to_test_enabled_gpgservice(self):
        client = getUtility(IGPGClient)
        person = self.factory.makePerson()
        gpgkey = self.factory.makeGPGKey(person)
        user = self.get_random_owner_id_string()
        client.addKeyForTest(user, gpgkey)

        key = client.getKeyByFingerprint(gpgkey.fingerprint)
        self.assertThat(
            key, ContainsDict({'owner': Equals(user),
                               'fingerprint': Equals(gpgkey.fingerprint)}))

    def test_can_get_openid_identifier(self):
        client = getUtility(IGPGClient)
        keyset = getUtility(IGPGKeySet)
        person = self.factory.makePerson()
        gpgkey = self.factory.makeGPGKey(person)
        identifier = keyset.getOwnerIdForKey(gpgkey)
        expected = person.account.openid_identifiers.order_by(
            OpenIdIdentifier.identifier).first().identifier
        self.assertEqual(expected, identifier)
