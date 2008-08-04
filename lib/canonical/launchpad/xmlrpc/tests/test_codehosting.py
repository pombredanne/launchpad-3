# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import IBranchSet
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.xmlrpc.codehosting import BranchDetailsStorageAPI
from canonical.testing import DatabaseFunctionalLayer


class BranchDetailsStorageTest(TestCaseWithFactory):
    """Tests for the implementation of `IBranchDetailsStorage`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.storage = BranchDetailsStorageAPI(None, None)

    def assertUnmirrored(self, branch):
        """Assert that `branch` has not yet been mirrored.

        Asserts that last_mirror_attempt, last_mirrored and
        mirror_status_message are all None, and that mirror_failures is 0.
        """
        self.assertIs(None, branch.last_mirror_attempt)
        self.assertIs(None, branch.last_mirrored)
        self.assertEqual(0, branch.mirror_failures)
        self.assertIs(None, branch.mirror_status_message)

    def test_startMirroring(self):
        # startMirroring updates last_mirror_attempt to 'now', leaves
        # last_mirrored alone and returns True when passed the id of an
        # existing branch.
        branch = self.factory.makeBranch()
        self.assertUnmirrored(branch)

        success = self.storage.startMirroring(branch.id)
        self.assertEqual(success, True)

        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirror_attempt', UTC_NOW)
        self.assertIs(None, branch.last_mirrored)

    def test_startMirroring_invalid_branch(self):
        # startMirroring returns False when given a branch id which does not
        # exist.
        invalid_id = -1
        branch = getUtility(IBranchSet).get(invalid_id)
        self.assertIs(None, branch)

        success = self.storage.startMirroring(invalid_id)
        self.assertEqual(success, False)

    def test_mirrorFailed(self):
        branch = self.factory.makeBranch()
        self.assertUnmirrored(branch)

        self.storage.startMirroring(branch.id)
        failure_message = self.factory.getUniqueString()
        success = self.storage.mirrorFailed(branch.id, failure_message)
        self.assertEqual(success, True)

        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirror_attempt', UTC_NOW)
        self.assertIs(None, branch.last_mirrored)
        self.assertEqual(1, branch.mirror_failures)
        self.assertEqual(failure_message, branch.mirror_status_message)

    def test_mirrorComplete(self):
        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored, mirror_failures
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertEqual(row[0], None)
        self.assertEqual(row[1], None)
        self.assertEqual(row[2], 0)

        success = self.storage._startMirroringInteraction(1)
        self.assertEqual(success, True)
        success = self.storage._mirrorCompleteInteraction(1, 'rev-1')
        self.assertEqual(success, True)

        cur = cursor()
        cur.execute("""
            SELECT last_mirror_attempt, last_mirrored, mirror_failures,
                   last_mirrored_id
                FROM branch WHERE id = 1""")
        row = cur.fetchone()
        self.assertNotEqual(row[0], None)
        self.assertEqual(row[0], row[1])
        self.assertEqual(row[2], 0)
        self.assertEqual(row[3], 'rev-1')

    def test_mirrorComplete_resets_failure_count(self):
        # this increments the failure count ...
        self.test_mirrorFailed()

        success = self.storage._startMirroringInteraction(1)
        self.assertEqual(success, True)
        success = self.storage._mirrorCompleteInteraction(1, 'rev-1')
        self.assertEqual(success, True)

        cur = cursor()
        cur.execute("""
            SELECT last_mirror_attempt, last_mirrored, mirror_failures
                FROM branch WHERE id = 1""")
        row = cur.fetchone()
        self.assertNotEqual(row[0], None)
        self.assertEqual(row[0], row[1])
        self.assertEqual(row[2], 0)

    def test_recordSuccess(self):
        # recordSuccess must insert the given data into BranchActivity.
        started = datetime.datetime(2007, 07, 05, 19, 32, 1, tzinfo=UTC)
        completed = datetime.datetime(2007, 07, 05, 19, 34, 24, tzinfo=UTC)
        started_tuple = tuple(started.utctimetuple())
        completed_tuple = tuple(completed.utctimetuple())
        success = self.storage._recordSuccessInteraction(
            'test-recordsuccess', 'vostok', started_tuple, completed_tuple)
        self.assertEqual(success, True, '_recordSuccessInteraction failed')

        cur = cursor()
        cur.execute("""
            SELECT name, hostname, date_started, date_completed
                FROM ScriptActivity where name = 'test-recordsuccess'""")
        row = cur.fetchone()
        self.assertEqual(row[0], 'test-recordsuccess')
        self.assertEqual(row[1], 'vostok')
        self.assertEqual(row[2], started.replace(tzinfo=None))
        self.assertEqual(row[3], completed.replace(tzinfo=None))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

