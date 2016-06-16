# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import base64
import json
import os
import random
import string
import subprocess

import gpgme
from lazr.restful.utils import get_current_browser_request
from testtools.matchers import (
    ContainsDict,
    Equals,
    HasLength,
    raises,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.registry.interfaces.gpg import IGPGKeySet
from lp.registry.interfaces.person import IPersonSet
from lp.services.database.constants import THIRTY_DAYS_AGO
from lp.services.database.interfaces import IMasterStore
from lp.services.features.testing import FeatureFixture
from lp.services.gpg.interfaces import (
    GPGKeyDoesNotExistOnServer,
    GPGKeyTemporarilyNotFoundError,
    GPGServiceException,
    IGPGClient,
    IGPGHandler,
    )
from lp.services.log.logger import BufferLogger
from lp.services.openid.model.openididentifier import OpenIdIdentifier
from lp.services.timeline.requesttimeline import get_request_timeline
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
from lp.testing.keyserver import KeyServerTac
from lp.testing.layers import (
    GPGServiceLayer,
    LaunchpadFunctionalLayer,
    ZopelessDatabaseLayer,
    )


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
                content, secret_key, password)
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
        person = getUtility(IPersonSet).getByName('name16')
        openid_id = getUtility(IGPGKeySet).getOwnerIdForPerson(person)
        data = client.getKeysForOwner(openid_id)
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
            lambda: client.addKeyForOwner(
                self.get_random_owner_id_string(), ''),
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
            raises(GPGServiceException(
                "Error: Fingerprint already in database.")))

    def test_disabling_active_key(self):
        self.useFixture(KeyServerTac())
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
        self.useFixture(KeyServerTac())
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
            lambda: client.disableKeyForOwner(
                self.get_random_owner_id_string(), ''),
            raises(ValueError("Invalid fingerprint: ''."))
        )

    def test_can_get_key_by_fingerprint(self):
        self.useFixture(KeyServerTac())
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
        self.useFixture(
            FeatureFixture({'gpg.write_to_gpgservice': True}))
        client = getUtility(IGPGClient)
        person = self.factory.makePerson()
        # With the feature flag enabled, the following creates a
        # gpg key on the gpgservice.
        gpgkey = self.factory.makeGPGKey(person)
        user = getUtility(IGPGKeySet).getOwnerIdForPerson(person)
        key = client.getKeyByFingerprint(gpgkey.fingerprint)
        self.assertThat(
            key, ContainsDict({'owner': Equals(user),
                               'fingerprint': Equals(gpgkey.fingerprint)}))

    def makePersonWithMultipleGPGKeysInDifferentOpenids(self):
        """Make a person with multiple GPG keys owned by
        different openid identifiers. This happens as a result
        of an account merge.

        :returns: an IPerson instance with two keys under
                  different openid identifiers.
        """
        person = self.factory.makePerson()
        self.factory.makeGPGKey(person)
        # Create a second openid identifier from 30 days ago.
        # This simulates the account merge:
        identifier = OpenIdIdentifier()
        identifier.account = person.account
        identifier.identifier = u'openid_identifier'
        identifier.date_created = THIRTY_DAYS_AGO
        IMasterStore(OpenIdIdentifier).add(identifier)
        self.factory.makeGPGKey(person)
        return person

    def test_can_retrieve_keys_for_all_openid_identifiers(self):
        person = self.makePersonWithMultipleGPGKeysInDifferentOpenids()
        keys = getUtility(IGPGKeySet).getGPGKeysForPerson(person)
        self.assertThat(keys, HasLength(2))

    def test_can_deactivate_all_keys_with_multiple_openid_identifiers(self):
        person = self.makePersonWithMultipleGPGKeysInDifferentOpenids()
        keyset = getUtility(IGPGKeySet)
        key_one, key_two = keyset.getGPGKeysForPerson(person)
        keyset.deactivate(key_one)
        keyset.deactivate(key_two)
        key_one, key_two = keyset.getGPGKeysForPerson(person, active=False)

        self.assertFalse(key_one.active)
        self.assertFalse(key_two.active)

    def test_can_reactivate_all_keys_with_multiple_openid_identifiers(self):
        person = self.makePersonWithMultipleGPGKeysInDifferentOpenids()
        keyset = getUtility(IGPGKeySet)
        for k in keyset.getGPGKeysForPerson(person):
            keyset.deactivate(k)
        for k in keyset.getGPGKeysForPerson(person, active=False):
            keyset.activate(person, k, k.can_encrypt)
        key_one, key_two = keyset.getGPGKeysForPerson(person)

        self.assertTrue(key_one.active)
        self.assertTrue(key_two.active)

    def test_cannot_reactivate_someone_elses_key(self):
        person1 = self.factory.makePerson()
        key = self.factory.makeGPGKey(person1)
        person2 = self.factory.makePerson()

        keyset = getUtility(IGPGKeySet)
        keyset.deactivate(key)
        self.assertRaises(
            AssertionError,
            keyset.activate,
            person2, key, key.can_encrypt
        )

    def assert_last_timeline_action(self, expected_method, expected_url):
        timeline = get_request_timeline(get_current_browser_request())
        action = timeline.actions[-1]
        self.assertEqual("gpgservice-%s" % expected_method, action.category)
        self.assertEqual(expected_url, action.detail.split(" ", 1)[0])

    def test_get_keys_for_owner_has_timeline_support(self):
        client = getUtility(IGPGClient)
        user = self.get_random_owner_id_string()
        client.getKeysForOwner(user)

        self.assert_last_timeline_action(
            'GET', construct_url("/users/{owner_id}/keys", user))

    def test_add_key_for_owner_has_timeline_support(self):
        self.useFixture(KeyServerTac())
        client = getUtility(IGPGClient)
        user = self.get_random_owner_id_string()
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        client.addKeyForOwner(user, fingerprint)

        self.assert_last_timeline_action(
            'POST', construct_url("/users/{owner_id}/keys", user))

    def test_disable_key_for_owner_has_timeline_support(self):
        self.useFixture(KeyServerTac())
        client = getUtility(IGPGClient)
        user = self.get_random_owner_id_string()
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        client.addKeyForOwner(user, fingerprint)
        client.disableKeyForOwner(user, fingerprint)

        self.assert_last_timeline_action(
            'DELETE',
            construct_url(
                "/users/{owner_id}/keys/{fingerprint}", user, fingerprint))

    def test_get_key_by_fingerprint_has_timeline_support(self):
        client = getUtility(IGPGClient)
        fingerprint = 'A419AE861E88BC9E04B9C26FBA2B9389DFD20543'
        client.getKeyByFingerprint(fingerprint)

        self.assert_last_timeline_action(
            'GET',
            construct_url("/keys/{fingerprint}", fingerprint=fingerprint))

    def test_get_keys_by_fingerprints_has_timeline_support(self):
        client = getUtility(IGPGClient)
        fingerprints = [
            'A419AE861E88BC9E04B9C26FBA2B9389DFD20543',
            'B439AF863EDEFC9E04FAB26FBA2B7289DF324545',
        ]
        client.getKeysByFingerprints(fingerprints)

        self.assert_last_timeline_action(
            'GET',
            construct_url(
                "/keys/{fingerprint}", fingerprint=','.join(fingerprints)))

    def test_timeline_support_filters_unknown_headers(self):
        client = removeSecurityProxy(getUtility(IGPGClient))
        client._request(
            'get', '/', headers={'X-Foo': 'bar', 'Content-Type': 'baz'})

        expected_headers = {'Content-Type': 'baz'}
        timeline = get_request_timeline(get_current_browser_request())
        action = timeline.actions[-1]
        self.assertEqual(
            '/ no body ' + json.dumps(expected_headers),
            action.detail
        )


def construct_url(template, owner_id='', fingerprint=''):
    owner_id = base64.b64encode(owner_id, altchars='-_')
    return template.format(owner_id=owner_id, fingerprint=fingerprint)
