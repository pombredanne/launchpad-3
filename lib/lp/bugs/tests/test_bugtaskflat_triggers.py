# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.model.bug import Bug
from lp.services.database.lpstorm import IStore
from lp.services.features.testing import FeatureFixture
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.layers import DatabaseFunctionalLayer


class TestBugTaskFlatTrigger(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTaskFlatTrigger, self).setUp()
        self.useFixture(FeatureFixture(
            {'disclosure.allow_multipillar_private_bugs.enabled': 'true'}))

    def checkFlattened(self, bugtask, check_only=True):
        if hasattr(bugtask, 'id'):
            bugtask = bugtask.id
        result = IStore(Bug).execute(
            "SELECT bugtask_flatten(?, ?)", (bugtask, check_only))
        return result.get_one()[0]

    def assertFlattened(self, bugtask):
        # Assert that the BugTask is correctly represented in
        # BugTaskFlat.
        self.assertIs(True, self.checkFlattened(bugtask))

    def assertFlattens(self, bugtask):
        # Assert that the BugTask isn't correctly represented in
        # BugTaskFlat, but a call to bugtask_flatten fixes it.
        self.assertFalse(self.checkFlattened(bugtask))
        self.checkFlattened(bugtask, check_only=False)
        self.assertTrue(self.checkFlattened(bugtask))

    def test_new_bug(self):
        # Triggers maintain BugTaskFlat when a task is created.
        task = self.factory.makeBugTask()
        self.assertFlattened(task)

    def test_bugtask_flatten_creates(self):
        # bugtask_flatten() returns true if the BugTaskFlat is missing,
        # and optionally creates it.
        task = self.factory.makeBugTask()
        self.assertTrue(self.checkFlattened(task))
        with dbuser('testadmin'):
            IStore(Bug).execute(
                "DELETE FROM BugTaskFlat WHERE bugtask = ?", (task.id,))
        self.assertFlattens(task)

    def test_bugtask_flatten_updates(self):
        # bugtask_flatten() returns true if the BugTaskFlat is out of
        # date, and optionally updates it.
        task = self.factory.makeBugTask()
        self.assertTrue(self.checkFlattened(task))
        with dbuser('testadmin'):
            IStore(Bug).execute(
                "UPDATE BugTaskFlat SET status = ? WHERE bugtask = ?",
                (BugTaskStatus.UNKNOWN.value, task.id))
        self.assertFlattens(task)

    def test_bugtask_flatten_deletes(self):
        # bugtask_flatten() returns true if the BugTaskFlat exists but
        # the task doesn't, and optionally deletes it.
        self.assertTrue(self.checkFlattened(200))
        with dbuser('testadmin'):
            IStore(Bug).execute(
                "INSERT INTO bugtaskflat "
                "(bug, bugtask, bug_owner, private, security_related, "
                " date_last_updated, heat, status, importance, owner, "
                " active) "
                "VALUES "
                "(1, 200, 1, false, false, "
                " current_timestamp at time zone 'UTC', 999, 1, 1, 1, true);")
        self.assertFlattens(200)
