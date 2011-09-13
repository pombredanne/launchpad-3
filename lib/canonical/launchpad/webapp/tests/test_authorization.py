# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `canonical.launchpad.webapp.authorization`."""

__metaclass__ = type

import StringIO
import unittest

import transaction
from zope.component import (
    provideAdapter,
    provideUtility,
    )
from zope.interface import (
    classProvides,
    implements,
    Interface,
    )
from zope.testing.cleanup import CleanUp

from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.webapp.authentication import LaunchpadPrincipal
from canonical.launchpad.webapp.authorization import (
    check_permission,
    LaunchpadSecurityPolicy,
    precache_permission_for_objects,
    )
from canonical.launchpad.webapp.interfaces import (
    AccessLevel,
    ILaunchpadContainer,
    ILaunchpadPrincipal,
    IStoreSelector,
    )
from canonical.launchpad.webapp.metazcml import ILaunchpadPermission
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest,
    LaunchpadTestRequest,
    )
from canonical.lazr.interfaces import IObjectPrivacy
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.interfaces.security import IAuthorization
from lp.app.security import AuthorizationBase
from lp.testing import (
    ANONYMOUS,
    login,
    TestCase,
    )
from lp.testing.factory import ObjectFactory


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

    def checkAccountAuthenticated(self, account):
        """See `IAuthorization.checkAccountAuthenticated`.

        We record the call and then return False, arbitrarily chosen, to keep
        the policy from complaining.
        """
        self.calls.append(('checkAccountAuthenticated', account))
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


class FakeAccount:
    """A minimal object to represent an account."""
    implements(IAccount)


class FakeLaunchpadPrincipal:
    """A minimal principal implementing `ILaunchpadPrincipal`"""
    implements(ILaunchpadPrincipal)
    account = FakeAccount()
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
    @staticmethod
    def push(dbpolicy):
        pass
    @staticmethod
    def pop():
        pass


class TestCheckPermissionCaching(CleanUp, unittest.TestCase):
    """Test the caching done by `LaunchpadSecurityPolicy.checkPermission`."""

    def setUp(self):
        """Register a new permission and a fake store selector."""
        super(TestCheckPermissionCaching, self).setUp()
        self.factory = ObjectFactory()
        provideUtility(FakeStoreSelector, IStoreSelector)

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
        provideUtility(
            PermissionAccessLevel(), ILaunchpadPermission, permission)
        checker_factory = CheckerFactory()
        provideAdapter(
            checker_factory, [Object], IAuthorization, name=permission)
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
        principal = FakeLaunchpadPrincipal()
        request = self.makeRequest()
        request.setPrincipal(principal)
        policy = LaunchpadSecurityPolicy(request)
        obj, permission, checker_factory = (
            self.getObjectPermissionAndCheckerFactory())
        # When we call checkPermission for the first time, the security policy
        # calls the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            [('checkAccountAuthenticated', principal.account)],
            checker_factory.calls)
        # A subsequent identical call does not call the checker.
        policy.checkPermission(permission, obj)
        self.assertEqual(
            [('checkAccountAuthenticated', principal.account)],
            checker_factory.calls)

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
        principal = FakeLaunchpadPrincipal()
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
            ['checkUnauthenticated', ('checkAccountAuthenticated',
                                      principal.account)],
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


class TestLaunchpadSecurityPolicy_getPrincipalsAccessLevel(
    CleanUp, unittest.TestCase):

    def setUp(self):
        self.principal = LaunchpadPrincipal(
            'foo.bar@canonical.com', 'foo', 'foo', object())
        self.security = LaunchpadSecurityPolicy()
        provideAdapter(
            adapt_loneobject_to_container, [ILoneObject], ILaunchpadContainer)

    def test_no_scope(self):
        """Principal's access level is used when no scope is given."""
        self.principal.access_level = AccessLevel.WRITE_PUBLIC
        self.principal.scope = None
        self.failUnlessEqual(
            self.security._getPrincipalsAccessLevel(
                self.principal, LoneObject()),
            self.principal.access_level)

    def test_object_within_scope(self):
        """Principal's access level is used when object is within scope."""
        obj = LoneObject()
        self.principal.access_level = AccessLevel.WRITE_PUBLIC
        self.principal.scope = obj
        self.failUnlessEqual(
            self.security._getPrincipalsAccessLevel(self.principal, obj),
            self.principal.access_level)

    def test_object_not_within_scope(self):
        """READ_PUBLIC is used when object is /not/ within scope."""
        obj = LoneObject()
        obj2 = LoneObject()  # This is out of obj's scope.
        self.principal.scope = obj

        self.principal.access_level = AccessLevel.WRITE_PUBLIC
        self.failUnlessEqual(
            self.security._getPrincipalsAccessLevel(self.principal, obj2),
            AccessLevel.READ_PUBLIC)

        self.principal.access_level = AccessLevel.READ_PRIVATE
        self.failUnlessEqual(
            self.security._getPrincipalsAccessLevel(self.principal, obj2),
            AccessLevel.READ_PUBLIC)

        self.principal.access_level = AccessLevel.WRITE_PRIVATE
        self.failUnlessEqual(
            self.security._getPrincipalsAccessLevel(self.principal, obj2),
            AccessLevel.READ_PUBLIC)


class ILoneObject(Interface):
    """A marker interface for objects that only contain themselves."""


class LoneObject:
    implements(ILoneObject, ILaunchpadContainer)

    def isWithin(self, context):
        return self == context


def adapt_loneobject_to_container(loneobj):
    """Adapt a LoneObject to an `ILaunchpadContainer`."""
    return loneobj


class TestPrecachePermissionForObjects(TestCase):
    """Test the precaching of permissions."""

    layer = DatabaseFunctionalLayer

    def test_precaching_permissions(self):
        # The precache_permission_for_objects function updates the security
        # policy cache for the permission specified.
        class Boring(object):
            """A boring, but weakref-able object."""
        objects = [Boring(), Boring()]
        request = LaunchpadTestRequest()
        login(ANONYMOUS, request)
        precache_permission_for_objects(request, 'launchpad.View', objects)
        # Confirm that the objects have the permission set.
        self.assertTrue(check_permission('launchpad.View', objects[0]))
        self.assertTrue(check_permission('launchpad.View', objects[1]))
