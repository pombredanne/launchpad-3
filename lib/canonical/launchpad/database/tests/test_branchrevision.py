# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for BranchRevisions."""

__metaclass__ = type

import psycopg
import transaction
from unittest import TestCase, TestLoader

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.interfaces import (
    IBranchSet, IBranchRevisionSet)
from canonical.launchpad.testing import LaunchpadObjectFactory

from canonical.testing import LaunchpadZopelessLayer

from zope.component import getUtility


class TestTipRevisionsForBranches(TestCase):
    """Test that the tip revisions get returned properly."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        login('test@canonical.com')

        factory = LaunchpadObjectFactory()
        branches = [factory.makeBranch() for count in range(5)]
        branch_ids = [branch.id for branch in branches]
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
        for branch in branches:
            factory.makeRevisionsForBranch(branch)
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.launchpad.dbuser)
        # Retrieve the updated branches (due to transaction boundaries).
        branch_set = getUtility(IBranchSet)
        self.branches = [branch_set.get(id) for id in branch_ids]
        self.branch_revision_set = getUtility(IBranchRevisionSet)

    def tearDown(self):
        logout()

    def _breakTransaction(self):
        # make sure the current transaction can not be committed by
        # sending a broken SQL statement to the database
        try:
            cursor().execute('break this transaction')
        except psycopg.DatabaseError:
            pass

    def testNoBranches(self):
        """Assert that when given an empty list, an empty list is returned."""
        bs = self.branch_revision_set
        branch_revisions = bs.getTipRevisionsForBranches([])
        self.assertEqual([], branch_revisions)

    def testOneBranches(self):
        """When given one branch, one branch revision is returned."""
        branch_revisions = list(
            self.branch_revision_set.getTipRevisionsForBranches(
                self.branches[:1]))
        self._breakTransaction()
        self.assertEqual(1, len(branch_revisions))
        branch_revision = branch_revisions[0]
        self.assertEqual(self.branches[0], branch_revision.branch)
        # By accessing to the revision we can confirm that the revision
        # has in fact been retrieved already.
        revision = branch_revision.revision
        self.assertTrue(revision is not None)

    def testManyBranches(self):
        """Assert multiple branch revisions are returned correctly."""
        branch_revisions = list(
            self.branch_revision_set.getTipRevisionsForBranches(
                self.branches))
        self._breakTransaction()
        self.assertEqual(5, len(branch_revisions))
        for branch_revision in branch_revisions:
            # By accessing to the revision we can confirm that the revision
            # has in fact been retrieved already.
            revision = branch_revision.revision
            self.assertTrue(revision is not None)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
