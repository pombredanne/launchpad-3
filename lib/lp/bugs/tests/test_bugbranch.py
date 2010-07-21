# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug-branch linking from the bugs side."""

__metaclass__ = type

from zope.event import notify

from canonical.testing import DatabaseFunctionalLayer
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lp.bugs.interfaces.bugbranch import IBugBranch
from lp.testing import TestCaseWithFactory


class TestBugBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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
