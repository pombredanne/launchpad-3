# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for GPG key on the web."""

__metaclass__ = type

from testtools.matchers import (
    Equals,
    HasLength,
    Not,
    Raises,
    raises,
    )
from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.gpg import IGPGKeySet
from lp.services.features.testing import FeatureFixture
from lp.services.gpg.interfaces import (
    GPG_DATABASE_READONLY_FEATURE_FLAG,
    GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG,
    GPGKeyAlgorithm,
    GPGReadOnly,
    )
from lp.services.webapp import canonical_url
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.views import create_initialized_view


class TestCanonicalUrl(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_canonical_url(self):
        # The canonical URL of a GPG key is ???
        person = self.factory.makePerson()
        gpgkey = self.factory.makeGPGKey(person)
        self.assertEqual(
            '%s/+gpg-keys/%s' % (
                canonical_url(person, rootsite='api'), gpgkey.keyid),
            canonical_url(gpgkey))


class TestPersonGPGView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_edit_pgp_keys_login_redirect(self):
        """+editpgpkeys should redirect to force you to re-authenticate."""
        person = self.factory.makePerson()
        login_person(person)
        view = create_initialized_view(person, "+editpgpkeys")
        response = view.request.response
        self.assertEqual(302, response.getStatus())
        expected_url = (
            '%s/+editpgpkeys/+login?reauth=1' % canonical_url(person))
        self.assertEqual(expected_url, response.getHeader('location'))

    def test_gpgkeys_POST_readonly_with_feature_flag_set(self):
        self.useFixture(FeatureFixture({
            GPG_DATABASE_READONLY_FEATURE_FLAG: True,
        }))
        person = self.factory.makePerson()
        login_person(person)
        view = create_initialized_view(person, "+editpgpkeys", principal=person,
                                       method='POST', have_fresh_login=True)
        self.assertThat(view.render, raises(GPGReadOnly))

    def test_gpgkeys_GET_readonly_with_feature_flag_set(self):
        self.useFixture(FeatureFixture({
            GPG_DATABASE_READONLY_FEATURE_FLAG: True,
        }))
        person = self.factory.makePerson()
        login_person(person)
        view = create_initialized_view(person, "+editpgpkeys", principal=person,
                                       method='GET', have_fresh_login=True)
        self.assertThat(view.render, Not(Raises()))


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
