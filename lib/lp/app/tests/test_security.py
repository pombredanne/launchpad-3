# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getSiteManager
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
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
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


class TestDelegatedAuthorization(TestCase):
    """Tests for `DelegatedAuthorization`."""

    def test_checkAuthenticated(self):
        # DelegatedAuthorization.checkAuthenticated() punts the checks back up
        # to the security policy by generating (object, permission) tuples.
        # The security policy is in a much better position to, well, apply
        # policy.
        obj, delegated_obj = object(), object()
        authorization = DelegatedAuthorization(
            obj, delegated_obj, "dedicatemyselfto.Evil")
        # By default DelegatedAuthorization.checkAuthenticated() ignores its
        # user argument, so we pass None in below, but it is required for
        # IAuthorization, and may be useful for subclasses.
        self.assertEqual(
            [(delegated_obj, "dedicatemyselfto.Evil")],
            list(authorization.checkAuthenticated(None)))

    def test_checkUnauthenticated(self):
        # DelegatedAuthorization.checkUnauthenticated() punts the checks back
        # up to the security policy by generating (object, permission) tuples.
        # The security policy is in a much better position to, well, apply
        # policy.
        obj, delegated_obj = object(), object()
        authorization = DelegatedAuthorization(
            obj, delegated_obj, "dedicatemyselfto.Evil")
        self.assertEqual(
            [(delegated_obj, "dedicatemyselfto.Evil")],
            list(authorization.checkUnauthenticated()))
