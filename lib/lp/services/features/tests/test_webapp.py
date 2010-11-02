# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for webapp glue."""

__metaclass__ = type

from canonical.testing import layers
from lp.services.features import webapp
from lp.testing import TestCase
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
        self.assertFalse(scopes.lookup('pageid:foo'))
