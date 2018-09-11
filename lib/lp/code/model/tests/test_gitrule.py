# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git repository access rules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from storm.store import Store
from testtools.matchers import (
    Equals,
    Is,
    MatchesSetwise,
    MatchesStructure,
    )

from lp.code.enums import GitGranteeType
from lp.code.interfaces.gitrule import IGitRule
from lp.services.database.sqlbase import get_transaction_timestamp
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitRule(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_IGitRule(self):
        rule = self.factory.makeGitRule()
        verifyObject(IGitRule, rule)

    def test_properties(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*",
            creator=member)
        now = get_transaction_timestamp(Store.of(rule))
        self.assertThat(rule, MatchesStructure.byEquality(
            repository=repository,
            ref_pattern="refs/heads/stable/*",
            creator=member,
            date_created=now,
            date_last_modified=now))

    def test_repr(self):
        repository = self.factory.makeGitRepository()
        rule = self.factory.makeGitRule(repository=repository)
        self.assertEqual(
            "<GitRule 'refs/heads/*'> for %r" % repository, repr(rule))

    def test_position(self):
        repository = self.factory.makeGitRepository()
        rules = [
            self.factory.makeGitRule(
                repository=repository,
                ref_pattern=self.factory.getUniqueUnicode(
                    prefix="refs/heads/"))
            for _ in range(2)]
        for i, rule in enumerate(rules):
            self.assertEqual(i, rule.position)

    def test_move(self):
        repository = self.factory.makeGitRepository()
        rules = [
            self.factory.makeGitRule(
                repository=repository,
                ref_pattern=self.factory.getUniqueUnicode(
                    prefix="refs/heads/"))
            for _ in range(4)]
        with person_logged_in(repository.owner):
            self.assertEqual(rules, repository.rules)
            rules[0].move(3)
            self.assertEqual(rules[1:] + [rules[0]], repository.rules)
            rules[0].move(0)
            self.assertEqual(rules, repository.rules)
            rules[2].move(1)
            self.assertEqual(
                [rules[0], rules[2], rules[1], rules[3]], repository.rules)

    def test_move_non_negative(self):
        rule = self.factory.makeGitRule()
        with person_logged_in(rule.repository.owner):
            self.assertRaises(ValueError, rule.move, -1)

    def test_grants(self):
        rule = self.factory.makeGitRule()
        other_rule = self.factory.makeGitRule(
            repository=rule.repository, ref_pattern="refs/heads/stable/*")
        grantees = [self.factory.makePerson() for _ in range(2)]
        self.factory.makeGitGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
            can_create=True)
        self.factory.makeGitGrant(
            rule=rule, grantee=grantees[0], can_push=True)
        self.factory.makeGitGrant(
            rule=rule, grantee=grantees[1], can_force_push=True)
        self.factory.makeGitGrant(
            rule=other_rule, grantee=grantees[0], can_push=True)
        self.assertThat(rule.grants, MatchesSetwise(
            MatchesStructure(
                rule=Equals(rule),
                grantee_type=Equals(GitGranteeType.REPOSITORY_OWNER),
                grantee=Is(None),
                can_create=Is(True),
                can_push=Is(False),
                can_force_push=Is(False)),
            MatchesStructure(
                rule=Equals(rule),
                grantee_type=Equals(GitGranteeType.PERSON),
                grantee=Equals(grantees[0]),
                can_create=Is(False),
                can_push=Is(True),
                can_force_push=Is(False)),
            MatchesStructure(
                rule=Equals(rule),
                grantee_type=Equals(GitGranteeType.PERSON),
                grantee=Equals(grantees[1]),
                can_create=Is(False),
                can_push=Is(False),
                can_force_push=Is(True))))
