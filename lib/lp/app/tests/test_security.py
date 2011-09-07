# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import (
    getSiteManager,
    queryAdapter,
    )
from zope.interface import (
    implements,
    Interface,
    )

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.app.interfaces.security import IAuthorization
from lp.app.security import (
    AuthorizationBase,
    DelegatedAuthorization,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


def registerFakeSecurityAdapter(interface, permission, adapter=None):
    """Register an instance of FakeSecurityAdapter.

    Create a factory for an instance of FakeSecurityAdapter and register
    it as an adapter for the given interface and permission name.
    """
    if adapter is None:
        adapter = FakeSecurityAdapter()

    def adapter_factory(adaptee):
        return adapter

    getSiteManager().registerAdapter(
        adapter_factory, (interface,), IAuthorization, permission)
    return adapter


class FakeSecurityAdapter(AuthorizationBase):

    def __init__(self, adaptee=None):
        super(FakeSecurityAdapter, self).__init__(adaptee)
        self.checkAuthenticated = FakeMethod()
        self.checkUnauthenticated = FakeMethod()


class IDummy(Interface):
    """Marker interface to test forwarding."""


class Dummy:
    """An implementation of IDummy."""
    implements(IDummy)


class TestAuthorizationBase(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_checkAccountAuthenticated_for_full_fledged_account(self):
        # AuthorizationBase.checkAccountAuthenticated should delegate to
        # checkAuthenticated() when the given account can be adapted into an
        # IPerson.
        full_fledged_account = self.factory.makePerson().account
        adapter = FakeSecurityAdapter()
        adapter.checkAccountAuthenticated(full_fledged_account)
        self.assertVectorEqual(
            (1, adapter.checkAuthenticated.call_count),
            (0, adapter.checkUnauthenticated.call_count))

    def test_checkAccountAuthenticated_for_personless_account(self):
        # AuthorizationBase.checkAccountAuthenticated should delegate to
        # checkUnauthenticated() when the given account can't be adapted into
        # an IPerson.
        personless_account = self.factory.makeAccount('Test account')
        adapter = FakeSecurityAdapter()
        adapter.checkAccountAuthenticated(personless_account)
        self.assertVectorEqual(
            (0, adapter.checkAuthenticated.call_count),
            (1, adapter.checkUnauthenticated.call_count))

    def test_forwardCheckAuthenticated_object_changes(self):
        # Requesting a check for the same permission on a different object.
        permission = self.factory.getUniqueString()
        next_adapter = registerFakeSecurityAdapter(
            IDummy, permission)

        adapter = FakeSecurityAdapter()
        adapter.permission = permission
        adapter.usedfor = None
        adapter.checkPermissionIsRegistered = FakeMethod(result=True)

        adapter.forwardCheckAuthenticated(None, Dummy())

        self.assertVectorEqual(
            (1, adapter.checkPermissionIsRegistered.call_count),
            (1, next_adapter.checkAuthenticated.call_count))

    def test_forwardCheckAuthenticated_permission_changes(self):
        # Requesting a check for a different permission on the same object.
        next_permission = self.factory.getUniqueString()
        next_adapter = registerFakeSecurityAdapter(
            IDummy, next_permission)

        adapter = FakeSecurityAdapter(Dummy())
        adapter.permission = self.factory.getUniqueString()
        adapter.usedfor = IDummy
        adapter.checkPermissionIsRegistered = FakeMethod(result=True)

        adapter.forwardCheckAuthenticated(None, permission=next_permission)

        self.assertVectorEqual(
            (1, adapter.checkPermissionIsRegistered.call_count),
            (1, next_adapter.checkAuthenticated.call_count))

    def test_forwardCheckAuthenticated_both_change(self):
        # Requesting a check for a different permission and a different
        # object.
        next_permission = self.factory.getUniqueString()
        next_adapter = registerFakeSecurityAdapter(
            IDummy, next_permission)

        adapter = FakeSecurityAdapter()
        adapter.permission = self.factory.getUniqueString()
        adapter.usedfor = None
        adapter.checkPermissionIsRegistered = FakeMethod(result=True)

        adapter.forwardCheckAuthenticated(None, Dummy(), next_permission)

        self.assertVectorEqual(
            (1, adapter.checkPermissionIsRegistered.call_count),
            (1, next_adapter.checkAuthenticated.call_count))

    def test_forwardCheckAuthenticated_no_forwarder(self):
        # If the requested forwarding adapter does not exist, return False.
        adapter = FakeSecurityAdapter()
        adapter.permission = self.factory.getUniqueString()
        adapter.usedfor = IDummy
        adapter.checkPermissionIsRegistered = FakeMethod(result=True)

        self.assertFalse(
            adapter.forwardCheckAuthenticated(None, Dummy()))


class FakeDelegatedAuthorization(DelegatedAuthorization):
    def __init__(self, obj, permission=None):
        super(FakeDelegatedAuthorization, self).__init__(
            obj.child_obj, permission)


class FakeForwardedObject:
    implements(IDummy)

    def __init__(self):
        self.child_obj = Dummy()


class TestDelegatedAuthorizationBase(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_DelegatedAuthorization_same_permissions(self):

        permission = self.factory.getUniqueString()
        fake_obj = FakeForwardedObject()
        outer_adapter = FakeDelegatedAuthorization(fake_obj)
        outer_adapter.permission = permission

        inner_adapter = FakeSecurityAdapter()
        inner_adapter.permission = permission
        registerFakeSecurityAdapter(IDummy, permission, inner_adapter)
        user = object()
        outer_adapter.checkAuthenticated(user)
        outer_adapter.checkUnauthenticated()
        self.assertVectorEqual(
            (1, inner_adapter.checkAuthenticated.call_count),
            (1, inner_adapter.checkUnauthenticated.call_count))

    def test_DelegatedAuthorization_different_permissions(self):
        perm_inner = 'inner'
        perm_outer = 'outer'
        fake_obj = FakeForwardedObject()
        outer_adapter = FakeDelegatedAuthorization(fake_obj, perm_inner)
        registerFakeSecurityAdapter(IDummy, perm_outer, outer_adapter)

        inner_adapter = FakeSecurityAdapter()
        inner_adapter.permission = perm_inner
        registerFakeSecurityAdapter(IDummy, perm_inner, inner_adapter)

        user = object()
        adapter = queryAdapter(
            FakeForwardedObject(), IAuthorization, perm_outer)
        adapter.checkAuthenticated(user)
        adapter.checkUnauthenticated()
        self.assertVectorEqual(
            (1, inner_adapter.checkAuthenticated.call_count),
            (1, inner_adapter.checkUnauthenticated.call_count))
