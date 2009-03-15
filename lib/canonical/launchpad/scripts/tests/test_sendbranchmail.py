#! /usr/bin/python2.4
# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Test the sendbranchmail script"""

import unittest
import transaction

from canonical.testing import ZopelessAppServerLayer
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, BranchSubscriptionDiffSize,
    CodeReviewNotificationLevel,)
from canonical.launchpad.database.branchjob import (
    RevisionMailJob, RevisionsAddedJob)


class TestSendbranchmail(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def createBranch(self):
        branch, tree = self.createMirroredBranchAndTree()
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL)
        transport = tree.bzrdir.root_transport
        transport.put_bytes('foo', 'bar')
        tree.add('foo')
        tree.commit('Added foo.', rev_id='rev1')
        return branch, tree

    def test_sendbranchmail(self):
        """Ensure sendbranchmail runs and sends email."""
        self.useTempBzrHome()
        branch, tree = self.createBranch()
        job_1 = RevisionMailJob.create(
            branch, 1, 'from@example.org', 'body', True, 'foo')
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/sendbranchmail.py', [])
        self.assertEqual('INFO    creating lockfile\n'
                         'INFO    Ran 1 RevisionMailJobs.\n', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(0, retcode)

    def test_revision_added_job(self):
        """RevisionsAddedJobs are run by sendbranchmail."""
        self.useTempBzrHome()
        branch, tree = self.createBranch()
        tree.bzrdir.root_transport.put_bytes('foo', 'baz')
        tree.commit('Added foo.', rev_id='rev2')
        job_1 = RevisionsAddedJob.create(
            branch, 'rev1', 'rev2', 'from@example.org')
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/sendbranchmail.py', [])
        self.assertEqual('INFO    creating lockfile\n'
                         'INFO    Ran 1 RevisionMailJobs.\n', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(0, retcode)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
