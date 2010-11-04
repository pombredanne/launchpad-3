# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for webapp glue."""

__metaclass__ = type

from canonical.testing import layers
from lp.services.features import webapp
from lp.testing import (
    login_as,
    TestCase,
    TestCaseWithFactory,
    )
from canonical.launchpad.webapp.servers import LaunchpadTestRequest


class TestScopesFromRequest(TestCase):

    def test_pageid_scope_normal(self):
        request = LaunchpadTestRequest()
        request.setInWSGIEnvironment('launchpad.pageid', 'foo:bar')
        scopes = webapp.ScopesFromRequest(request)
        self.assertTrue(scopes.lookup('pageid:'))
        self.assertTrue(scopes.lookup('pageid:foo'))
        self.assertTrue(scopes.lookup('pageid:foo:bar'))
        self.assertFalse(scopes.lookup('pageid:foo:bar#quux'))

    def test_pageid_scope_collection(self):
        request = LaunchpadTestRequest()
        request.setInWSGIEnvironment('launchpad.pageid', 'scoped:thing:#type')
        scopes = webapp.ScopesFromRequest(request)
        self.assertTrue(scopes.lookup('pageid:'))
        self.assertTrue(scopes.lookup('pageid:scoped'))
        self.assertTrue(scopes.lookup('pageid:scoped:thing'))
        self.assertTrue(scopes.lookup('pageid:scoped:thing:#type'))
        self.assertFalse(scopes.lookup('pageid:scoped:thing:#type:other'))

    def test_pageid_scope_empty(self):
        request = LaunchpadTestRequest()
        request.setInWSGIEnvironment('launchpad.pageid', '')
        scopes = webapp.ScopesFromRequest(request)
        self.assertTrue(scopes.lookup('pageid:'))
        self.assertFalse(scopes.lookup('pageid:foo'))
        self.assertFalse(scopes.lookup('pageid:foo:bar'))


class TestDBScopes(TestCaseWithFactory):

    layer = layers.DatabaseFunctionalLayer

    def test_team_scope_outside_team(self):
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        self.factory.loginAsAnyone()
        self.assertFalse(scopes.lookup('team:nonexistent'))

    def test_team_scope_in_team(self):
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        member = self.factory.makePerson()
        team = self.factory.makeTeam(members=[member])
        login_as(member)
        self.assertTrue(scopes.lookup('team:%s' % team.name))
