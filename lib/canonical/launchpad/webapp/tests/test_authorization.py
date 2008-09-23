# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for `canonical.launchpad.webapp.authorization`."""

__metaclass__ = type

import StringIO
import unittest

from zope.app.testing import ztapi
from zope.component import getUtility

from canonical.launchpad.security import AuthorizationBase
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.interfaces import IAuthorization, IPlacelessLoginSource
from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest
from canonical.testing.layers import DatabaseFunctionalLayer


class Checker(AuthorizationBase):

    def __init__(self, obj, calls):
        AuthorizationBase.__init__(self, obj)
        self.calls = calls

    def checkUnauthenticated(self):
        self.calls.append('checkUnauthenticated')
        return False

    def checkAuthenticated(self, user):
        self.calls.append(('checkAuthenticated', user))
        return True


class CheckerFactory:

    def __init__(self):
        self.calls = []

    def __call__(self, obj):
        return Checker(obj, self.calls)


class TestCheckPermissionCaching(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    permission = 'launchpad.Edit'

    def makeRequest(self):
        data = StringIO.StringIO()
        env = {}
        return LaunchpadBrowserRequest(data, env)

    def registerCheckerFactoryForClass(self, cls):
        checker_factory = CheckerFactory()
        ztapi.provideAdapter(
            cls, IAuthorization, checker_factory, name=self.permission)
        return checker_factory

    def test_checkPermission_cache_unauthenticated(self):
        request = self.makeRequest()
        policy = LaunchpadSecurityPolicy(request)
        class C:
            pass
        checker_factory = self.registerCheckerFactoryForClass(C)
        objecttoauthorize = C()
        self.assertEqual(
            False, policy.checkPermission(self.permission, objecttoauthorize))
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)
        self.assertEqual(
            False, policy.checkPermission(self.permission, objecttoauthorize))
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)

    def test_checkPermission_cache_authenticated(self):
        person = self.factory.makePerson()
        login_src = getUtility(IPlacelessLoginSource)
        principal = login_src.getPrincipal(person.id)
        request = self.makeRequest()
        request.setPrincipal(principal)
        policy = LaunchpadSecurityPolicy(request)
        class C:
            pass
        checker_factory = self.registerCheckerFactoryForClass(C)
        objecttoauthorize = C()
        self.assertEqual(
            True, policy.checkPermission(self.permission, objecttoauthorize))
        self.assertEqual(
            [('checkAuthenticated', person)], checker_factory.calls)
        self.assertEqual(
            True, policy.checkPermission(self.permission, objecttoauthorize))
        self.assertEqual(
            [('checkAuthenticated', person)], checker_factory.calls)

    def test_checkPermission_setPrincipal_resets_cache(self):
        person = self.factory.makePerson()
        login_src = getUtility(IPlacelessLoginSource)
        principal = login_src.getPrincipal(person.id)
        request = self.makeRequest()
        policy = LaunchpadSecurityPolicy(request)
        class C:
            pass
        checker_factory = self.registerCheckerFactoryForClass(C)
        objecttoauthorize = C()
        self.assertEqual(
            False, policy.checkPermission(self.permission, objecttoauthorize))
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)
        request.setPrincipal(principal)
        self.assertEqual(
            True, policy.checkPermission(self.permission, objecttoauthorize))
        self.assertEqual(
            ['checkUnauthenticated', ('checkAuthenticated', person)],
            checker_factory.calls)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

