# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
import base64
from zope.interface import implements
from zope.component import getUtility

from zope.publisher.browser import TestRequest
from zope.publisher.interfaces.http import IHTTPCredentials

from zope.app.tests import ztapi
from zope.app.testing.placelesssetup import PlacelessSetup
from zope.app.security.principalregistry import Principal
from zope.app.security.interfaces import ILoginPassword
from zope.app.security.basicauthadapter import BasicAuthAdapter

from zope.app.security.principalregistry import UnauthenticatedPrincipal
from canonical.launchpad.webapp.authentication import PlacelessAuthUtility
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.interfaces import (
    IPasswordEncryptor, IPersonSet, IPerson)

Bruce = Principal('bruce', 'bruce', 'Bruce', 'bruce', 'bruce!')

class DummyPlacelessLoginSource(object):
    implements(IPlacelessLoginSource)

    def getPrincipalByLogin(self, id):
        return Bruce

    getPrincipal = getPrincipalByLogin

    def getPrincipals(self, name):
        return [Bruce]


class DummyPerson(object):
    implements(IPerson)
    is_valid_person = True


class DummyPersonSet(object):
    implements(IPersonSet)
    def get(self, id):
        return DummyPerson()


class TestPlacelessAuth(PlacelessSetup, unittest.TestCase):
    def setUp(self):
        PlacelessSetup.setUp(self)
        ztapi.provideUtility(IPasswordEncryptor, SSHADigestEncryptor())
        ztapi.provideUtility(IPlacelessLoginSource,
                             DummyPlacelessLoginSource())
        ztapi.provideUtility(IPlacelessAuthUtility, PlacelessAuthUtility())
        ztapi.provideAdapter(IHTTPCredentials, ILoginPassword, BasicAuthAdapter)
        ztapi.provideUtility(IPersonSet, DummyPersonSet())

    def tearDown(self):
        ztapi.unprovideUtility(IPasswordEncryptor)
        ztapi.unprovideUtility(IPlacelessLoginSource)
        ztapi.unprovideUtility(IPlacelessAuthUtility)
        ztapi.unprovideUtility(IPersonSet)
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



def test_suite():
    t = unittest.makeSuite(TestPlacelessAuth)
    return unittest.TestSuite((t,))


if __name__=='__main__':
    main(defaultTest='test_suite')
