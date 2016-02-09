# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for GPG key on the web."""

__metaclass__ = type

from lp.services.features.testing import FeatureFixture
from lp.services.gpg.interfaces import (
    GPGReadOnly,
    GPG_SERVICE_READONLY_FEATURE_FLAG,
    )
from lp.services.webapp import canonical_url
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class TestCanonicalUrl(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_canonical_url(self):
        # The canonical URL of a GPG key is ???
        person = self.factory.makePerson()
        gpgkey = self.factory.makeGPGKey(person)
        self.assertEqual(
            '%s/+gpg-keys/%s' % (
                canonical_url(person, rootsite='api'), gpgkey.keyid),
            canonical_url(gpgkey))


class TestPersonGPGView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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
            GPG_SERVICE_READONLY_FEATURE_FLAG: True,
        }))
        person = self.factory.makePerson()
        login_person(person)
        view = create_initialized_view(person, "+editpgpkeys", principal=person,
                                       method='POST', have_fresh_login=True)
        self.assertRaises(GPGReadOnly, view.render)

    def test_gpgkeys_GET_readonly_with_feature_flag_set(self):
        self.useFixture(FeatureFixture({
            GPG_SERVICE_READONLY_FEATURE_FLAG: True,
        }))
        person = self.factory.makePerson()
        login_person(person)
        view = create_initialized_view(person, "+editpgpkeys", principal=person,
                                       method='GET', have_fresh_login=True)
        view.render()
