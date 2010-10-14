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
        self.assertEqual(self.task.status, BugTaskStatus.NEW)
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

    def test_owner_can_set_bug_supervisor_statuses(self):
        self.assertEqual(self.task.status, BugTaskStatus.NEW)
        with person_logged_in(self.owner):
            self.task.transitionToStatus(BugTaskStatus.WONTFIX, self.owner)
            self.assertEqual(self.task.status, BugTaskStatus.WONTFIX)
            self.task.transitionToStatus(BugTaskStatus.EXPIRED, self.owner)
            self.assertEqual(self.task.status, BugTaskStatus.EXPIRED)
            self.task.transitionToStatus(BugTaskStatus.TRIAGED, self.owner)
            self.assertEqual(self.task.status, BugTaskStatus.TRIAGED)

    def test_supervisor_can_set_bug_supervisor_statuses(self):
        self.assertEqual(self.task.status, BugTaskStatus.NEW)
        with person_logged_in(self.team_member):
            self.task.transitionToStatus(
                BugTaskStatus.WONTFIX, self.team_member)
            self.assertEqual(self.task.status, BugTaskStatus.WONTFIX)
            self.task.transitionToStatus(
                BugTaskStatus.EXPIRED, self.team_member)
            self.assertEqual(self.task.status, BugTaskStatus.EXPIRED)
            self.task.transitionToStatus(
                BugTaskStatus.TRIAGED, self.team_member)
            self.assertEqual(self.task.status, BugTaskStatus.TRIAGED)

    def test_person_unset_wont_fix_status(self):
        self.assertEqual(self.task.status, BugTaskStatus.NEW)
        with person_logged_in(self.team_member):
            self.task.transitionToStatus(
                BugTaskStatus.WONTFIX, self.team_member)
            self.assertEqual(self.task.status, BugTaskStatus.WONTFIX)
            self.task.transitionToStatus(
                BugTaskStatus.NEW, self.team_member)
            self.assertEqual(self.task.status, BugTaskStatus.NEW)
        with person_logged_in(self.owner):
            self.task.transitionToStatus(
                BugTaskStatus.WONTFIX, self.owner)
            self.assertEqual(self.task.status, BugTaskStatus.WONTFIX)
        person = self.factory.makePerson()
        with person_logged_in(person):
            self.assertRaises(
                UserCannotEditBugTaskStatus, self.task.transitionToStatus,
                BugTaskStatus.CONFIRMED, person)


class TestCanTransitionToStatus(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestCanTransitionToStatus, self).setUp()
        self.user = self.factory.makePerson()
        self.owner = self.factory.makePerson()
        self.team_member = self.factory.makePerson()
        self.supervisor = self.factory.makeTeam(owner=self.owner)
        self.product = self.factory.makeProduct(owner=self.owner)
        self.task = self.factory.makeBugTask(target=self.product)
        self.bug = self.task.bug
        with person_logged_in(self.owner):
            self.supervisor.addMember(self.team_member, self.owner)
            self.product.setBugSupervisor(self.supervisor, self.owner)

    def test_user_cannot_transition_bug_supervisor_statuses(self):
        self.assertEqual(
            self.task.canTransitionToStatus(BugTaskStatus.WONTFIX, self.user),
            False)
        self.assertEqual(
            self.task.canTransitionToStatus(BugTaskStatus.EXPIRED, self.user),
            False)
        self.assertEqual(
            self.task.canTransitionToStatus(BugTaskStatus.TRIAGED, self.user),
            False)

    def test_user_can_transition_to_any_other_status(self):
        self.assertEqual(
            self.task.canTransitionToStatus(BugTaskStatus.NEW, self.user),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.INCOMPLETE, self.user), True)
        self.assertEqual(
            self.task.canTransitionToStatus(BugTaskStatus.OPINION, self.user),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(BugTaskStatus.INVALID, self.user),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.CONFIRMED, self.user), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.INPROGRESS, self.user), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.FIXCOMMITTED, self.user), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.FIXRELEASED, self.user), True)

    def test_bug_supervisor_can_transition_to_any_status(self):
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.WONTFIX, self.supervisor),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.EXPIRED, self.supervisor),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.TRIAGED, self.supervisor),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.NEW, self.supervisor),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.INCOMPLETE, self.supervisor), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.OPINION, self.supervisor),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.INVALID, self.supervisor),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.CONFIRMED, self.supervisor), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.INPROGRESS, self.supervisor), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.FIXCOMMITTED, self.supervisor), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.FIXRELEASED, self.supervisor), True)

    def test_owner_can_transition_to_any_status(self):
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.WONTFIX, self.owner),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.EXPIRED, self.owner),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.TRIAGED, self.owner),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.NEW, self.owner),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.INCOMPLETE, self.owner), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.OPINION, self.owner),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.INVALID, self.owner),
            True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.CONFIRMED, self.owner), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.INPROGRESS, self.owner), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.FIXCOMMITTED, self.owner), True)
        self.assertEqual(
            self.task.canTransitionToStatus(
                BugTaskStatus.FIXRELEASED, self.owner), True)
