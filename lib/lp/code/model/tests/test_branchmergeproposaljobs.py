# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for branch merge proposal jobs."""

__metaclass__ = type

import transaction
import unittest

from sqlobject import SQLObjectNotFound

from canonical.config import config
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer, LaunchpadZopelessLayer

from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposalJob, IMergeProposalCreatedJob,
    IUpdatePreviewDiffJobSource,
    )
from lp.code.model.branchmergeproposaljob import (
     BranchMergeProposalJob, BranchMergeProposalJobDerived,
     BranchMergeProposalJobType, MergeProposalCreatedJob,
     UpdatePreviewDiffJob,
     )
from lp.code.model.tests.test_diff import DiffTestCase
from lp.services.job.runner import JobRunner
from lp.testing import TestCaseWithFactory
from lp.testing.mail_helpers import pop_notifications


class TestBranchMergeProposalJob(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        """BranchMergeProposalJob implements expected interfaces."""
        bmp = self.factory.makeBranchMergeProposal()
        job = BranchMergeProposalJob(
            bmp, BranchMergeProposalJobType.MERGE_PROPOSAL_CREATED, {})
        job.sync()
        verifyObject(IBranchMergeProposalJob, job)


class TestBranchMergeProposalJobDerived(TestCaseWithFactory):
    """Test the behaviour of the BranchMergeProposalJobDerived base class."""

    layer = LaunchpadZopelessLayer

    def test_get(self):
        """Ensure get returns or raises appropriately.

        It's an error to call get on BranchMergeProposalJobDerived-- it must
        be called on a subclass.  An object is returned only if the job id
        and job type match the request.  If no suitable object can be found,
        SQLObjectNotFound is raised.
        """
        bmp = self.factory.makeBranchMergeProposal()
        job = MergeProposalCreatedJob.create(bmp)
        transaction.commit()
        self.assertRaises(
            AttributeError, BranchMergeProposalJobDerived.get, job.id)
        self.assertRaises(SQLObjectNotFound, UpdatePreviewDiffJob.get, job.id)
        self.assertRaises(
            SQLObjectNotFound, MergeProposalCreatedJob.get, job.id + 1)
        self.assertEqual(job, MergeProposalCreatedJob.get(job.id))


class TestMergeProposalCreatedJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        """MergeProposalCreatedJob provides the expected interfaces."""
        bmp = self.factory.makeBranchMergeProposal()
        job = MergeProposalCreatedJob.create(bmp)
        verifyObject(IMergeProposalCreatedJob, job)
        verifyObject(IBranchMergeProposalJob, job)

    def test_run_makes_diff(self):
        """MergeProposalCreationJob.run creates a diff."""
        self.useBzrBranches()
        target, target_tree = self.create_branch_and_tree('target')
        target_tree.bzrdir.root_transport.put_bytes('foo', 'foo\n')
        target_tree.add('foo')
        rev1 = target_tree.commit('added foo')
        source, source_tree = self.create_branch_and_tree('source')
        source_tree.pull(target_tree.branch, stop_revision=rev1)
        source_tree.bzrdir.root_transport.put_bytes('foo', 'foo\nbar\n')
        source_tree.commit('added bar')
        target_tree.merge_from_branch(source_tree.branch)
        target_tree.commit('merged from source')
        source_tree.bzrdir.root_transport.put_bytes('foo', 'foo\nbar\nqux\n')
        source_tree.commit('added qux')
        bmp = self.factory.makeBranchMergeProposal(
            source_branch=source, target_branch=target,
            registrant=source.owner)
        job = MergeProposalCreatedJob.create(bmp)
        transaction.commit()
        self.layer.switchDbUser(config.merge_proposal_email_jobs.dbuser)
        job.run()
        self.assertIs(None, bmp.review_diff)
        self.assertIsNot(None, bmp.preview_diff)
        transaction.commit()
        self.checkDiff(bmp.preview_diff)

    def checkDiff(self, diff):
        self.assertNotIn('+bar', diff.diff.text)
        self.assertIn('+qux', diff.diff.text)

    def createProposalWithEmptyBranches(self):
        target_branch, tree = self.create_branch_and_tree()
        tree.commit('test')
        source_branch = self.factory.makeProductBranch(
            product=target_branch.product)
        self.createBzrBranch(source_branch, tree.branch)
        return self.factory.makeBranchMergeProposal(
            source_branch=source_branch, target_branch=target_branch)

    def test_run_sends_email(self):
        """MergeProposalCreationJob.run sends an email."""
        self.useBzrBranches()
        bmp = self.createProposalWithEmptyBranches()
        job = MergeProposalCreatedJob.create(bmp)
        self.assertEqual([], pop_notifications())
        job.run()
        self.assertEqual(2, len(pop_notifications()))

    def test_getOopsMailController(self):
        """The registrant is notified about merge proposal creation issues."""
        bmp = self.factory.makeBranchMergeProposal()
        bmp.source_branch.requestMirror()
        job = MergeProposalCreatedJob.create(bmp)
        ctrl = job.getOopsMailController('1234')
        self.assertEqual([bmp.registrant.preferredemail.email], ctrl.to_addrs)
        message = (
            'notifying people about the proposal to merge %s into %s' %
            (bmp.source_branch.bzr_identity, bmp.target_branch.bzr_identity))
        self.assertIn(message, ctrl.body)

    def test_MergeProposalCreateJob_with_sourcepackage_branch(self):
        """Jobs for merge proposals with sourcepackage branches work."""
        self.useBzrBranches()
        bmp = self.factory.makeBranchMergeProposal(
            target_branch=self.factory.makePackageBranch())
        tree = self.create_branch_and_tree(db_branch=bmp.target_branch)[1]
        tree.commit('Initial commit')
        self.createBzrBranch(bmp.source_branch, tree.branch)
        self.factory.makeRevisionsForBranch(bmp.source_branch, count=1)
        job = MergeProposalCreatedJob.create(bmp)
        transaction.commit()
        self.layer.switchDbUser(config.merge_proposal_email_jobs.dbuser)
        job.run()


class TestUpdatePreviewDiffJob(DiffTestCase):

    layer = LaunchpadZopelessLayer

    def test_implement_interface(self):
        """UpdatePreviewDiffJob implements IUpdatePreviewDiffJobSource."""
        verifyObject(IUpdatePreviewDiffJobSource, UpdatePreviewDiffJob)

    def test_run(self):
        self.useBzrBranches()
        bmp = self.createExampleMerge()[0]
        UpdatePreviewDiffJob.create(bmp)
        self.factory.makeRevisionsForBranch(bmp.source_branch, count=1)
        bmp.source_branch.next_mirror_time = None
        transaction.commit()
        self.layer.switchDbUser(config.update_preview_diffs.dbuser)
        JobRunner.fromReady(UpdatePreviewDiffJob).runAll()
        transaction.commit()
        self.checkExampleMerge(bmp.preview_diff.text)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
