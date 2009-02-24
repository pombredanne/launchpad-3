# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for `canonical.launchpad.webapp.authorization`."""

__metaclass__ = type

import StringIO
import unittest

import transaction

from zope.app.testing import ztapi
from zope.interface import implements, classProvides
from zope.testing.cleanup import CleanUp

from canonical.lazr.interfaces import IObjectPrivacy

from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.security import AuthorizationBase
from canonical.launchpad.testing import ObjectFactory
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.interfaces import (
    IAuthorization, IStoreSelector)
from canonical.launchpad.webapp.metazcml import ILaunchpadPermission
from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest


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


class Object:
    """An arbitrary object, adaptable to `IObjectPrivacy`.

    For simplicity we implement `IObjectPrivacy` directly."""
    implements(IObjectPrivacy)
    is_private = False


class PermissionAccessLevel:
    """A minimal implementation of `ILaunchpadPermission`."""
    implements(ILaunchpadPermission)
    access_level = 'read'


class FakePersonPrincipal:
    """A minimal principal that can be adapted to `IAccount` and `IPerson`.

    For simplicity we declare this class implements `IAccount` and
    `IPerson` so it will just adapt to itself.
    """
    implements(IAccount, IPerson)
    scope = None
    access_level = ''


class FakeStore:
    """Enough of a store to fool the `block_implicit_flushes` decorator."""
    def block_implicit_flushes(self):
        pass
    def unblock_implicit_flushes(self):
        pass


class FakeStoreSelector:
    """A store selector that always returns a `FakeStore`."""
    classProvides(IStoreSelector)
    @staticmethod
    def get(name, flavor):
        return FakeStore()


class TestCheckPermissionCaching(CleanUp, unittest.TestCase):
    """Test the caching done by `LaunchpadSecurityPolicy.checkPermission`."""

    def setUp(self):
        """Register a new permission and a fake store selector."""
        super(TestCheckPermissionCaching, self).setUp()
        self.factory = ObjectFactory()
        ztapi.provideUtility(IStoreSelector, FakeStoreSelector)

    def makeRequest(self):
        """Construct an arbitrary `LaunchpadBrowserRequest` object."""
        data = StringIO.StringIO()
        env = {}
        return LaunchpadBrowserRequest(data, env)

    def getObjectPermissionAndCheckerFactory(self):
        """Return an object, a permission and a `CheckerFactory` for them.

        :return: A tuple ``(obj, permission, checker_factory)``, such that
            ``queryAdapter(obj, IAuthorization, permission)`` will return a
            `Checker` created by ``checker_factory``.
        """
        permission = self.factory.getUniqueString()
        ztapi.provideUtility(
            ILaunchpadPermission, PermissionAccessLevel(), permission)
        checker_factory = CheckerFactory()
        ztapi.provideAdapter(
            Object, IAuthorization, checker_factory, name=permission)
        return Object(), permission, checker_factory

    def test_checkPermission_cache_unauthenticated(self):
        # checkPermission caches the result of checkUnauthenticated for a
        # particular object and permission.
        request = self.makeRequest()
        policy = LaunchpadSecurityPolicy(request)
        obj, permission, checker_factory = (
            self.getObjectPermissionAndCheckerFactory())
        # When we call checkPermission for the first time, the security policy
        # calls the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)
        # A subsequent identical call does not call the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)

    def test_checkPermission_cache_authenticated(self):
        # checkPermission caches the result of checkAuthenticated for a
        # particular object and permission.
        principal = FakePersonPrincipal()
        request = self.makeRequest()
        request.setPrincipal(principal)
        policy = LaunchpadSecurityPolicy(request)
        obj, permission, checker_factory = (
            self.getObjectPermissionAndCheckerFactory())
        # When we call checkPermission for the first time, the security policy
        # calls the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            [('checkAuthenticated', principal)], checker_factory.calls)
        # A subsequent identical call does not call the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            [('checkAuthenticated', principal)], checker_factory.calls)

    def test_checkPermission_clearSecurityPolicyCache_resets_cache(self):
        # Calling clearSecurityPolicyCache on the request clears the cache.
        request = self.makeRequest()
        policy = LaunchpadSecurityPolicy(request)
        obj, permission, checker_factory = (
            self.getObjectPermissionAndCheckerFactory())
        # When we call checkPermission for the first time, the security policy
        # calls checkUnauthenticated on the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)
        request.clearSecurityPolicyCache()
        # After clearing the cache the policy calls checkUnauthenticated
        # again.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            ['checkUnauthenticated', 'checkUnauthenticated'],
            checker_factory.calls)

    def test_checkPermission_setPrincipal_resets_cache(self):
        # Setting the principal on the request clears the cache of results
        # (this is important during login).
        principal = FakePersonPrincipal()
        request = self.makeRequest()
        policy = LaunchpadSecurityPolicy(request)
        obj, permission, checker_factory = (
            self.getObjectPermissionAndCheckerFactory())
        # When we call checkPermission before setting the principal, the
        # security policy calls checkUnauthenticated on the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)
        request.setPrincipal(principal)
        # After setting the principal, the policy calls checkAuthenticated
        # rather than finding a value in the cache.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            ['checkUnauthenticated', ('checkAuthenticated', principal)],
            checker_factory.calls)

    def test_checkPermission_commit_clears_cache(self):
        # Committing a transaction clears the cache.
        request = self.makeRequest()
        policy = LaunchpadSecurityPolicy(request)
        obj, permission, checker_factory = (
            self.getObjectPermissionAndCheckerFactory())
        # When we call checkPermission before setting the principal, the
        # security policy calls checkUnauthenticated on the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            ['checkUnauthenticated'], checker_factory.calls)
        transaction.commit()
        # After committing a transaction, the policy calls
        # checkUnauthenticated again rather than finding a value in the cache.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            ['checkUnauthenticated', 'checkUnauthenticated'],
            checker_factory.calls)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
