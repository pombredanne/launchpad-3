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
    MatchesListwise,
    MatchesSetwise,
    MatchesStructure,
    )
import transaction
from zope.event import notify
from zope.interface import providedBy
from zope.security.proxy import removeSecurityProxy

from lp.code.enums import (
    GitActivityType,
    GitGranteeType,
    GitPermissionType,
    )
from lp.code.interfaces.gitrule import (
    IGitNascentRuleGrant,
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
            "<GitRule 'refs/heads/*' for %s>" % repository.unique_name,
            repr(rule))

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

    def test_addGrant_refuses_inconsistent_permissions(self):
        rule = self.factory.makeGitRule()
        with person_logged_in(rule.repository.owner):
            self.assertRaises(
                AssertionError, rule.addGrant,
                GitGranteeType.REPOSITORY_OWNER, rule.repository.owner,
                can_create=True, can_push=True,
                permissions={GitPermissionType.CAN_CREATE})

    def test_addGrant_broken_down_permissions(self):
        rule = self.factory.makeGitRule()
        with person_logged_in(rule.repository.owner):
            grant = rule.addGrant(
                GitGranteeType.REPOSITORY_OWNER, rule.repository.owner,
                can_create=True, can_push=True)
        self.assertThat(grant, MatchesStructure(
            rule=Equals(rule),
            grantee_type=Equals(GitGranteeType.REPOSITORY_OWNER),
            grantee=Is(None),
            grantor=Equals(rule.repository.owner),
            can_create=Is(True),
            can_push=Is(True),
            can_force_push=Is(False)))

    def test_addGrant_combined_permissions(self):
        rule = self.factory.makeGitRule()
        with person_logged_in(rule.repository.owner):
            grant = rule.addGrant(
                GitGranteeType.REPOSITORY_OWNER, rule.repository.owner,
                permissions={
                    GitPermissionType.CAN_CREATE, GitPermissionType.CAN_PUSH,
                    })
        self.assertThat(grant, MatchesStructure(
            rule=Equals(rule),
            grantee_type=Equals(GitGranteeType.REPOSITORY_OWNER),
            grantee=Is(None),
            grantor=Equals(rule.repository.owner),
            can_create=Is(True),
            can_push=Is(True),
            can_force_push=Is(False)))

    def test__validateGrants_ok(self):
        rule = self.factory.makeGitRule()
        grants = [
            IGitNascentRuleGrant({
                "grantee_type": GitGranteeType.REPOSITORY_OWNER,
                "can_force_push": True,
                }),
            ]
        removeSecurityProxy(rule)._validateGrants(grants)

    def test__validateGrants_grantee_type_person_but_no_grantee(self):
        rule = self.factory.makeGitRule(ref_pattern="refs/heads/*")
        grants = [
            IGitNascentRuleGrant({
                "grantee_type": GitGranteeType.PERSON,
                "can_force_push": True,
                }),
            ]
        self.assertRaisesWithContent(
            ValueError,
            "Permission grant for refs/heads/* has grantee_type 'Person' but "
            "no grantee",
            removeSecurityProxy(rule)._validateGrants, grants)

    def test__validateGrants_grantee_but_wrong_grantee_type(self):
        rule = self.factory.makeGitRule(ref_pattern="refs/heads/*")
        grantee = self.factory.makePerson()
        grants = [
            IGitNascentRuleGrant({
                "grantee_type": GitGranteeType.REPOSITORY_OWNER,
                "grantee": grantee,
                "can_force_push": True,
                }),
            ]
        self.assertRaisesWithContent(
            ValueError,
            "Permission grant for refs/heads/* has grantee_type "
            "'Repository owner', contradicting grantee ~%s" % grantee.name,
            removeSecurityProxy(rule)._validateGrants, grants)

    def test_setGrants_add(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        rule = self.factory.makeGitRule(owner=owner)
        grantee = self.factory.makePerson()
        removeSecurityProxy(rule.repository.getActivity()).remove()
        with person_logged_in(member):
            rule.setGrants([
                IGitNascentRuleGrant({
                    "grantee_type": GitGranteeType.REPOSITORY_OWNER,
                    "can_create": True,
                    "can_force_push": True,
                    }),
                IGitNascentRuleGrant({
                    "grantee_type": GitGranteeType.PERSON,
                    "grantee": grantee,
                    "can_push": True,
                    }),
                ], member)
        self.assertThat(rule.grants, MatchesSetwise(
            MatchesStructure(
                rule=Equals(rule),
                grantor=Equals(member),
                grantee_type=Equals(GitGranteeType.REPOSITORY_OWNER),
                grantee=Is(None),
                can_create=Is(True),
                can_push=Is(False),
                can_force_push=Is(True)),
            MatchesStructure(
                rule=Equals(rule),
                grantor=Equals(member),
                grantee_type=Equals(GitGranteeType.PERSON),
                grantee=Equals(grantee),
                can_create=Is(False),
                can_push=Is(True),
                can_force_push=Is(False))))
        self.assertThat(list(rule.repository.getActivity()), MatchesListwise([
            MatchesStructure(
                repository=Equals(rule.repository),
                changer=Equals(member),
                changee=Equals(grantee),
                what_changed=Equals(GitActivityType.GRANT_ADDED),
                old_value=Is(None),
                new_value=MatchesDict({
                    "changee_type": Equals("Person"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(False),
                    "can_push": Is(True),
                    "can_force_push": Is(False),
                    })),
            MatchesStructure(
                repository=Equals(rule.repository),
                changer=Equals(member),
                changee=Is(None),
                what_changed=Equals(GitActivityType.GRANT_ADDED),
                old_value=Is(None),
                new_value=MatchesDict({
                    "changee_type": Equals("Repository owner"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(True),
                    "can_push": Is(False),
                    "can_force_push": Is(True),
                    })),
            ]))

    def test_setGrants_modify(self):
        owner = self.factory.makeTeam()
        members = [
            self.factory.makePerson(member_of=[owner]) for _ in range(2)]
        rule = self.factory.makeGitRule(owner=owner)
        grantees = [self.factory.makePerson() for _ in range(2)]
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
            grantor=members[0], can_create=True)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantees[0], grantor=members[0], can_push=True)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantees[1], grantor=members[0],
            can_force_push=True)
        date_created = get_transaction_timestamp(Store.of(rule))
        transaction.commit()
        removeSecurityProxy(rule.repository.getActivity()).remove()
        with person_logged_in(members[1]):
            rule.setGrants([
                IGitNascentRuleGrant({
                    "grantee_type": GitGranteeType.REPOSITORY_OWNER,
                    "can_force_push": True,
                    }),
                IGitNascentRuleGrant({
                    "grantee_type": GitGranteeType.PERSON,
                    "grantee": grantees[1],
                    "can_create": True,
                    }),
                IGitNascentRuleGrant({
                    "grantee_type": GitGranteeType.PERSON,
                    "grantee": grantees[0],
                    "can_push": True,
                    "can_force_push": True,
                    }),
                ], members[1])
            date_modified = get_transaction_timestamp(Store.of(rule))
        self.assertThat(rule.grants, MatchesSetwise(
            MatchesStructure(
                rule=Equals(rule),
                grantor=Equals(members[0]),
                grantee_type=Equals(GitGranteeType.REPOSITORY_OWNER),
                grantee=Is(None),
                can_create=Is(False),
                can_push=Is(False),
                can_force_push=Is(True),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_modified)),
            MatchesStructure(
                rule=Equals(rule),
                grantor=Equals(members[0]),
                grantee_type=Equals(GitGranteeType.PERSON),
                grantee=Equals(grantees[0]),
                can_create=Is(False),
                can_push=Is(True),
                can_force_push=Is(True),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_modified)),
            MatchesStructure(
                rule=Equals(rule),
                grantor=Equals(members[0]),
                grantee_type=Equals(GitGranteeType.PERSON),
                grantee=Equals(grantees[1]),
                can_create=Is(True),
                can_push=Is(False),
                can_force_push=Is(False),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_modified))))
        self.assertThat(list(rule.repository.getActivity()), MatchesListwise([
            MatchesStructure(
                repository=Equals(rule.repository),
                changer=Equals(members[1]),
                changee=Equals(grantees[0]),
                what_changed=Equals(GitActivityType.GRANT_CHANGED),
                old_value=MatchesDict({
                    "changee_type": Equals("Person"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(False),
                    "can_push": Is(True),
                    "can_force_push": Is(False),
                    }),
                new_value=MatchesDict({
                    "changee_type": Equals("Person"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(False),
                    "can_push": Is(True),
                    "can_force_push": Is(True),
                    })),
            MatchesStructure(
                repository=Equals(rule.repository),
                changer=Equals(members[1]),
                changee=Equals(grantees[1]),
                what_changed=Equals(GitActivityType.GRANT_CHANGED),
                old_value=MatchesDict({
                    "changee_type": Equals("Person"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(False),
                    "can_push": Is(False),
                    "can_force_push": Is(True),
                    }),
                new_value=MatchesDict({
                    "changee_type": Equals("Person"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(True),
                    "can_push": Is(False),
                    "can_force_push": Is(False),
                    })),
            MatchesStructure(
                repository=Equals(rule.repository),
                changer=Equals(members[1]),
                changee=Is(None),
                what_changed=Equals(GitActivityType.GRANT_CHANGED),
                old_value=MatchesDict({
                    "changee_type": Equals("Repository owner"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(True),
                    "can_push": Is(False),
                    "can_force_push": Is(False),
                    }),
                new_value=MatchesDict({
                    "changee_type": Equals("Repository owner"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(False),
                    "can_push": Is(False),
                    "can_force_push": Is(True),
                    })),
            ]))

    def test_setGrants_remove(self):
        owner = self.factory.makeTeam()
        members = [
            self.factory.makePerson(member_of=[owner]) for _ in range(2)]
        rule = self.factory.makeGitRule(owner=owner)
        grantees = [self.factory.makePerson() for _ in range(2)]
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
            grantor=members[0], can_create=True)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantees[0], grantor=members[0], can_push=True)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantees[1], grantor=members[0],
            can_force_push=True)
        date_created = get_transaction_timestamp(Store.of(rule))
        transaction.commit()
        removeSecurityProxy(rule.repository.getActivity()).remove()
        with person_logged_in(members[1]):
            rule.setGrants([
                IGitNascentRuleGrant({
                    "grantee_type": GitGranteeType.PERSON,
                    "grantee": grantees[0],
                    "can_push": True,
                    }),
                ], members[1])
        self.assertThat(rule.grants, MatchesSetwise(
            MatchesStructure(
                rule=Equals(rule),
                grantor=Equals(members[0]),
                grantee_type=Equals(GitGranteeType.PERSON),
                grantee=Equals(grantees[0]),
                can_create=Is(False),
                can_push=Is(True),
                can_force_push=Is(False),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_created))))
        self.assertThat(list(rule.repository.getActivity()), MatchesSetwise(
            MatchesStructure(
                repository=Equals(rule.repository),
                changer=Equals(members[1]),
                changee=Is(None),
                what_changed=Equals(GitActivityType.GRANT_REMOVED),
                old_value=MatchesDict({
                    "changee_type": Equals("Repository owner"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(True),
                    "can_push": Is(False),
                    "can_force_push": Is(False),
                    }),
                new_value=Is(None)),
            MatchesStructure(
                repository=Equals(rule.repository),
                changer=Equals(members[1]),
                changee=Equals(grantees[1]),
                what_changed=Equals(GitActivityType.GRANT_REMOVED),
                old_value=MatchesDict({
                    "changee_type": Equals("Person"),
                    "ref_pattern": Equals(rule.ref_pattern),
                    "can_create": Is(False),
                    "can_push": Is(False),
                    "can_force_push": Is(True),
                    }),
                new_value=Is(None)),
            ))

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
            "<GitRuleGrant [create, push] to repository owner for %s:%s>" % (
                rule.repository.unique_name, rule.ref_pattern),
            repr(grant))

    def test_repr_person(self):
        rule = self.factory.makeGitRule()
        grantee = self.factory.makePerson()
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=grantee, can_push=True)
        self.assertEqual(
            "<GitRuleGrant [push] to ~%s for %s:%s>" % (
                grantee.name, rule.repository.unique_name, rule.ref_pattern),
            repr(grant))

    def test_permissions(self):
        grant = self.factory.makeGitRuleGrant(can_push=True)
        self.assertEqual(
            frozenset({GitPermissionType.CAN_PUSH}), grant.permissions)
        new_permissions = {
            GitPermissionType.CAN_CREATE, GitPermissionType.CAN_FORCE_PUSH}
        with person_logged_in(grant.repository.owner):
            grant.permissions = new_permissions
        self.assertEqual(frozenset(new_permissions), grant.permissions)
        self.assertTrue(grant.can_create)
        self.assertFalse(grant.can_push)
        self.assertTrue(grant.can_force_push)

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
