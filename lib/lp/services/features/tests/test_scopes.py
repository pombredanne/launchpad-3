# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test feature-flag scopes."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.services.features.scopes import (
    BaseScope,
    BaseWebRequestScope,
    DefaultScope,
    MailHeaderScope,
    MultiScopeHandler,
    ScopesForMail,
    ScopesForScript,
    ScriptScope,
    ServerScope,
    )
from testtools.matchers import (
    Matcher,
    MatchesAll,
    Mismatch,
    )


class MultiScopeContains(Matcher):
    """Matches if a MultiScopeHandler checks the given scope."""

    def __init__(self, scope_class):
        self.scope_class = scope_class

    def match(self, multi_handler):
        for h in multi_handler.handlers:
            if isinstance(h, self.scope_class):
                return
        else:
            return Mismatch(
                "Scope class %r not found in %r"
                % (scope_class, multi_scope))


class FakeScope(BaseWebRequestScope):
    pattern = r'fake:'

    def lookup(self, scope_name):
        return scope_name == (self.pattern + self.request)


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


class TestMailScopes(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def make_mail_scopes(self):
        fake_email = None
        scopes = ScopesForMail(fake_email)
        return scopes

    def test_ScopesForMail_examines_server(self):
        mail_scopes = self.make_mail_scopes()
        self.assertThat(mail_scopes, MatchesAll(
            MultiScopeContains(ServerScope),
            MultiScopeContains(DefaultScope),
            MultiScopeContains(MailHeaderScope),
            ))

    # TODO: test checking the current interaction user works
    # TODO: checking the server
    # TODO: checking the email from address
    # TODO: checking the dkim signer
