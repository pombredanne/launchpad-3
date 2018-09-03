# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git repository access grants."""

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
            # can_force_push implies can_push.
            can_push=Is(True),
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

    def test_destroySelf(self):
        rule = self.factory.makeGitRule()
        grants = [
            self.factory.makeGitGrant(
                rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER,
                can_create=True),
            self.factory.makeGitGrant(rule=rule, can_push=True),
            ]
        with person_logged_in(rule.repository.owner):
            grants[1].destroySelf()
        self.assertThat(rule.grants, MatchesSetwise(Equals(grants[0])))
