# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `canonical.launchpad.webapp.authorization`."""

__metaclass__ = type

from random import getrandbits
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
    iter_authorization,
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
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessLayer,
    )
from lp.app.interfaces.security import IAuthorization
from lp.app.security import AuthorizationBase
from lp.testing import (
    ANONYMOUS,
    login,
    TestCase,
    )
from lp.testing.factory import ObjectFactory
from lp.testing.fixture import ZopeAdapterFixture


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


class Allow(AuthorizationBase):
    """An `IAuthorization` adapter allowing everything."""

    def checkUnauthenticated(self):
        return True

    def checkAccountAuthenticated(self, account):
        return True


class Deny(AuthorizationBase):
    """An `IAuthorization` adapter denying everything."""

    def checkUnauthenticated(self):
        return False

    def checkAccountAuthenticated(self, account):
        return False


class Explode(AuthorizationBase):
    """An `IAuthorization` adapter that explodes when used."""

    def checkUnauthenticated(self):
        raise NotImplementedError()

    def checkAccountAuthenticated(self, account):
        raise NotImplementedError()


class AnotherObjectOne:
    """Another arbitrary object."""


class AnotherObjectTwo:
    """Another arbitrary object."""


class DelegateToAnotherObject(AuthorizationBase):
    """An `IAuthorization` adapter that delegates to `AnotherObject`."""

    permission = "making.Hay"

    def checkUnauthenticated(self):
        yield AnotherObjectOne(), self.permission
        yield AnotherObjectTwo(), self.permission

    def checkAccountAuthenticated(self, account):
        yield AnotherObjectOne(), self.permission
        yield AnotherObjectTwo(), self.permission


class TestIterAuthorization(TestCase):
    """Tests for `iter_authorization`.

    In the tests (and their names) below, "normal" refers to a non-delegated
    authorization.
    """

    # TODO: Show that cache is updated.
    # TODO: Use more tokens.

    layer = ZopelessLayer

    def setUp(self):
        super(TestIterAuthorization, self).setUp()
        self.object = Object()
        self.principal = FakeLaunchpadPrincipal()
        self.permission = "docking.Permission"

    def allow(self):
        """Allow authorization for `Object` with `self.permission`."""
        self.useFixture(
            ZopeAdapterFixture(Allow, [Object], name=self.permission))

    def deny(self):
        """Deny authorization for `Object` with `self.permission`."""
        self.useFixture(
            ZopeAdapterFixture(Deny, [Object], name=self.permission))

    def explode(self):
        """Explode if auth for `Object` with `self.permission` is tried."""
        self.useFixture(
            ZopeAdapterFixture(Explode, [Object], name=self.permission))

    def delegate(self):
        self.useFixture(
            ZopeAdapterFixture(
                DelegateToAnotherObject, [Object], name=self.permission))
        # Allow auth to AnotherObjectOne.
        self.useFixture(
            ZopeAdapterFixture(
                Allow, [AnotherObjectOne], name=(
                    DelegateToAnotherObject.permission)))
        # Deny auth to AnotherObjectTwo.
        self.useFixture(
            ZopeAdapterFixture(
                Deny, [AnotherObjectTwo], name=(
                    DelegateToAnotherObject.permission)))

    #
    # Non-delegated, non-cached checks.
    #

    def test_normal_unauthenticated_no_adapter(self):
        # Authorization is denied when there's no adapter.
        expected = [False]
        observed = iter_authorization(
            self.object, self.permission, principal=None, cache=None)
        self.assertEqual(expected, list(observed))

    def test_normal_unauthenticated_allowed(self):
        # Authorization is allowed when the adapter returns True.
        self.allow()
        expected = [True]
        observed = iter_authorization(
            self.object, self.permission, principal=None, cache=None)
        self.assertEqual(expected, list(observed))

    def test_normal_unauthenticated_denied(self):
        # Authorization is denied when the adapter returns True.
        self.deny()
        expected = [False]
        observed = iter_authorization(
            self.object, self.permission, principal=None, cache=None)
        self.assertEqual(expected, list(observed))

    def test_normal_authenticated_no_adapter(self):
        # Authorization is denied when there's no adapter.
        expected = [False]
        observed = iter_authorization(
            self.object, self.permission, self.principal, cache=None)
        self.assertEqual(expected, list(observed))

    def test_normal_authenticated_allowed(self):
        # Authorization is allowed when the adapter returns True.
        self.allow()
        expected = [True]
        observed = iter_authorization(
            self.object, self.permission, self.principal, cache=None)
        self.assertEqual(expected, list(observed))

    def test_normal_authenticated_denied(self):
        # Authorization is denied when the adapter returns True.
        self.deny()
        expected = [False]
        observed = iter_authorization(
            self.object, self.permission, self.principal, cache=None)
        self.assertEqual(expected, list(observed))

    #
    # Non-delegated, cached checks.
    #

    def test_normal_unauthenticated_no_adapter_cached(self):
        # Authorization is taken from the cache even if an adapter is not
        # registered. This situation - the cache holding a result for an
        # object+permission for which there is no IAuthorization adapter -
        # will not arise unless the cache is tampered with, so this test is
        # solely for documentation.
        token = getrandbits(32)
        expected = [token]
        observed = iter_authorization(
            self.object, self.permission, principal=None,
            cache={self.object: {self.permission: token}})
        self.assertEqual(expected, list(observed))

    def test_normal_unauthenticated_cached(self):
        # Authorization is taken from the cache regardless of the presence of
        # an adapter or its behaviour.
        self.explode()
        token = getrandbits(32)
        expected = [token]
        observed = iter_authorization(
            self.object, self.permission, principal=None,
            cache={self.object: {self.permission: token}})
        self.assertEqual(expected, list(observed))

    def test_normal_authenticated_no_adapter_cached(self):
        # Authorization is taken from the cache even if an adapter is not
        # registered. This situation - the cache holding a result for an
        # object+permission for which there is no IAuthorization adapter -
        # will not arise unless the cache is tampered with, so this test is
        # solely for documentation.
        token = getrandbits(32)
        expected = [token]
        observed = iter_authorization(
            self.object, self.permission, self.principal,
            cache={self.object: {self.permission: token}})
        self.assertEqual(expected, list(observed))

    def test_normal_authenticated_cached(self):
        # Authorization is taken from the cache regardless of the presence of
        # an adapter or its behaviour.
        self.explode()
        token = getrandbits(32)
        expected = [token]
        observed = iter_authorization(
            self.object, self.permission, principal=self.principal,
            cache={self.object: {self.permission: token}})
        self.assertEqual(expected, list(observed))

    #
    # Delegated checks.
    #

    def test_delegated_unauthenticated(self):
        # Authorization is delegated and we see the results of authorization
        # against the objects to which it has been delegated.
        self.delegate()
        expected = [True, False]
        observed = iter_authorization(
            self.object, self.permission, principal=None, cache=None)
        self.assertEqual(expected, list(observed))

    def test_delegated_authenticated(self):
        # Authorization is delegated and we see the results of authorization
        # against the objects to which it has been delegated.
        self.delegate()
        expected = [True, False]
        observed = iter_authorization(
            self.object, self.permission, self.principal, cache=None)
        self.assertEqual(expected, list(observed))
