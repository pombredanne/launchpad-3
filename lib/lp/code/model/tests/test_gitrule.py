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
from lp.code.interfaces.gitrule import (
    IGitRule,
    IGitRuleGrant,
    )
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

    def test_is_exact(self):
        repository = self.factory.makeGitRepository()
        for ref_pattern, is_exact in (
                ("refs/heads/master", True),
                ("refs/heads/*", False),
                # XXX cjwatson 2018-09-25: We may want to support ? and
                # [...] in the future, since they're potentially useful and
                # don't collide with valid ref names.
                ("refs/heads/?", True),
                ("refs/heads/[abc]", True),
                (r"refs/heads/.\$", True),
                ):
            self.assertEqual(
                is_exact,
                self.factory.makeGitRule(
                    repository=repository,
                    ref_pattern=ref_pattern).is_exact)

    def test_grants(self):
        rule = self.factory.makeGitRule()
        other_rule = self.factory.makeGitRule(
            repository=rule.repository, ref_pattern="refs/heads/stable/*")
        grantees = [self.factory.makePerson() for _ in range(2)]
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
            can_create=True)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantees[0], can_push=True)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantees[1], can_force_push=True)
        self.factory.makeGitRuleGrant(
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

    def test_destroySelf(self):
        repository = self.factory.makeGitRepository()
        rules = [
            self.factory.makeGitRule(
                repository=repository,
                ref_pattern=self.factory.getUniqueUnicode(
                    prefix="refs/heads/"))
            for _ in range(4)]
        self.assertEqual([0, 1, 2, 3], [rule.position for rule in rules])
        self.assertEqual(rules, list(repository.rules))
        with person_logged_in(repository.owner):
            rules[1].destroySelf()
        del rules[1]
        self.assertEqual([0, 1, 2], [rule.position for rule in rules])
        self.assertEqual(rules, list(repository.rules))

    def test_destroySelf_removes_grants(self):
        repository = self.factory.makeGitRepository()
        rule = self.factory.makeGitRule(repository=repository)
        grant = self.factory.makeGitRuleGrant(rule=rule)
        self.assertEqual([grant], list(repository.grants))
        with person_logged_in(repository.owner):
            rule.destroySelf()
        self.assertEqual([], list(repository.grants))


class TestGitRuleGrant(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_IGitRuleGrant(self):
        grant = self.factory.makeGitRuleGrant()
        verifyObject(IGitRuleGrant, grant)

    def test_properties_owner(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        rule = self.factory.makeGitRule(owner=owner)
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER, grantor=member,
            can_create=True, can_force_push=True)
        now = get_transaction_timestamp(Store.of(grant))
        self.assertThat(grant, MatchesStructure(
            repository=Equals(rule.repository),
            rule=Equals(rule),
            grantee_type=Equals(GitGranteeType.REPOSITORY_OWNER),
            grantee=Is(None),
            can_create=Is(True),
            can_push=Is(False),
            can_force_push=Is(True),
            grantor=Equals(member),
            date_created=Equals(now),
            date_last_modified=Equals(now)))

    def test_properties_person(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        rule = self.factory.makeGitRule(owner=owner)
        grantee = self.factory.makePerson()
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantee, grantor=member, can_push=True)
        now = get_transaction_timestamp(Store.of(rule))
        self.assertThat(grant, MatchesStructure(
            repository=Equals(rule.repository),
            rule=Equals(rule),
            grantee_type=Equals(GitGranteeType.PERSON),
            grantee=Equals(grantee),
            can_create=Is(False),
            can_push=Is(True),
            can_force_push=Is(False),
            grantor=Equals(member),
            date_created=Equals(now),
            date_last_modified=Equals(now)))

    def test_repr_owner(self):
        rule = self.factory.makeGitRule()
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
            can_create=True, can_push=True)
        self.assertEqual(
            "<GitRuleGrant [create, push] to repository owner> for %r" % rule,
            repr(grant))

    def test_repr_person(self):
        rule = self.factory.makeGitRule()
        grantee = self.factory.makePerson()
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantee, can_push=True)
        self.assertEqual(
            "<GitRuleGrant [push] to ~%s> for %r" % (grantee.name, rule),
            repr(grant))

    def test_destroySelf(self):
        rule = self.factory.makeGitRule()
        grants = [
            self.factory.makeGitRuleGrant(
                rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
                can_create=True),
            self.factory.makeGitRuleGrant(rule=rule, can_push=True),
            ]
        with person_logged_in(rule.repository.owner):
            grants[1].destroySelf()
        self.assertThat(rule.grants, MatchesSetwise(Equals(grants[0])))
