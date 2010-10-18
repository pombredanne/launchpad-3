# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug task status transitions."""

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.interfaces.bugtask import UserCannotEditBugTaskStatus
from lp.bugs.model.bugtask import BugTaskStatus
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBugTaskStatusUserRestrictions(TestCaseWithFactory):
    """Test bugtask status restrictions for a regular logged in user."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # We can work with a project only here, since both project
        # and distribution use the same methods on IBugTask.
        super(TestBugTaskStatusUserRestrictions, self).setUp()
        self.user = self.factory.makePerson()
        self.task = self.factory.makeBugTask()

    def test_person_cannot_set_bug_supervisor_statuses(self):
        # A regular user should not be able to set statuses in
        # BUG_SUPERVISOR_BUGTASK_STATUSES.
        self.assertEqual(self.task.status, BugTaskStatus.NEW)
        with person_logged_in(self.user):
            self.assertRaises(
                UserCannotEditBugTaskStatus, self.task.transitionToStatus,
                BugTaskStatus.WONTFIX, self.user)
            self.assertRaises(
                UserCannotEditBugTaskStatus, self.task.transitionToStatus,
                BugTaskStatus.EXPIRED, self.user)
            self.assertRaises(
                UserCannotEditBugTaskStatus, self.task.transitionToStatus,
                BugTaskStatus.TRIAGED, self.user)

    def test_unset_wont_fix_status(self):
        # A regular user should not be able to transition a bug away
        # from Won't Fix.
        removeSecurityProxy(self.task).status = BugTaskStatus.WONTFIX
        with person_logged_in(self.user):
            self.assertRaises(
                UserCannotEditBugTaskStatus, self.task.transitionToStatus,
                BugTaskStatus.CONFIRMED, self.user)



class TestBugTaskStatusSetting(TestCaseWithFactory):
    """Tests to ensure restricted status changes are enforced."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # We can work with a project only here, since both project
        # and distribution use the same methods on IBugTask.
        super(TestBugTaskStatusSetting, self).setUp()
        self.owner = self.factory.makePerson()
        self.team_member = self.factory.makePerson()
        self.supervisor = self.factory.makeTeam(members=[self.team_member])
        self.product = self.factory.makeProduct(owner=self.owner)
        self.task = self.factory.makeBugTask(target=self.product)
        self.bug = self.task.bug
        with person_logged_in(self.owner):
            self.product.setBugSupervisor(self.supervisor, self.supervisor)

    def test_owner_can_set_bug_supervisor_statuses(self):
        # Project registrant should be able to set statuses in
        # BUG_SUPERVISOR_BUGTASK_STATUSES.
        self.assertEqual(self.task.status, BugTaskStatus.NEW)
        with person_logged_in(self.owner):
            self.task.transitionToStatus(BugTaskStatus.WONTFIX, self.owner)
            self.assertEqual(self.task.status, BugTaskStatus.WONTFIX)
            self.task.transitionToStatus(BugTaskStatus.EXPIRED, self.owner)
            self.assertEqual(self.task.status, BugTaskStatus.EXPIRED)
            self.task.transitionToStatus(BugTaskStatus.TRIAGED, self.owner)
            self.assertEqual(self.task.status, BugTaskStatus.TRIAGED)

    def test_supervisor_can_set_bug_supervisor_statuses(self):
        # Bug supervisor should be able to set statuses in
        # BUG_SUPERVISOR_BUGTASK_STATUSES.
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



class TestCanTransitionToStatus(TestCaseWithFactory):
    """Tests for BugTask.canTransitionToStatus."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # We can work with a project only here, since both project
        # and distribution use the same methods on IBugTask.
        super(TestCanTransitionToStatus, self).setUp()
        self.user = self.factory.makePerson()
        self.owner = self.factory.makePerson()
        self.team_member = self.factory.makePerson()
        self.supervisor = self.factory.makeTeam(members=[self.team_member])
        self.product = self.factory.makeProduct(owner=self.owner)
        self.task = self.factory.makeBugTask(target=self.product)
        self.bug = self.task.bug
        with person_logged_in(self.owner):
            self.product.setBugSupervisor(self.supervisor, self.supervisor)

    def test_user_cannot_transition_bug_supervisor_statuses(self):
        # A regular user is not allowed to transition to
        # BUG_SUPERVISOR_BUGTASK_STATUSES.
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
        # A regular user should be able to transition to any status
        # other than those in BUG_SUPERVISOR_BUGTASK_STATUSES.
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
        # A bug supervisor can transition to any status.
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
        # An owner can transition to any status.
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

    def test_user_cannot_transition_from_wont_fix(self):
        # A regular user cannot transition away from Won't Fix.
        with person_logged_in(self.owner):
            self.task.transitionToStatus(BugTaskStatus.WONTFIX, self.owner)
        self.assertEqual(self.task.status, BugTaskStatus.WONTFIX)
        self.assertEqual(
            self.task.canTransitionToStatus(BugTaskStatus.NEW, self.user),
            False)
