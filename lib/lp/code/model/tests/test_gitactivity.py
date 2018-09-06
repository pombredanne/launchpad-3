# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git repository activity logs."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from storm.store import Store
from testtools.matchers import MatchesStructure

from lp.code.enums import GitActivityType
from lp.code.interfaces.gitactivity import IGitActivity
from lp.code.model.gitactivity import GitActivity
from lp.services.database.sqlbase import get_transaction_timestamp
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitActivity(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_IGitActivity(self):
        repository = self.factory.makeGitRepository()
        activity = GitActivity(
            repository, repository.owner, GitActivityType.RULE_ADDED)
        verifyObject(IGitActivity, activity)

    def test_properties(self):
        repository = self.factory.makeGitRepository()
        changee = self.factory.makePerson()
        activity = GitActivity(
            repository, repository.owner, GitActivityType.RULE_ADDED,
            changee=changee, old_value={"old": None}, new_value={"new": None})
        now = get_transaction_timestamp(Store.of(activity))
        self.assertThat(activity, MatchesStructure.byEquality(
            repository=repository,
            date_changed=now,
            changer=repository.owner,
            changee=changee,
            what_changed=GitActivityType.RULE_ADDED,
            old_value={"old": None},
            new_value={"new": None}))
