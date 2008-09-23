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
from canonical.launchpad.webapp.interfaces import (
    IAuthorization, IPlacelessLoginSource)
from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest
from canonical.testing.layers import DatabaseFunctionalLayer


class Checker(AuthorizationBase):
    """See `IAuthorization`.

    Instances of this class record calls made to `IAuthorization` methods.
    """

    def __init__(self, obj, calls):
        AuthorizationBase.__init__(self, obj)
        self.calls = calls

    def checkUnauthenticated(self):
        """See `IAuthorization.checkUnauthenticated`.

        We record the call and then return False, arbitrarily chosen, to keep
        the policy from complaining.
        """
        self.calls.append('checkUnauthenticated')
        return False

    def checkAuthenticated(self, user):
        """See `IAuthorization.checkAuthenticated`.

        We record the call and then return False, arbitrarily chosen, to keep
        the policy from complaining.
        """
        self.calls.append(('checkAuthenticated', user))
        return False


class CheckerFactory:
    """Factory for `Checker` objects.

    Instances of this class are intended to be registered as adapters to
    `IAuthorization`.

    :ivar calls: Calls made to the methods of `Checker`s constructed by this
        instance.
    """

    def __init__(self):
        self.calls = []

    def __call__(self, obj):
        return Checker(obj, self.calls)


class TestCheckPermissionCaching(TestCaseWithFactory):
    """Test the caching done by `LaunchpadSecurityPolicy.checkPermission`."""

    layer = DatabaseFunctionalLayer

    permission = 'launchpad.Edit'

    def makeRequest(self):
        """Construct an arbitrary `LaunchpadBrowserRequest` object."""
        data = StringIO.StringIO()
        env = {}
        return LaunchpadBrowserRequest(data, env)

    def getObjectAndCheckerFactoryForObject(self):
        """Return an arbitary object and a `CheckerFactory` for it.

        The checker factory is registered as an adapter to `IAuthorization`
        for the object and has a 'calls' attribute that can be used to check
        the calls the security policy makes.
        """
        class C:
            pass
        checker_factory = CheckerFactory()
        ztapi.provideAdapter(
            C, IAuthorization, checker_factory, name=self.permission)
        return C(), checker_factory

    def test_checkPermission_cache_unauthenticated(self):
        # checkPermission caches the result of checkUnauthenticated for a
        # particular object and permission.
        request = self.makeRequest()
        policy = LaunchpadSecurityPolicy(request)
        obj, checker_factory = self.getObjectAndCheckerFactoryForObject()
        # When we call checkPermission for the first time, the security policy
        # calls the checker.
        policy.checkPermission(self.permission, obj)
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)
        # A subsequent identical call does not call the checker.
        policy.checkPermission(self.permission, obj)
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)

    def test_checkPermission_cache_authenticated(self):
        # checkPermission caches the result of checkAuthenticated for a
        # particular object and permission.
        person = self.factory.makePerson()
        login_src = getUtility(IPlacelessLoginSource)
        principal = login_src.getPrincipal(person.id)
        request = self.makeRequest()
        request.setPrincipal(principal)
        policy = LaunchpadSecurityPolicy(request)

        obj, checker_factory = self.getObjectAndCheckerFactoryForObject()

        # When we call checkPermission for the first time, the security policy
        # calls the checker.
        policy.checkPermission(self.permission, obj)
        self.assertEqual(
            [('checkAuthenticated', person)], checker_factory.calls)
        # A subsequent identical call does not call the checker.
        policy.checkPermission(self.permission, obj)
        self.assertEqual(
            [('checkAuthenticated', person)], checker_factory.calls)

    def test_checkPermission_setPrincipal_resets_cache(self):
        # Setting the principal on the request clears the cache of results
        # (this is important during login).
        person = self.factory.makePerson()
        login_src = getUtility(IPlacelessLoginSource)
        principal = login_src.getPrincipal(person.id)
        request = self.makeRequest()
        policy = LaunchpadSecurityPolicy(request)

        obj, checker_factory = self.getObjectAndCheckerFactoryForObject()

        # When we call checkPermission before setting the principal, the
        # security policy calls checkUnauthenticated on the checker.
        policy.checkPermission(self.permission, obj)
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)
        request.setPrincipal(principal)
        # After setting the principal, the policy calls checkAuthenticated
        # rather than finding a value in the cache.
        policy.checkPermission(self.permission, obj)
        self.assertEqual(
            ['checkUnauthenticated', ('checkAuthenticated', person)],
            checker_factory.calls)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

