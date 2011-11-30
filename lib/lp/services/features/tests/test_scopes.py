# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test feature-flag scopes."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.testing import (
    TestCaseWithFactory,
    )

from lp.services.features.scopes import (
    BaseScope,
    MultiScopeHandler,
    ScopesForScript,
    ScriptScope,
    UserSliceScope,
    )


class FakeScope(BaseScope):

    pattern = r'fake:'

    def __init__(self, name):
        self.name = name

    def lookup(self, scope_name):
        return scope_name == (self.pattern + self.name)


class TestScopes(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_ScriptScope_lookup_matches_script_scope(self):
        script_name = self.factory.getUniqueString()
        scope = ScriptScope(script_name)
        self.assertTrue(scope.lookup("script:" + script_name))

    def test_ScriptScope_lookup_does_not_match_other_script_scope(self):
        script_name = self.factory.getUniqueString()
        scope = ScriptScope(script_name)
        self.assertFalse(scope.lookup("script:other"))

    def test_MultiScopeHandler_lookup_ignores_unmatched_scope(self):
        scope_name = self.factory.getUniqueString()
        fake_scope = FakeScope(scope_name)
        handler = MultiScopeHandler([fake_scope])
        self.assertFalse(handler.lookup("other:other"))

    def test_MultiScopeHandler_lookup_ignores_inapplicable_scope(self):
        scope_name = self.factory.getUniqueString()
        handler = MultiScopeHandler([FakeScope(scope_name)])
        self.assertFalse(handler.lookup("fake:other"))

    def test_MultiScopeHandler_lookup_finds_matching_scope(self):
        scope_name = self.factory.getUniqueString()
        handler = MultiScopeHandler([FakeScope(scope_name)])
        self.assertTrue(handler.lookup("fake:" + scope_name))

    def test_ScopesForScript_includes_default_scope(self):
        script_name = self.factory.getUniqueString()
        scopes = ScopesForScript(script_name)
        self.assertTrue(scopes.lookup("default"))

    def test_ScopesForScript_lookup_finds_script(self):
        script_name = self.factory.getUniqueString()
        scopes = ScopesForScript(script_name)
        self.assertTrue(scopes.lookup("script:" + script_name))

    def test_ScopesForScript_lookup_does_not_find_other_script(self):
        script_name = self.factory.getUniqueString()
        scopes = ScopesForScript(script_name)
        self.assertFalse(scopes.lookup("script:other"))


class TestUserSliceScope(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_user_modulus(self):
        person = self.factory.makePerson()
        # NB: scopes take a callable that returns the person, that in
        # production comes from the request.
        scope = UserSliceScope(lambda: person)
        # Effectively selects everyone; should always be true.
        self.assertTrue(scope.lookup('userslice:0,1'))
        # Exactly one of these should be true.
        checks = 7
        matches = []
        for i in range(checks):
            name = 'userslice:%d,%d' % (i, checks)
            if scope.lookup(name):
                matches.append(name)
        self.assertEquals(len(matches), 1, matches)
