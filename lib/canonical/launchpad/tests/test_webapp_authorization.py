# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.interface import implements

from canonical.testing import ZopelessLayer

from canonical.launchpad.webapp.interfaces import ILaunchpadContainer
from canonical.launchpad.webapp.authentication import LaunchpadPrincipal
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.interfaces import AccessLevel


class TestLaunchpadSecurityPolicy_getPrincipalsAccessLevel(unittest.TestCase):
    layer = ZopelessLayer

    def setUp(self):
        self.principal = LaunchpadPrincipal(
            'foo.bar@canonical.com', 'foo', 'foo', object())
        self.security = LaunchpadSecurityPolicy()

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


class LoneObject:
    """An object which is only within itself."""
    implements(ILaunchpadContainer)

    def isWithin(self, context):
        return self == context


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
