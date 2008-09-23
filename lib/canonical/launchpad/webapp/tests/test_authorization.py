# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for `canonical.launchpad.webapp.authorization`."""

__metaclass__ = type

import StringIO
import unittest

from zope.app.testing import ztapi

from canonical.launchpad.security import AuthorizationBase
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.interfaces import IAuthorization
from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest
from canonical.testing.layers import DatabaseFunctionalLayer


class Checker(AuthorizationBase):

    def __init__(self, obj, calls):
        AuthorizationBase.__init__(self, obj)
        self.calls = calls

    def checkUnauthenticated(self):
        self.calls.append('checkUnauthenticated')
        return False


class CheckerFactory:

    def __init__(self):
        self.calls = []

    def __call__(self, obj):
        return Checker(obj, self.calls)


class TestCheckPermissionCaching(unittest.TestCase):

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
        policy.checkPermission(self.permission, objecttoauthorize)
        self.assertEqual(['checkUnauthenticated'], checker_factory.calls)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

