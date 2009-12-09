#! /usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the update_preview_diffs script."""


import transaction

from canonical.testing import ZopelessAppServerLayer
from lp.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.webapp import errorlog
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.branchmergeproposaljob import UpdatePreviewDiffJob


class TestUpdatePreviewDiffs(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def create_preview_diff_job(self):
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
        return job, bmp, source_tree

    def test_update_preview_diffs(self):
        """Ensure update_preview_diffs runs and generates diffs."""
        job, bmp, source_tree = self.create_preview_diff_job()
        retcode, stdout, stderr = run_script(
            'cronscripts/update_preview_diffs.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Running synchronously.\n'
            'INFO    Ran 1 IUpdatePreviewDiffJobSource jobs.\n'
            'INFO    0 IUpdatePreviewDiffJobSource jobs did not complete.\n',
            stderr)
        self.assertIsNot(None, bmp.preview_diff)

    def test_update_preview_diffs_twisted(self):
        """Ensure update_preview_diffs runs and generates diffs."""
        job, bmp, source_tree = self.create_preview_diff_job()
        retcode, stdout, stderr = run_script(
            'cronscripts/update_preview_diffs.py', ['--twisted'])
        self.assertEqual(0, retcode)
        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Running through Twisted.\n'
            'INFO    Ran 1 IUpdatePreviewDiffJobSource jobs.\n'
            'INFO    0 IUpdatePreviewDiffJobSource jobs did not complete.\n',
            stderr)
        self.assertIsNot(None, bmp.preview_diff)

    def test_update_preview_diffs_oops(self):
        """Ensure update_preview_diffs runs and generates diffs."""
        job, bmp, source_tree = self.create_preview_diff_job()
        source_tree.bzrdir.root_transport.delete_tree('.bzr')
        error_utility = errorlog.ErrorReportingUtility()
        error_utility.configure('update_preview_diffs')
        old_id = error_utility.getLastOopsReport().id
        retcode, stdout, stderr = run_script(
            'cronscripts/update_preview_diffs.py', [])
        self.assertEqual(0, retcode)
        self.assertIn(
            'INFO    1 IUpdatePreviewDiffJobSource jobs did not complete.\n',
            stderr)
        self.assertIn('INFO    Job resulted in OOPS:', stderr)
        new_id = error_utility.getLastOopsReport().id
        self.assertNotEqual(old_id, new_id)

