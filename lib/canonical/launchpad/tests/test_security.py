# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.launchpad.security import AuthorizationBase
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestAuthorizationBase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_default_checkAccountAuthenticated_for_full_fledged_account(self):
        # AuthorizationBase.checkAccountAuthenticated should delegate to
        # checkAuthenticated() when the given account can be adapted into an
        # IPerson.
        full_fledged_account = self.factory.makePerson().account
        adapter = TestSecurityAdapter(None)
        adapter.checkAccountAuthenticated(full_fledged_account)
        self.failUnless(adapter.checkAuthenticated_called)
        self.failIf(adapter.checkUnauthenticated_called)

    def test_default_checkAccountAuthenticated_for_personless_account(self):
        # AuthorizationBase.checkAccountAuthenticated should delegate to
        # checkUnauthenticated() when the given account can't be adapted into
        # an IPerson.
        personless_account = self.factory.makeAccount('Test account')
        adapter = TestSecurityAdapter(None)
        adapter.checkAccountAuthenticated(personless_account)
        self.failUnless(adapter.checkUnauthenticated_called)
        self.failIf(adapter.checkAuthenticated_called)


class TestSecurityAdapter(AuthorizationBase):

    checkAuthenticated_called = False
    checkUnauthenticated_called = False

    def checkAuthenticated(self, user):
        self.checkAuthenticated_called = True

    def checkUnauthenticated(self):
        self.checkUnauthenticated_called = True


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
