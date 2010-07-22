# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug-branch linking from the bugs side."""

__metaclass__ = type

from zope.event import notify

from canonical.testing import DatabaseFunctionalLayer
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lp.bugs.model.bugbranch import BugBranch, BugBranchSet
from lp.bugs.interfaces.bugbranch import IBugBranch, IBugBranchSet
from lp.testing import TestCase, TestCaseWithFactory


class TestBugBranchSet(TestCase):

    layer = DatabaseFunctionalLayer

    def test_bugbranchset_provides_IBugBranchSet(self):
        # BugBranchSet objects provide IBugBranchSet.
        self.assertProvides(BugBranchSet(), IBugBranchSet)


class TestBugBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugBranch, self).setUp()
        # Bug branch linking is generally available to any logged in user.
        self.factory.loginAsAnyone()

    def test_bugbranch_provides_IBugBranch(self):
        # BugBranch objects provide IBugBranch.
        bug_branch = BugBranch(
            branch=self.factory.makeBranch(), bug=self.factory.makeBug(),
            registrant=self.factory.makePerson())
        self.assertProvides(bug_branch, IBugBranch)

    def test_linkBranch_returns_IBugBranch(self):
        # Bug.linkBranch returns an IBugBranch linking the bug to the branch.
        bug = self.factory.makeBug()
        branch = self.factory.makeBranch()
        registrant = self.factory.makePerson()
        bug_branch = bug.linkBranch(branch, registrant)
        self.assertEqual(branch, bug_branch.branch)
        self.assertEqual(bug, bug_branch.bug)
        self.assertEqual(registrant, bug_branch.registrant)

    def test_bug_start_with_no_linked_branches(self):
        # Bugs have a linked_branches attribute which is initially an empty
        # collection.
        bug = self.factory.makeBug()
        self.assertEqual([], list(bug.linked_branches))

    def test_linkBranch_adds_to_linked_branches(self):
        # Bug.linkBranch populates the Bug.linked_branches with the created
        # BugBranch object.
        bug = self.factory.makeBug()
        branch = self.factory.makeBranch()
        bug_branch = bug.linkBranch(branch, self.factory.makePerson())
        self.assertEqual([bug_branch], list(bug.linked_branches))

    def test_linking_branch_twice_returns_same_IBugBranch(self):
        # Calling Bug.linkBranch twice with the same parameters returns the
        # same object.
        bug = self.factory.makeBug()
        branch = self.factory.makeBranch()
        bug_branch = bug.linkBranch(branch, self.factory.makePerson())
        bug_branch_2 = bug.linkBranch(branch, self.factory.makePerson())
        self.assertEqual(bug_branch, bug_branch_2)

    def test_linking_branch_twice_different_registrants(self):
        # Calling Bug.linkBranch twice with the branch but different
        # registrants returns the existing bug branch object rather than
        # creating a new one.
        bug = self.factory.makeBug()
        branch = self.factory.makeBranch()
        bug_branch = bug.linkBranch(branch, self.factory.makePerson())
        bug_branch_2 = bug.linkBranch(branch, self.factory.makePerson())
        self.assertEqual(bug_branch, bug_branch_2)

    def test_bug_has_no_branches(self):
        # Bug.hasBranch returns False for any branch that it is not linked to.
        bug = self.factory.makeBug()
        self.assertFalse(bug.hasBranch(self.factory.makeBranch()))

    def test_bug_has_branch(self):
        # Bug.hasBranch returns False for any branch that it is linked to.
        bug = self.factory.makeBug()
        branch = self.factory.makeBranch()
        bug.linkBranch(branch, self.factory.makePerson())
        self.assertTrue(bug.hasBranch(branch))

    def test_adding_branch_changes_date_last_updated(self):
        # Adding a branch to a bug changes IBug.date_last_updated.
        bug = self.factory.makeBug()
        last_updated = bug.date_last_updated
        branch = self.factory.makeBranch()
        self.factory.loginAsAnyone()
        bug.linkBranch(branch, self.factory.makePerson())
        self.assertTrue(bug.date_last_updated > last_updated)

    def test_editing_branch_changes_date_last_updated(self):
        # Editing a branch linked to a bug changes IBug.date_last_updated.
        bug = self.factory.makeBug()
        branch = self.factory.makeBranch()
        registrant = self.factory.makePerson()
        self.factory.loginAsAnyone()
        branch_link = bug.linkBranch(branch, registrant)
        last_updated = bug.date_last_updated
        # Rather than modifying the bugbranch link directly, we emit an
        # ObjectModifiedEvent, which is triggered whenever the object is
        # edited.

        # XXX: jml has no idea why we do this. Accessing any attribute of the
        # returned BugBranch appears to be forbidden, and there's no evidence
        # that the object is even editable at all.
        before_modification = Snapshot(branch_link, providing=IBugBranch)
        # XXX: WTF? IBugBranch doesn't even have a status attribute? jml.
        event = ObjectModifiedEvent(
            branch_link, before_modification, ['status'])
        notify(event)
        self.assertTrue(bug.date_last_updated > last_updated)
