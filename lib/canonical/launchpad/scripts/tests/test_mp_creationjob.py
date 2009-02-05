#! /usr/bin/python2.4
# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Test the sendbranchmail script"""

import unittest
import transaction

from canonical.testing import ZopelessAppServerLayer
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.database.branchmergeproposal import (
    BranchMergeProposal, MergeProposalCreatedJob)


class TestDiffBMPs(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_mpcreationjobs(self):
        """Ensure mpcreationjobs runs and generates diffs."""
        self.useTempBzrHome()
        target, target_tree = self.createMirroredBranchAndTree()
        target_tree.bzrdir.root_transport.put_bytes('foo', 'foo\n')
        target_tree.add('foo')
        target_tree.commit('added foo')
        source, source_tree = self.createMirroredBranchAndTree()
        source_tree.pull(target_tree.branch)
        source_tree.bzrdir.root_transport.put_bytes('foo', 'foo\nbar\n')
        source_tree.commit('added bar')
        bmp = BranchMergeProposal(
            source_branch=source, target_branch=target,
            registrant=source.owner)
        job = MergeProposalCreatedJob.create(bmp)
        self.assertIs(None, bmp.review_diff)
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/mpcreationjobs.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual('Ran 1 MergeProposalCreatedJobs.\n', stdout)
        self.assertEqual('INFO    creating lockfile\n', stderr)
        self.assertIsNot(None, bmp.review_diff)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
