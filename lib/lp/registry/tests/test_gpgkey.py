# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for GPG key on the web."""

__metaclass__ = type

from testtools.matchers import (
    Contains,
    Equals,
    HasLength,
    StartsWith,
    )
from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.gpg import IGPGKeySet
from lp.services.config.fixture import (
    ConfigFixture,
    ConfigUseFixture,
    )
from lp.services.features.testing import FeatureFixture
from lp.services.gpg.interfaces import (
    GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG,
    GPG_WRITE_TO_GPGSERVICE_FEATURE_FLAG,
    GPGKeyAlgorithm,
    )
from lp.services.verification.interfaces.authtoken import LoginTokenType
from lp.services.verification.interfaces.logintoken import ILoginTokenSet
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadFunctionalLayer


class GPGKeySetTests(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_can_add_keys_for_test(self):
        # IGPGKeySet.new _only_ writes to the launchpad database, so this test
        # only works if the read_from_gpgservice FF is *not* set. Once this is
        # the default codepath this test should be deleted.
        self.useFixture(FeatureFixture({
            GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG: None,
        }))
        keyset = getUtility(IGPGKeySet)
        person = self.factory.makePerson()
        fingerprint = "DEADBEEF12345678DEADBEEF12345678DEADBEEF"
        keyset.new(person.id, "F0A432C2", fingerprint, 4096,
                   GPGKeyAlgorithm.R, True, True)

        keys = keyset.getGPGKeysForPerson(person)

        self.assertThat(keys, HasLength(1))
        self.assertThat(keys[0].fingerprint, Equals(fingerprint))

    def test_sampledata_contains_gpgkeys(self):
        keyset = getUtility(IGPGKeySet)
        personset = getUtility(IPersonSet)
        foobar = personset.getByName('name16')
        keys = keyset.getGPGKeysForPerson(foobar)

        self.assertThat(keys, HasLength(1))
        self.assertThat(keys[0].keyid, Equals('12345678'))
        self.assertThat(keys[0].fingerprint,
                        Equals('ABCDEF0123456789ABCDDCBA0000111112345678'))

    def test_can_retrieve_keys_by_fingerprint(self):
        keyset = getUtility(IGPGKeySet)
        person = self.factory.makePerson()
        key = self.factory.makeGPGKey(person)

        retrieved_key = keyset.getByFingerprint(key.fingerprint)

        self.assertThat(retrieved_key.owner.name, Equals(person.name))
        self.assertThat(retrieved_key.fingerprint, Equals(key.fingerprint))

    def test_getGPGKeysForPerson_retrieves_active_keys(self):
        keyset = getUtility(IGPGKeySet)
        person = self.factory.makePerson()
        key = self.factory.makeGPGKey(person)

        keys = keyset.getGPGKeysForPerson(person)

        self.assertThat(keys, HasLength(1))
        self.assertThat(keys, Contains(key))

    def test_getGPGKeysForPerson_retrieves_inactive_keys(self):
        keyset = getUtility(IGPGKeySet)
        person = self.factory.makePerson()
        key = self.factory.makeGPGKey(person)
        keyset.deactivate(key)

        active_keys = keyset.getGPGKeysForPerson(person)
        inactive_keys = keyset.getGPGKeysForPerson(person, active=False)

        self.assertThat(active_keys, HasLength(0))
        self.assertThat(inactive_keys, HasLength(1))
        self.assertThat(inactive_keys, Contains(key))

    def test_getGPGKeysForPerson_excludes_keys_with_logintoken(self):
        keyset = getUtility(IGPGKeySet)
        email = 'foo@bar.com'
        person = self.factory.makePerson(email)
        key = self.factory.makeGPGKey(person)
        keyset.deactivate(key)
        getUtility(ILoginTokenSet).new(
            person, email, email, LoginTokenType.VALIDATEGPG, key.fingerprint)

        inactive_keys = keyset.getGPGKeysForPerson(person, active=False)
        self.assertThat(inactive_keys, HasLength(0))

    def set_config_parameters(self, **kwargs):
        config_name = self.getUniqueString()
        config_fixture = self.useFixture(
            ConfigFixture(
                config_name,
                LaunchpadFunctionalLayer.config_fixture.instance_name))
        setting_lines = ['[launchpad]'] + \
            ['%s: %s' % (k, v) for k, v in kwargs.items()]
        config_fixture.add_section('\n'.join(setting_lines))
        self.useFixture(ConfigUseFixture(config_name))

    def test_getOwnerIdForPerson_uses_canonical_url(self):
        keyset = getUtility(IGPGKeySet)
        email = 'foo@bar.com'
        person = self.factory.makePerson(email)
        openid_canonical_root = self.getUniqueString()
        self.set_config_parameters(openid_canonical_root=openid_canonical_root)

        self.assertThat(
            keyset.getOwnerIdForPerson(person),
            StartsWith(openid_canonical_root))

    def test_getAllOwnerIdsForPerson_uses_canonical_url(self):
        keyset = getUtility(IGPGKeySet)
        email = 'foo@bar.com'
        person = self.factory.makePerson(email)
        openid_canonical_root = self.getUniqueString()
        self.set_config_parameters(openid_canonical_root=openid_canonical_root)

        for id in keyset.getAllOwnerIdsForPerson(person):
            self.assertThat(id, StartsWith(openid_canonical_root))


class GPGKeySetWithGPGServiceTests(GPGKeySetTests):

    """A copy of GPGKeySetTests, but with gpgservice used."""

    def setUp(self):
        super(GPGKeySetWithGPGServiceTests, self).setUp()
        self.useFixture(FeatureFixture({
            GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG: True,
            GPG_WRITE_TO_GPGSERVICE_FEATURE_FLAG: True,
        }))
