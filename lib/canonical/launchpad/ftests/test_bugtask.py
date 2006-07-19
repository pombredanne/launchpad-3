# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bugtask related tests that are too complex to be readable as doctests."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.interfaces import (
    BugTaskSearchParams, IBugSet, IDistributionSet, RESOLVED_BUGTASK_STATUSES,
    UNRESOLVED_BUGTASK_STATUSES)
from canonical.launchpad.searchbuilder import any
from canonical.lp.dbschema import BugTaskStatus


class BugTaskSearchBugsElsewhereTest(LaunchpadFunctionalTestCase):
    """Tests for searching bugs filtering on related bug tasks.

    It also acts as a helper class, which makes related doctests more
    readable, since they can use methods from this class."""

    def __init__(self, methodName='runTest', helper_only=False):
        """If helper_only is True, set up it only as a helper class."""
        if not helper_only:
            LaunchpadFunctionalTestCase.__init__(self, methodName=methodName)

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)
        self.login('test@canonical.com')
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        self.setUpBugsElsewhereTests()
        # We don't need to be logged in to run the tests.
        self.login(user=None)

    def _getBugTaskByProductName(self, bug, product_name):
        """Return a bug's bugtask that have the given product name."""
        for bugtask in bug.bugtasks:
            if bugtask.product and bugtask.product.name == product_name:
                return bugtask
        else:
            raise AssertionError(
                "Didn't find a %s task on bug %s." % (product_name, bug.id))

    def setUpBugsElsewhereTests(self):
        """Sets up a Firefox and a Thunderbird task as resolved."""
        bug_one = getUtility(IBugSet).get(1)
        firefox_upstream = self._getBugTaskByProductName(bug_one, 'firefox')
        self.assert_(firefox_upstream.product.official_malone)
        self.old_firefox_status = firefox_upstream.status
        firefox_upstream.transitionToStatus(BugTaskStatus.FIXRELEASED)
        self.firefox_upstream = firefox_upstream

        bug_nine = getUtility(IBugSet).get(9)
        thunderbird_upstream = self._getBugTaskByProductName(
            bug_nine, 'thunderbird')
        self.old_thunderbird_status = thunderbird_upstream.status
        thunderbird_upstream.transitionToStatus(BugTaskStatus.REJECTED)
        self.thunderbird_upstream = thunderbird_upstream

        flush_database_updates()

    def tearDown(self):
        self.login('test@canonical.com')
        self.tearDownBugsElsewhereTests()
        LaunchpadFunctionalTestCase.tearDown(self)

    def tearDownBugsElsewhereTests(self):
        """Resets the modified bugtasks to their original statuses."""
        self.firefox_upstream.transitionToStatus(self.old_firefox_status)
        self.thunderbird_upstream.transitionToStatus(
            self.old_thunderbird_status)
        flush_database_updates()

    def assertBugTaskIsPendingBugWatchElsewhere(self, bugtask):
        """Assert the the bugtask is pending a bug watch elsewhere.

        Pending a bugwatch elsewhere means that at least one of the bugtask's
        related task's target isn't using Malone, and that
        related_bugtask.bugwatch is None.
        """
        non_malone_using_bugtasks = [
            related_task for related_task in bugtask.related_tasks
            if not related_task.target_uses_malone
            ]
        pending_bugwatch_bugtasks = [
            related_bugtask for related_bugtask in non_malone_using_bugtasks
            if related_bugtask.bugwatch is None
            ]
        self.assert_(len(pending_bugwatch_bugtasks) > 0)

    def assertBugTaskIsResolvedElsewhere(self, bugtask):
        """Make sure that at least one of the related bugtasks is resolved."""
        resolved_related_tasks = [
            related_task for related_task in bugtask.related_tasks
            if related_task.status in RESOLVED_BUGTASK_STATUSES
            ]
        self.assert_(len(resolved_related_tasks) > 0)

    def isElsewhere(self, bugtask, related_task):
        """Whether the related task indeed is elsewhere.

        With elsewhere means in a diffferent distribution, distrorelease
        or product. Different source packages doesn't count as
        elsewhere.
        """
        return (
            related_task.product != bugtask.product or
            related_task.distribution != bugtask.distribution or
            related_task.distrorelease != bugtask.distrorelease)

    def assertShouldBeShownOnOmittedStatusSearch(self, bugtask,
                                                 omitted_statuses):
        """Make sure that the given bugtask should be shown.

        It checks that not all the tasks elsewhere have the omitted
        statuses.
        """
        tasks_with_omitted_statuses = [
            related_task for related_task in bugtask.related_tasks
            if (self.isElsewhere(related_task, bugtask) and
                related_task.status in omitted_statuses)
            ]
        self.assert_(
            len(bugtask.related_tasks) == 0 or
            len(tasks_with_omitted_statuses) < len(bugtask.related_tasks))

    def test_pending_bugwatch_ubuntu(self):
        # Find all open Ubuntu tasks that are pending a bug watch.
        params = BugTaskSearchParams(
            pending_bugwatch_elsewhere=True, user=None)
        pending_bugwatch_elsewhere_tasks = self.ubuntu.searchTasks(params)
        for bugtask in pending_bugwatch_elsewhere_tasks:
            self.assertBugTaskIsPendingBugWatchElsewhere(bugtask)

    def test_resolved_somewhere(self):
        # Find all open Ubuntu tasks that have been resolved somewhere
        # (i.e one of its related task has been resolved).
        params = BugTaskSearchParams(
            status_elsewhere=any(*RESOLVED_BUGTASK_STATUSES), user=None)
        closed_elsewhere_tasks = self.ubuntu.searchTasks(params)
        for bugtask in closed_elsewhere_tasks:
            self.assertBugTaskIsResolvedElsewhere(bugtask)

    def test_omit_resolved_status_ubuntu(self):
        # Show all open tasks on Ubuntu that haven't yet been resolved
        # somewhere else.
        params = BugTaskSearchParams(
            omit_status_elsewhere=any(*UNRESOLVED_BUGTASK_STATUSES), user=None)
        not_open_elsewhere_tasks = self.ubuntu.searchTasks(params)
        for bugtask in not_open_elsewhere_tasks:
            self.assertShouldBeShownOnOmittedStatusSearch(
                bugtask, UNRESOLVED_BUGTASK_STATUSES)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BugTaskSearchBugsElsewhereTest))
    return suite

if __name__ == '__main__':
    unittest.main()

