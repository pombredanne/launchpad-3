# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for setting bug task status."""

__metaclass__ = type

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.interfaces.bugtask import UserCannotEditBugTaskStatus
from lp.bugs.model.bugtask import BugTaskStatus
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBugTaskStatusSetting(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugTaskStatusSetting, self).setUp()
        self.owner = self.factory.makePerson()
        self.team_member = self.factory.makePerson()
        self.supervisor = self.factory.makeTeam(owner=self.owner)
        self.product = self.factory.makeProduct(owner=self.owner)
        self.task = self.factory.makeBugTask(target=self.product)
        self.bug = self.task.bug
        with person_logged_in(self.owner):
            self.supervisor.addMember(self.team_member, self.owner)
            self.product.setBugSupervisor(self.supervisor, self.owner)

    def test_person_cannot_set_bug_supervisor_statuses(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            self.assertRaises(
                UserCannotEditBugTaskStatus, self.task.transitionToStatus,
                BugTaskStatus.WONTFIX, person)
            self.assertRaises(
                UserCannotEditBugTaskStatus, self.task.transitionToStatus,
                BugTaskStatus.EXPIRED, person)
            self.assertRaises(
                UserCannotEditBugTaskStatus, self.task.transitionToStatus,
                BugTaskStatus.TRIAGED, person)

