# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the internal codehosting API."""

__metaclass__ = type

from pymacaroons import (
    Macaroon,
    Verifier,
    )
from testtools.matchers import Is
from zope.component import getUtility
from zope.interface import implementer
from zope.publisher.xmlrpc import TestRequest

from lp.services.authserver.xmlrpc import AuthServerAPIView
from lp.services.config import config
from lp.services.macaroons.interfaces import IMacaroonIssuer
from lp.testing import (
    person_logged_in,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessLayer,
    )
from lp.xmlrpc import faults
from lp.xmlrpc.interfaces import IPrivateApplication


class GetUserAndSSHKeysTests(TestCaseWithFactory):
    """Tests for the implementation of `IAuthServer.getUserAndSSHKeys`.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        private_root = getUtility(IPrivateApplication)
        self.authserver = AuthServerAPIView(
            private_root.authserver, TestRequest())

    def test_user_not_found(self):
        # getUserAndSSHKeys returns the NoSuchPersonWithName fault if there is
        # no Person of the given name.
        self.assertEqual(
            faults.NoSuchPersonWithName('no-one'),
            self.authserver.getUserAndSSHKeys('no-one'))

    def test_user_no_keys(self):
        # getUserAndSSHKeys returns a dict with keys ['id', 'name', 'keys'].
        # 'keys' refers to a list of SSH public keys in LP, which is empty for
        # a freshly created user.
        new_person = self.factory.makePerson()
        self.assertEqual(
            dict(id=new_person.id, name=new_person.name, keys=[]),
            self.authserver.getUserAndSSHKeys(new_person.name))

    def test_user_with_keys(self):
        # For a user with registered SSH keys, getUserAndSSHKeys returns the
        # name of the key type (RSA or DSA) and the text of the keys under
        # 'keys' in the dict.
        new_person = self.factory.makePerson()
        with person_logged_in(new_person):
            key = self.factory.makeSSHKey(person=new_person)
            self.assertEqual(
                dict(id=new_person.id, name=new_person.name,
                     keys=[(key.keytype.title, key.keytext)]),
                self.authserver.getUserAndSSHKeys(new_person.name))


@implementer(IMacaroonIssuer)
class DummyMacaroonIssuer:

    _root_secret = 'test'

    def issueMacaroon(self, context):
        """See `IMacaroonIssuer`."""
        macaroon = Macaroon(
            location=config.vhost.mainsite.hostname, identifier='test',
            key=self._root_secret)
        macaroon.add_first_party_caveat('test %s' % context)
        return macaroon

    def checkMacaroonIssuer(self, macaroon):
        """See `IMacaroonIssuer`."""
        if macaroon.location != config.vhost.mainsite.hostname:
            return False
        try:
            verifier = Verifier()
            verifier.satisfy_general(
                lambda caveat: caveat.startswith('test '))
            return verifier.verify(macaroon, self._root_secret)
        except Exception:
            return False

    def verifyMacaroon(self, macaroon, context):
        """See `IMacaroonIssuer`."""
        if not self.checkMacaroonIssuer(macaroon):
            return False
        try:
            verifier = Verifier()
            verifier.satisfy_exact('test %s' % context)
            return verifier.verify(macaroon, self._root_secret)
        except Exception:
            return False


class VerifyMacaroonTests(TestCase):

    layer = ZopelessLayer

    def setUp(self):
        super(VerifyMacaroonTests, self).setUp()
        self.issuer = DummyMacaroonIssuer()
        self.useFixture(ZopeUtilityFixture(
            self.issuer, IMacaroonIssuer, name='test'))
        private_root = getUtility(IPrivateApplication)
        self.authserver = AuthServerAPIView(
            private_root.authserver, TestRequest())

    def test_nonsense_macaroon(self):
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon('nonsense', 0))

    def test_unknown_issuer(self):
        macaroon = Macaroon(
            location=config.vhost.mainsite.hostname,
            identifier='unknown-issuer', key='test')
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon(macaroon.serialize(), 0))

    def test_wrong_context(self):
        macaroon = self.issuer.issueMacaroon(0)
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon(macaroon.serialize(), 1))

    def test_success(self):
        macaroon = self.issuer.issueMacaroon(0)
        self.assertThat(
            self.authserver.verifyMacaroon(macaroon.serialize(), 0), Is(True))
