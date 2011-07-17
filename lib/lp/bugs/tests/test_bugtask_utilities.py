# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugTask utilities."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.interfaces.bugtask import (
    BUG_SUPERVISOR_BUGTASK_STATUSES,
    BugTaskStatus,
    )
from lp.bugs.utilities.bugtask import can_transition_to_status_on_target
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBugTaskUtilities(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_can_transition_to_status_on_target_accepts_valid_changes(self):
        # can_transition_to_status_on_target returns True when a given
        # user has permission to set a given BugTaskStatus for bug tasks
        # on a given bug target.
        user = self.factory.makePerson()
        target = self.factory.makeProduct(
            official_malone=True, owner=user)
        # The user can set any status for a bug on `target`.
        bug = self.factory.makeBug(product=target)
        for status in BugTaskStatus.items:
            self.assertTrue(
                can_transition_to_status_on_target(
                    bug.default_bugtask, target, status, user),
                "User should be able to set status %s" % status.title)

    def test_can_transition_to_status_on_target_rejects_invalid_changes(self):
        # can_transition_to_status_on_target returns False when a user
        # doesn't have permission to set a given status on a given
        # target.
        target = self.factory.makeProduct(
            official_malone=True)
        with person_logged_in(target.owner):
            target.setBugSupervisor(target.owner, target.owner)
        # The user can set any status for a bug on `target`.
        not_the_bug_supervisor = self.factory.makePerson()
        bug = self.factory.makeBug(product=target)
        for status in BUG_SUPERVISOR_BUGTASK_STATUSES:
            self.assertFalse(
                can_transition_to_status_on_target(
                    bug.default_bugtask, target, status,
                    not_the_bug_supervisor),
                "User should not be able to set status %s" % status.title)

    def test_celebrities_can_do_anything(self):
        # can_transition_to_status_on_target will always return True for
        # the Janitor, the Bug Importer or the Bug Watch Updater
        # celebrities.
        target = self.factory.makeProduct(
            official_malone=True)
        with person_logged_in(target.owner):
            target.setBugSupervisor(target.owner, target.owner)
        # The user can set any status for a bug on `target`.
        celebs = (
            getUtility(ILaunchpadCelebrities).janitor,
            getUtility(ILaunchpadCelebrities).bug_watch_updater,
            getUtility(ILaunchpadCelebrities).bug_importer,
            )
        bug = self.factory.makeBug(product=target)
        for celeb in celebs:
            for status in BugTaskStatus.items:
                self.assertTrue(
                    can_transition_to_status_on_target(
                        bug.default_bugtask, target, status,
                        celeb),
                    "Celebrity %s should be able to set status %s" %
                    (celeb.name, status.title))
