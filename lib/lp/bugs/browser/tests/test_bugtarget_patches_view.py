# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import unittest

from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.browser.bugtarget import BugsPatchesView
from lp.bugs.browser.bugtask import BugListingPortletStatsView
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.testing import TestCaseWithFactory


DISPLAY_BUG_STATUS_FOR_PATCHES = {
    BugTaskStatus.NEW:  True,
    BugTaskStatus.INCOMPLETE: True,
    BugTaskStatus.INVALID: False,
    BugTaskStatus.WONTFIX: False,
    BugTaskStatus.CONFIRMED: True,
    BugTaskStatus.TRIAGED: True,
    BugTaskStatus.INPROGRESS: True,
    BugTaskStatus.FIXCOMMITTED: True,
    BugTaskStatus.FIXRELEASED: False,
    BugTaskStatus.UNKNOWN: False,
    BugTaskStatus.EXPIRED: False
    }


class TestBugTargetPatchCountBase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugTargetPatchCountBase, self).setUp()
        login('foo.bar@canonical.com')
        self.product = self.factory.makeProduct()

    def makeBugWithPatch(self, status):
        bug = self.factory.makeBug(
            product=self.product, owner=self.product.owner)
        self.factory.makeBugAttachment(bug=bug, is_patch=True)
        bug.default_bugtask.transitionToStatus(status, user=bug.owner)


class TestBugTargetPatchView(TestBugTargetPatchCountBase):

    def setUp(self):
        super(TestBugTargetPatchView, self).setUp()
        self.view = BugsPatchesView(self.product, LaunchpadTestRequest())

    def test_status_of_bugs_with_patches_shown(self):
        # Bugs with patches that have the status FIXRELEASED, INVALID,
        # WONTFIX, UNKNOWN, EXPIRED are not shown in the +patches view; all
        # other bugs are shown.
        number_of_bugs_shown = 0
        for bugtask_status in DISPLAY_BUG_STATUS_FOR_PATCHES:
            if DISPLAY_BUG_STATUS_FOR_PATCHES[bugtask_status]:
                number_of_bugs_shown += 1
            self.makeBugWithPatch(bugtask_status)
            batched_tasks = self.view.batchedPatchTasks()
            self.assertEqual(
                batched_tasks.batch.listlength, number_of_bugs_shown,
                "Unexpected number of bugs with patches displayed for status "
                "%s" % bugtask_status)


class TestBugListingPortletStatsView(TestBugTargetPatchCountBase):

    def setUp(self):
        super(TestBugListingPortletStatsView, self).setUp()
        self.view = BugListingPortletStatsView(
            self.product, LaunchpadTestRequest())

    def test_bugs_with_patches_count(self):
        # Bugs with patches that have the status FIXRELEASED, INVALID,
        # WONTFIX, or UNKNOWN are not counted in
        # BugListingPortletStatsView.bugs_with_patches_count, bugs
        # with all other statuses are counted.
        number_of_bugs_shown = 0
        for bugtask_status in DISPLAY_BUG_STATUS_FOR_PATCHES:
            if DISPLAY_BUG_STATUS_FOR_PATCHES[bugtask_status]:
                number_of_bugs_shown += 1
            self.makeBugWithPatch(bugtask_status)
            self.assertEqual(
                self.view.bugs_with_patches_count, number_of_bugs_shown,
                "Unexpected number of bugs with patches displayed for status "
                "%s" % bugtask_status)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBugTargetPatchView))
    suite.addTest(unittest.makeSuite(TestBugListingPortletStatsView))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
