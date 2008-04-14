# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for Revisions."""

__metaclass__ = type

from unittest import TestCase, TestLoader

import psycopg2
import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.interfaces import (
    IBranchSet, IRevisionSet)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer


class TestTipRevisionsForBranches(TestCase):
    """Test that the tip revisions get returned properly."""

    # The LaunchpadZopelessLayer is used as the setUp needs to
    # switch database users in order to create revisions for the
    # test branches.
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
        self.revision_set = getUtility(IRevisionSet)

    def tearDown(self):
        logout()

    def _breakTransaction(self):
        # make sure the current transaction can not be committed by
        # sending a broken SQL statement to the database
        try:
            cursor().execute('break this transaction')
        except psycopg2.DatabaseError:
            pass

    def testNoBranches(self):
        """Assert that when given an empty list, an empty list is returned."""
        bs = self.revision_set
        revisions = bs.getTipRevisionsForBranches([])
        self.assertTrue(revisions is None)

    def testOneBranches(self):
        """When given one branch, one branch revision is returned."""
        revisions = list(
            self.revision_set.getTipRevisionsForBranches(
                self.branches[:1]))
        self._breakTransaction()
        self.assertEqual(1, len(revisions))
        revision = revisions[0]
        self.assertEqual(self.branches[0].last_scanned_id,
                         revision.revision_id)
        # By accessing to the revision_author we can confirm that the
        # revision author has in fact been retrieved already.
        revision_author = revision.revision_author
        self.assertTrue(revision_author is not None)

    def testManyBranches(self):
        """Assert multiple branch revisions are returned correctly."""
        revisions = list(
            self.revision_set.getTipRevisionsForBranches(
                self.branches))
        self._breakTransaction()
        self.assertEqual(5, len(revisions))
        for revision in revisions:
            # By accessing to the revision_author we can confirm that the
            # revision author has in fact been retrieved already.
            revision_author = revision.revision_author
            self.assertTrue(revision_author is not None)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
