# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test vocabularies related to Git access rules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lp.code.enums import GitPermissionType
from lp.code.vocabularies.gitrule import GitPermissionsVocabulary
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitPermissionsVocabulary(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    expected_branch_values = [
        set(),
        {GitPermissionType.CAN_PUSH},
        {GitPermissionType.CAN_CREATE, GitPermissionType.CAN_PUSH},
        {GitPermissionType.CAN_CREATE, GitPermissionType.CAN_PUSH,
         GitPermissionType.CAN_FORCE_PUSH},
        ]
    expected_branch_tokens = [
        "cannot_push", "can_push_existing", "can_push", "can_force_push",
        ]
    expected_tag_values = [
        set(),
        {GitPermissionType.CAN_CREATE},
        {GitPermissionType.CAN_CREATE, GitPermissionType.CAN_PUSH,
         GitPermissionType.CAN_FORCE_PUSH},
        ]
    expected_tag_tokens = ["cannot_create", "can_create", "can_move"]

    def assertVocabularyHasTerms(self, context, expected_values,
                                 expected_tokens):
        vocabulary = GitPermissionsVocabulary(context)
        terms = list(vocabulary)
        self.assertEqual(expected_values, [term.value for term in terms])
        self.assertEqual(expected_tokens, [term.token for term in terms])
        return terms

    def test_ref_branch(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/master"])
        self.assertVocabularyHasTerms(
            ref, self.expected_branch_values, self.expected_branch_tokens)

    def test_ref_tag(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/tags/1.0"])
        self.assertVocabularyHasTerms(
            ref, self.expected_tag_values, self.expected_tag_tokens)

    def test_ref_other(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/other"])
        self.assertVocabularyHasTerms(
            ref, self.expected_branch_values, self.expected_branch_tokens)

    def test_rule_branch(self):
        rule = self.factory.makeGitRule(ref_pattern="refs/heads/*")
        self.assertVocabularyHasTerms(
            rule, self.expected_branch_values, self.expected_branch_tokens)

    def test_rule_tag(self):
        rule = self.factory.makeGitRule(ref_pattern="refs/tags/*")
        self.assertVocabularyHasTerms(
            rule, self.expected_tag_values, self.expected_tag_tokens)

    def test_rule_other(self):
        rule = self.factory.makeGitRule(ref_pattern="refs/*")
        self.assertVocabularyHasTerms(
            rule, self.expected_branch_values, self.expected_branch_tokens)

    def test_rule_grant_branch(self):
        grant = self.factory.makeGitRuleGrant(
            ref_pattern="refs/heads/*", can_create=True, can_push=True)
        self.assertVocabularyHasTerms(
            grant, self.expected_branch_values, self.expected_branch_tokens)

    def test_rule_grant_branch_with_custom(self):
        grant = self.factory.makeGitRuleGrant(
            ref_pattern="refs/heads/*", can_push=True, can_force_push=True)
        expected_values = (
            self.expected_branch_values +
            [{GitPermissionType.CAN_PUSH, GitPermissionType.CAN_FORCE_PUSH}])
        expected_tokens = self.expected_branch_tokens + ["custom"]
        terms = self.assertVocabularyHasTerms(
            grant, expected_values, expected_tokens)
        self.assertEqual(
            "Custom permissions: push, force-push", terms[-1].title)

    def test_rule_grant_tag(self):
        grant = self.factory.makeGitRuleGrant(
            ref_pattern="refs/tags/*", can_create=True)
        self.assertVocabularyHasTerms(
            grant, self.expected_tag_values, self.expected_tag_tokens)

    def test_rule_grant_other(self):
        grant = self.factory.makeGitRuleGrant(ref_pattern="refs/*")
        self.assertVocabularyHasTerms(
            grant, self.expected_branch_values, self.expected_branch_tokens)
