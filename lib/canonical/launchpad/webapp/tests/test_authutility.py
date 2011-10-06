# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import base64
import unittest

from zope.app.security.basicauthadapter import BasicAuthAdapter
from zope.app.security.interfaces import ILoginPassword
from zope.app.security.principalregistry import UnauthenticatedPrincipal
from zope.app.testing import ztapi
from zope.app.testing.placelesssetup import PlacelessSetup
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces.http import IHTTPCredentials

from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.interfaces.launchpad import IPasswordEncryptor
from canonical.launchpad.webapp.authentication import (
    LaunchpadPrincipal,
    PlacelessAuthUtility,
    )
from canonical.launchpad.webapp.interfaces import (
    IPlacelessAuthUtility,
    IPlacelessLoginSource,
    )
from lp.registry.interfaces.person import IPerson


class DummyPerson(object):
    implements(IPerson)
    is_valid = True


class DummyAccount(object):
    implements(IAccount)
    is_valid = True
    person = DummyPerson()


Bruce = LaunchpadPrincipal(42, 'bruce', 'Bruce', DummyAccount(), 'bruce!')


class DummyPlacelessLoginSource(object):
    implements(IPlacelessLoginSource)

    def getPrincipalByLogin(self, id, want_password=True):
        return Bruce

    getPrincipal = getPrincipalByLogin

    def getPrincipals(self, name):
        return [Bruce]


class DummyPasswordEncryptor(object):
    implements(IPasswordEncryptor)

    def validate(self, plaintext, encrypted):
        return plaintext == encrypted


class TestPlacelessAuth(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        PlacelessSetup.setUp(self)
        ztapi.provideUtility(IPasswordEncryptor, DummyPasswordEncryptor())
        ztapi.provideUtility(IPlacelessLoginSource,
                             DummyPlacelessLoginSource())
        ztapi.provideUtility(IPlacelessAuthUtility, PlacelessAuthUtility())
        ztapi.provideAdapter(
            IHTTPCredentials, ILoginPassword, BasicAuthAdapter)

    def tearDown(self):
        ztapi.unprovideUtility(IPasswordEncryptor)
        ztapi.unprovideUtility(IPlacelessLoginSource)
        ztapi.unprovideUtility(IPlacelessAuthUtility)
        PlacelessSetup.tearDown(self)

    def _make(self, login, pwd):
        dict = {
            'HTTP_AUTHORIZATION':
            'Basic %s' % base64.encodestring('%s:%s' % (login, pwd))}
        request = TestRequest(**dict)
        return getUtility(IPlacelessAuthUtility), request

    def test_authenticate_ok(self):
        authsvc, request = self._make('bruce', 'bruce!')
        self.assertEqual(authsvc.authenticate(request), Bruce)

    def test_authenticate_notok(self):
        authsvc, request = self._make('bruce', 'notbruce!')
        self.assertEqual(authsvc.authenticate(request), None)

    def test_unauthenticatedPrincipal(self):
        authsvc, request = self._make(None, None)
        self.assert_(isinstance(authsvc.unauthenticatedPrincipal(),
                                UnauthenticatedPrincipal))

    def test_unauthorized(self):
        authsvc, request = self._make('bruce', 'bruce!')
        self.assertEqual(authsvc.unauthorized('bruce', request), None)
        self.assertEqual(request._response._status, 401)

    def test_getPrincipal(self):
        authsvc, request = self._make('bruce', 'bruce!')
        self.assertEqual(authsvc.getPrincipal('bruce'), Bruce)

    def test_getPrincipals(self):
        authsvc, request = self._make('bruce', 'bruce!')
        self.assertEqual(authsvc.getPrincipals('bruce'), [Bruce])

    def test_getPrincipalByLogin(self):
        authsvc, request = self._make('bruce', 'bruce!')
        self.assertEqual(authsvc.getPrincipalByLogin('bruce'), Bruce)
