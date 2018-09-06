# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git repository access grants."""

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
from lp.code.interfaces.gitgrant import IGitGrant
from lp.services.database.sqlbase import get_transaction_timestamp
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitGrant(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_IGitGrant(self):
        grant = self.factory.makeGitGrant()
        verifyObject(IGitGrant, grant)

    def test_properties_owner(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        rule = self.factory.makeGitRule(owner=owner)
        grant = self.factory.makeGitGrant(
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
        grant = self.factory.makeGitGrant(
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
        grant = self.factory.makeGitGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
            can_create=True, can_push=True)
        self.assertEqual(
            "<GitGrant [create, push] to repository owner> for %r" % rule,
            repr(grant))

    def test_repr_person(self):
        rule = self.factory.makeGitRule()
        grantee = self.factory.makePerson()
        grant = self.factory.makeGitGrant(
            rule=rule, grantee=grantee, can_push=True)
        self.assertEqual(
            "<GitGrant [push] to ~%s> for %r" % (grantee.name, rule),
            repr(grant))

    def test_activity_grant_added(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        grant = self.factory.makeGitGrant(
            repository=repository, grantor=member, can_push=True)
        self.assertThat(repository.activity.first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Equals(grant.grantee),
            what_changed=Equals(GitActivityType.GRANT_ADDED),
            old_value=Is(None),
            new_value=MatchesDict({
                "grantee_type": Equals("Person"),
                "can_create": Is(False),
                "can_push": Is(True),
                "can_force_push": Is(False),
                })))

    def test_activity_grant_changed(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        grant = self.factory.makeGitGrant(
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
        self.assertThat(repository.activity.first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Is(None),
            what_changed=Equals(GitActivityType.GRANT_CHANGED),
            old_value=MatchesDict({
                "grantee_type": Equals("Repository owner"),
                "can_create": Is(True),
                "can_push": Is(False),
                "can_force_push": Is(False),
                }),
            new_value=MatchesDict({
                "grantee_type": Equals("Repository owner"),
                "can_create": Is(False),
                "can_push": Is(False),
                "can_force_push": Is(True),
                })))

    def test_activity_grant_removed(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        grant = self.factory.makeGitGrant(
            repository=repository, can_create=True, can_push=True)
        grantee = grant.grantee
        with person_logged_in(member):
            grant.destroySelf(member)
        self.assertThat(repository.activity.first(), MatchesStructure(
            repository=Equals(repository),
            changer=Equals(member),
            changee=Equals(grantee),
            what_changed=Equals(GitActivityType.GRANT_REMOVED),
            old_value=MatchesDict({
                "grantee_type": Equals("Person"),
                "can_create": Is(True),
                "can_push": Is(True),
                "can_force_push": Is(False),
                }),
            new_value=Is(None)))

    def test_destroySelf(self):
        rule = self.factory.makeGitRule()
        grants = [
            self.factory.makeGitGrant(
                rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
                can_create=True),
            self.factory.makeGitGrant(rule=rule, can_push=True),
            ]
        with person_logged_in(rule.repository.owner):
            grants[1].destroySelf(rule.repository.owner)
        self.assertThat(rule.grants, MatchesSetwise(Equals(grants[0])))
