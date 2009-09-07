#! /usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the update_preview_diffs script."""


import transaction

from canonical.testing import ZopelessAppServerLayer
from lp.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.branchmergeproposaljob import UpdatePreviewDiffJob


class TestUpdatePreviewDiffs(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_update_preview_diffs(self):
        """Ensure update_preview_diffs runs and generates diffs."""
        self.useTempBzrHome()
        target, target_tree = self.createMirroredBranchAndTree()
        target_tree.bzrdir.root_transport.put_bytes('foo', 'foo\n')
        target_tree.add('foo')
        target_tree.commit('added foo')
        source, source_tree = self.createMirroredBranchAndTree()
        source_tree.pull(target_tree.branch)
        source_tree.bzrdir.root_transport.put_bytes('foo', 'foo\nbar\n')
        source_tree.commit('added bar')
        # Add a fake revisions so the proposal is ready.
        self.factory.makeRevisionsForBranch(source, count=1)
        bmp = BranchMergeProposal(
            source_branch=source, target_branch=target,
            registrant=source.owner)
        job = UpdatePreviewDiffJob.create(bmp)
        self.assertIs(None, bmp.preview_diff)
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/update_preview_diffs.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Ran 1 IUpdatePreviewDiffJobSource jobs.\n', stderr)
        self.assertIsNot(None, bmp.preview_diff)
