# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for visibility of a bug."""

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestPublicBugVisibility(TestCaseWithFactory):
    """Test visibility for a public bug."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestPublicBugVisibility, self).setUp()
        owner = self.factory.makePerson(name="bugowner")
        self.bug = self.factory.makeBug(owner=owner)

    def test_publicBugAnonUser(self):
        # Since the bug is public, the anonymous user can see it.
        self.assertTrue(self.bug.userCanView(None))

    def test_publicBugRegularUser(self):
        # A regular (non-privileged) user can view a public bug.
        user = self.factory.makePerson()
        self.assertTrue(self.bug.userCanView(user))


class TestPrivateBugVisibility(TestCaseWithFactory):
    """Test visibility for a private bug."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestPrivateBugVisibility, self).setUp()
        self.owner = self.factory.makePerson(name="bugowner")
        self.product_owner = self.factory.makePerson(name="productowner")
        self.product = self.factory.makeProduct(
            name="regular-product", owner=self.product_owner)
        self.bug_team = self.factory.makeTeam(
            name="bugteam", owner=self.product.owner)
        self.bug_team_member = self.factory.makePerson(name="bugteammember")
        with person_logged_in(self.product.owner):
            self.bug_team.addMember(self.bug_team_member, self.product.owner)
            self.product.setBugSupervisor(
                bug_supervisor=self.bug_team,
                user=self.product.owner)
        self.bug = self.factory.makeBug(
            owner=self.owner, private=True, product=self.product)

    def test_privateBugRegularUser(self):
        # A regular (non-privileged) user can not view a private bug.
        user = self.factory.makePerson()
        self.assertFalse(self.bug.userCanView(user))

    def test_privateBugOwner(self):
        # The bug submitter may view a private bug.
        self.assertTrue(self.bug.userCanView(self.owner))

    def test_privateBugSupervisor(self):
        # A member of the bug supervisor team can not see a private bug.
        self.assertFalse(self.bug.userCanView(self.bug_team_member))

    def test_privateBugSubscriber(self):
        # A person subscribed to a private bug can see it.
        user = self.factory.makePerson()
        with person_logged_in(self.owner):
            self.bug.subscribe(user, self.owner)
        self.assertTrue(self.bug.userCanView(user))

    def test_privateBugAssignee(self):
        # The bug assignee can see the private bug.
        bug_assignee = self.factory.makePerson(name="bugassignee")
        with person_logged_in(self.product.owner):
            self.bug.default_bugtask.transitionToAssignee(bug_assignee)
        self.assertTrue(self.bug.userCanView(bug_assignee))

    def test_publicBugAnonUser(self):
        # Since the bug is private, the anonymous user cannot see it.
        self.assertFalse(self.bug.userCanView(None))
