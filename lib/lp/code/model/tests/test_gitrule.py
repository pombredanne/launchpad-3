# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git repository access rules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from storm.store import Store
from testtools.matchers import (
    Equals,
    Is,
    MatchesDict,
    MatchesSetwise,
    MatchesStructure,
    )
from zope.event import notify
from zope.interface import providedBy

from lp.code.enums import (
    GitActivityType,
    GitGranteeType,
    )
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

    def test_activity_rule_added(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        self.factory.makeGitRule(repository=repository, creator=member)
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*",
            creator=member)
        self.assertThat(repository.getActivity().first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Is(None),
            what_changed=Equals(GitActivityType.RULE_ADDED),
            old_value=Is(None),
            new_value=MatchesDict({
                "ref_pattern": Equals("refs/heads/stable/*"),
                "position": Equals(1),
                })))

    def test_activity_rule_changed(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        rule_before_modification = Snapshot(rule, providing=providedBy(rule))
        with person_logged_in(member):
            rule.ref_pattern = "refs/heads/other/*"
            notify(ObjectModifiedEvent(
                rule, rule_before_modification, ["ref_pattern"]))
        self.assertThat(repository.getActivity().first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Is(None),
            what_changed=Equals(GitActivityType.RULE_CHANGED),
            old_value=MatchesDict({
                "ref_pattern": Equals("refs/heads/*"),
                "position": Equals(0),
                }),
            new_value=MatchesDict({
                "ref_pattern": Equals("refs/heads/other/*"),
                "position": Equals(0),
                })))

    def test_activity_rule_removed(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        with person_logged_in(member):
            rule.destroySelf(member)
        self.assertThat(repository.getActivity().first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Is(None),
            what_changed=Equals(GitActivityType.RULE_REMOVED),
            old_value=MatchesDict({
                "ref_pattern": Equals("refs/heads/*"),
                "position": Equals(0),
                }),
            new_value=Is(None)))

    def test_activity_rule_moved(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        with person_logged_in(member):
            repository.moveRule(rule, 0, member)
        self.assertThat(repository.getActivity().first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Is(None),
            what_changed=Equals(GitActivityType.RULE_MOVED),
            old_value=MatchesDict({
                "ref_pattern": Equals("refs/heads/stable/*"),
                "position": Equals(1),
                }),
            new_value=MatchesDict({
                "ref_pattern": Equals("refs/heads/stable/*"),
                "position": Equals(0),
                })))

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
            rules[1].destroySelf(repository.owner)
        del rules[1]
        self.assertEqual([0, 1, 2], [rule.position for rule in rules])
        self.assertEqual(rules, list(repository.rules))

    def test_destroySelf_removes_grants(self):
        repository = self.factory.makeGitRepository()
        rule = self.factory.makeGitRule(repository=repository)
        grant = self.factory.makeGitRuleGrant(rule=rule)
        self.assertEqual([grant], list(repository.grants))
        with person_logged_in(repository.owner):
            rule.destroySelf(repository.owner)
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

    def test_activity_grant_added(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        grant = self.factory.makeGitRuleGrant(
            repository=repository, grantor=member, can_push=True)
        self.assertThat(repository.getActivity().first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Equals(grant.grantee),
            what_changed=Equals(GitActivityType.GRANT_ADDED),
            old_value=Is(None),
            new_value=MatchesDict({
                "changee_type": Equals("Person"),
                "ref_pattern": Equals("refs/heads/*"),
                "can_create": Is(False),
                "can_push": Is(True),
                "can_force_push": Is(False),
                })))

    def test_activity_grant_changed(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        grant = self.factory.makeGitRuleGrant(
            repository=repository, grantee=GitGranteeType.REPOSITORY_OWNER,
            can_create=True)
        grant_before_modification = Snapshot(
            grant, providing=providedBy(grant))
        with person_logged_in(member):
            grant.can_create = False
            grant.can_force_push = True
            notify(ObjectModifiedEvent(
                grant, grant_before_modification,
                ["can_create", "can_force_push"]))
        self.assertThat(repository.getActivity().first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Is(None),
            what_changed=Equals(GitActivityType.GRANT_CHANGED),
            old_value=MatchesDict({
                "changee_type": Equals("Repository owner"),
                "ref_pattern": Equals("refs/heads/*"),
                "can_create": Is(True),
                "can_push": Is(False),
                "can_force_push": Is(False),
                }),
            new_value=MatchesDict({
                "changee_type": Equals("Repository owner"),
                "ref_pattern": Equals("refs/heads/*"),
                "can_create": Is(False),
                "can_push": Is(False),
                "can_force_push": Is(True),
                })))

    def test_activity_grant_removed(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        grant = self.factory.makeGitRuleGrant(
            repository=repository, can_create=True, can_push=True)
        grantee = grant.grantee
        with person_logged_in(member):
            grant.destroySelf(member)
        self.assertThat(repository.getActivity().first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Equals(grantee),
            what_changed=Equals(GitActivityType.GRANT_REMOVED),
            old_value=MatchesDict({
                "changee_type": Equals("Person"),
                "ref_pattern": Equals("refs/heads/*"),
                "can_create": Is(True),
                "can_push": Is(True),
                "can_force_push": Is(False),
                }),
            new_value=Is(None)))

    def test_destroySelf(self):
        rule = self.factory.makeGitRule()
        grants = [
            self.factory.makeGitRuleGrant(
                rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
                can_create=True),
            self.factory.makeGitRuleGrant(rule=rule, can_push=True),
            ]
        with person_logged_in(rule.repository.owner):
            grants[1].destroySelf(rule.repository.owner)
        self.assertThat(rule.grants, MatchesSetwise(Equals(grants[0])))
