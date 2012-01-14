# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import base64

from zope.app.security.principalregistry import UnauthenticatedPrincipal
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.browser import TestRequest

from lp.registry.interfaces.person import IPerson
from lp.services.config import config
from lp.services.identity.interfaces.account import IAccount
from lp.services.webapp.authentication import LaunchpadPrincipal
from lp.services.webapp.interfaces import (
    IPlacelessAuthUtility,
    IPlacelessLoginSource,
    )
from lp.testing import TestCase
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import DatabaseFunctionalLayer


class DummyPerson(object):
    implements(IPerson)
    is_valid_person = True


class DummyAccount(object):
    implements(IAccount)
    person = DummyPerson()


Bruce = LaunchpadPrincipal(42, 'bruce', 'Bruce', DummyAccount())
Bruce.person = Bruce.account.person


class DummyPlacelessLoginSource(object):
    implements(IPlacelessLoginSource)

    def getPrincipalByLogin(self, id):
        return Bruce

    getPrincipal = getPrincipalByLogin

    def getPrincipals(self, name):
        return [Bruce]


class TestPlacelessAuth(TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPlacelessAuth, self).setUp()
        self.useFixture(ZopeUtilityFixture(
            DummyPlacelessLoginSource(), IPlacelessLoginSource, ''))

    def _make(self, login, pwd):
        dict = {
            'HTTP_AUTHORIZATION':
            'Basic %s' % base64.encodestring('%s:%s' % (login, pwd))}
        request = TestRequest(**dict)
        return getUtility(IPlacelessAuthUtility), request

    def test_authenticate_ok(self):
        authsvc, request = self._make('bruce', 'test')
        self.assertEqual(authsvc.authenticate(request), Bruce)

    def test_authenticate_notok(self):
        authsvc, request = self._make('bruce', 'nottest')
        self.assertEqual(authsvc.authenticate(request), None)

    def test_unauthenticatedPrincipal(self):
        authsvc, request = self._make(None, None)
        self.assert_(isinstance(authsvc.unauthenticatedPrincipal(),
                                UnauthenticatedPrincipal))

    def test_unauthorized(self):
        authsvc, request = self._make('bruce', 'test')
        self.assertEqual(authsvc.unauthorized('bruce', request), None)
        self.assertEqual(request._response._status, 401)

    def test_only_for_testrunner(self):
        # Basic authentication only works on a launchpad_ftest*
        # database, with a mainsite hostname of launchpad.dev. It has a
        # hardcoded password, so must never be used on production.
        try:
            config.push(
                "change-rooturl", "[vhost.mainsite]\nhostname: launchpad.net")
            authsvc, request = self._make('bruce', 'test')
            self.assertRaisesWithContent(
                AssertionError,
                "Attempted to use basic auth outside the test suite.",
                authsvc.authenticate, request)
        finally:
            config.pop("change-rooturl")

    def test_getPrincipal(self):
        authsvc, request = self._make('bruce', 'test')
        self.assertEqual(authsvc.getPrincipal('bruce'), Bruce)

    def test_getPrincipals(self):
        authsvc, request = self._make('bruce', 'test')
        self.assertEqual(authsvc.getPrincipals('bruce'), [Bruce])

    def test_getPrincipalByLogin(self):
        authsvc, request = self._make('bruce', 'test')
        self.assertEqual(authsvc.getPrincipalByLogin('bruce'), Bruce)
