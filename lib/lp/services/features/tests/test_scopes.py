# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test feature-flag scopes."""

__metaclass__ = type

import email

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
    MatchesAny,
    Mismatch,
    Not,
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


class ScopeMatches(Matcher):
    """True if a particular scope is detected as active."""

    def __init__(self, scope_string):
        self.scope_string = scope_string

    def __str__(self):
        return "%s(%r)" % (
            self.__class__.__name__,
            self.scope_string)

    def match(self, scope_handler):
        if not scope_handler.lookup(self.scope_string):
            return Mismatch(
                "Handler %r didn't match scope string %r" %
                (scope_handler, self.scope_string))


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


sample_message = """\
From: rae@example.com
To: new@bugs.launchpad.net
Message-Id: <20110107085110.EB4A1181C2A@whatever>
Date: Fri,  7 Jan 2011 02:51:10 -0600 (CST)
Received: by other.example.com (Postfix, from userid 1000)
	id DEADBEEF; Fri,  7 Jan 2011 02:51:10 -0600 (CST)
Received: by lithe (Postfix, from userid 1000)
	id JOB_ID; Fri,  7 Jan 2011 02:51:10 -0600 (CST)
Subject: email scopes don't work

This is awful.
"""

class TestMailScopes(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def make_mail_scopes(self):
        # actual Launchpad uses an ISignedMessage which is a zinterface around
        # an email.message, but the basic one will do
        sample_email_message = email.message_from_string(sample_message)
        scopes = ScopesForMail(sample_email_message)
        return scopes

    def test_ScopesForMail_examines_server(self):
        mail_scopes = self.make_mail_scopes()
        self.assertThat(mail_scopes, MatchesAll(
            MultiScopeContains(ServerScope),
            MultiScopeContains(DefaultScope),
            MultiScopeContains(MailHeaderScope),
            ))

    def test_mail_header_scope(self):
        mail_scopes = self.make_mail_scopes()
        self.assertThat(mail_scopes, MatchesAll(
            ScopeMatches("mail_header:From:rae@example.com")))
        # Regexs are case-sensitive by default, like Python.
        self.assertThat(mail_scopes, Not(
            ScopeMatches("mail_header:From:rae@Example.com")))
        # But header field names are case-insensitive, like rfc2822.
        self.assertThat(mail_scopes, 
            ScopeMatches("mail_header:from:rae@example.com"))
        # Repeated headers check all values.
        self.assertThat(mail_scopes, MatchesAll(
            ScopeMatches(r"mail_header:Received:other\.example\.com"),
            ScopeMatches(r"mail_header:Received:lithe")))
        # Long lines are not unfolded, but you can match them if you turn on
        # DOTALL.
        self.assertThat(mail_scopes,
            ScopeMatches(r"mail_header:Received:(?s)other\.example\.com.*"
                "id DEADBEEF"))
