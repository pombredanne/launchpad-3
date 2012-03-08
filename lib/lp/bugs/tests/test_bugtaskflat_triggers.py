# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from collections import namedtuple
from contextlib import contextmanager

from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.model.bug import Bug
from lp.services.database.lpstorm import IStore
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.layers import DatabaseFunctionalLayer

BUGTASKFLAT_COLUMNS = (
    'bugtask',
    'bug',
    'datecreated',
    'duplicateof',
    'bug_owner',
    'fti',
    'private',
    'security_related',
    'date_last_updated',
    'heat',
    'product',
    'productseries',
    'distribution',
    'distroseries',
    'sourcepackagename',
    'status',
    'importance',
    'assignee',
    'milestone',
    'owner',
    'active',
    'access_policies',
    'access_grants',
    )

BugTaskFlat = namedtuple('BugTaskFlat', BUGTASKFLAT_COLUMNS)


class BugTaskFlatTestMixin(TestCaseWithFactory):

    def setUp(self):
        super(BugTaskFlatTestMixin, self).setUp()
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

    def getBugTaskFlat(self, bugtask):
        if hasattr(bugtask, 'id'):
            bugtask = bugtask.id
        assert bugtask is not None
        result = IStore(Bug).execute(
            "SELECT %s FROM bugtaskflat WHERE bugtask = ?"
            % ', '.join(BUGTASKFLAT_COLUMNS), (bugtask,)).get_one()
        if result is not None:
            result = BugTaskFlat(*result)
        return result

    @contextmanager
    def bugtaskflat_is_deleted(self, bugtask):
        old_row = self.getBugTaskFlat(bugtask)
        self.assertFlattened(bugtask)
        self.assertIsNot(None, old_row)
        yield
        new_row = self.getBugTaskFlat(bugtask)
        self.assertFlattened(bugtask)
        self.assertIs(None, new_row)

    @contextmanager
    def bugtaskflat_is_updated(self, bugtask, expected_fields):
        old_row = self.getBugTaskFlat(bugtask)
        self.assertFlattened(bugtask)
        yield
        new_row = self.getBugTaskFlat(bugtask)
        self.assertFlattened(bugtask)
        changed_fields = [
            field for field in BugTaskFlat._fields
            if getattr(old_row, field) != getattr(new_row, field)]
        self.assertEqual(expected_fields, changed_fields)

    @contextmanager
    def bugtaskflat_is_identical(self, bugtask):
        old_row = self.getBugTaskFlat(bugtask)
        self.assertFlattened(bugtask)
        yield
        new_row = self.getBugTaskFlat(bugtask)
        self.assertFlattened(bugtask)
        self.assertEqual(old_row, new_row)


class TestBugTaskFlatten(BugTaskFlatTestMixin):

    layer = DatabaseFunctionalLayer

    def test_create(self):
        # bugtask_flatten() returns true if the BugTaskFlat is missing,
        # and optionally creates it.
        task = self.factory.makeBugTask()
        self.assertTrue(self.checkFlattened(task))
        with dbuser('testadmin'):
            IStore(Bug).execute(
                "DELETE FROM BugTaskFlat WHERE bugtask = ?", (task.id,))
        self.assertFlattens(task)

    def test_update(self):
        # bugtask_flatten() returns true if the BugTaskFlat is out of
        # date, and optionally updates it.
        task = self.factory.makeBugTask()
        self.assertTrue(self.checkFlattened(task))
        with dbuser('testadmin'):
            IStore(Bug).execute(
                "UPDATE BugTaskFlat SET status = ? WHERE bugtask = ?",
                (BugTaskStatus.UNKNOWN.value, task.id))
        self.assertFlattens(task)

    def test_delete(self):
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


class TestBugTaskFlatTriggers(BugTaskFlatTestMixin):

    layer = DatabaseFunctionalLayer

    def test_bugtask_create(self):
        # Triggers maintain BugTaskFlat when a task is created.
        task = self.factory.makeBugTask()
        self.assertFlattened(task)

    def test_bugtask_delete(self):
        # Triggers maintain BugTaskFlat when a task is deleted.
        task = self.factory.makeBugTask()
        with person_logged_in(task.owner):
            with self.bugtaskflat_is_deleted(task):
                task.delete()

    def test_bugtask_change(self):
        # Triggers maintain BugTaskFlat when a task is changed.
        task = self.factory.makeBugTask()
        with person_logged_in(task.owner):
            with self.bugtaskflat_is_updated(task, ['status']):
                task.transitionToStatus(BugTaskStatus.UNKNOWN, task.owner)

    def test_bugtask_change_unflattened(self):
        # Some fields on BugTask aren't mirrored, so don't trigger updates.
        task = self.factory.makeBugTask()
        with person_logged_in(task.owner):
            with self.bugtaskflat_is_identical(task):
                task.bugwatch = self.factory.makeBugWatch()

    def test_bug_change(self):
        # Triggers maintain BugTaskFlat when a bug is changed
        task = self.factory.makeBugTask()
        with person_logged_in(task.owner):
            with self.bugtaskflat_is_updated(task, ['security_related']):
                task.bug.security_related = True

    def test_bug_change_unflattened(self):
        # Some fields on Bug aren't mirrored, so don't trigger updates.
        task = self.factory.makeBugTask()
        with person_logged_in(task.owner):
            with self.bugtaskflat_is_identical(task):
                task.bug.who_made_private = task.owner
