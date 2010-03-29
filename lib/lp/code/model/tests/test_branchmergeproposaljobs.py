# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for branch merge proposal jobs."""

__metaclass__ = type

import transaction
import unittest

from sqlobject import SQLObjectNotFound
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer, LaunchpadZopelessLayer

from lazr.lifecycle.event import ObjectModifiedEvent
from lp.code.adapters.branch import BranchMergeProposalDelta
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposalJob, IBranchMergeProposalJobSource,
    IMergeProposalCreatedJob, IUpdatePreviewDiffJobSource,
    )
from lp.code.model.branchmergeproposaljob import (
     BranchMergeProposalJob, BranchMergeProposalJobDerived,
     BranchMergeProposalJobType, CodeReviewCommentEmailJob,
     MergeProposalCreatedJob, MergeProposalUpdatedEmailJob,
     ReviewRequestedEmailJob, UpdatePreviewDiffJob,
     )
from lp.code.model.tests.test_diff import DiffTestCase
from lp.code.subscribers.branchmergeproposal import merge_proposal_modified
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


class TestBranchMergeProposalJobSource(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.job_source = getUtility(IBranchMergeProposalJobSource)

    def test_utility_provides_interface(self):
        # The utility that is registered as the job source needs to implement
        # the methods is says it does.
        self.assertProvides(self.job_source, IBranchMergeProposalJobSource)

    def test_iterReady_new_merge_proposal_update_unready(self):
        # A new merge proposal has two jobs, one for the diff, and one for the
        # email.  The diff email is always returned first, providing that it
        # is ready.  The diff job is ready if both the source and target have
        # revisions, and the source branch doesn't have a pending scan.
        bmp = self.factory.makeBranchMergeProposal()
        jobs = self.job_source.iterReady()
        self.assertEqual([], jobs)

    def test_iterReady_new_merge_proposal_target_revisions(self):
        # The target branch having revisions is not enough for the job to be
        # considered ready.
        bmp = self.factory.makeBranchMergeProposal()
        self.factory.makeRevisionsForBranch(bmp.target_branch)
        jobs = self.job_source.iterReady()
        self.assertEqual([], jobs)

    def test_iterReady_new_merge_proposal_source_revisions(self):
        # The source branch having revisinos is not enough for the job to be
        # considered ready.
        bmp = self.factory.makeBranchMergeProposal()
        self.factory.makeRevisionsForBranch(bmp.source_branch)
        jobs = self.job_source.iterReady()
        self.assertEqual([], jobs)

    def test_iterReady_new_merge_proposal_update_diff_first(self):
        # A new merge proposal has two jobs, one for the diff, and one for the
        # email.  The diff email is always returned first.
        bmp = self.factory.makeBranchMergeProposal()
        [job] = self.job_source.iterReady()
        self.assertEqual(job.branch_merge_proposal, bmp)
        self.assertIsInstance(job, UpdatePreviewDiffJob)

    def test_iterReady_new_merge_proposal_update_diff_running(self):
        # If the update preview diff job is running, then iterReady does not
        # return any other jobs for that merge proposal.
        self.factory.makeBranchMergeProposal()
        [job] = self.job_source.iterReady()
        job.start()
        jobs = self.job_source.iterReady()
        self.assertEqual(0, len(jobs))

    def test_iterReady_new_merge_proposal_update_diff_finished(self):
        # Once the update preview diff job has finished running, then
        # iterReady returns the next job for the merge proposal, which is in
        # this case the initial email job.
        bmp = self.factory.makeBranchMergeProposal()
        [update_diff] = self.job_source.iterReady()
        update_diff.start()
        update_diff.complete()
        [job] = self.job_source.iterReady()
        self.assertEqual(job.branch_merge_proposal, bmp)
        self.assertIsInstance(job, MergeProposalCreatedJob)

    def completePendingJobs(self):
        # Mark all current pending jobs as complete
        while True:
            jobs = self.job_source.iterReady()
            if len(jobs) == 0:
                break
            for job in jobs:
                job.start()
                job.complete()

    def test_iterReady_supports_review_requested(self):
        # iterReady will also return pending ReviewRequestedEmailJobs.
        bmp = self.factory.makeBranchMergeProposal()
        self.completePendingJobs()
        reviewer = self.factory.makePerson()
        bmp.nominateReviewer(reviewer, bmp.registrant)
        [job] = self.job_source.iterReady()
        self.assertEqual(job.branch_merge_proposal, bmp)
        self.assertIsInstance(job, ReviewRequestedEmailJob)
        self.assertEqual(reviewer, job.reviewer)
        self.assertEqual(bmp.registrant, job.requester)

    def test_iterReady_supports_code_review_comment(self):
        # iterReady will also return pending CodeReviewCommentEmailJob.
        bmp = self.factory.makeBranchMergeProposal()
        self.completePendingJobs()
        commenter = self.factory.makePerson()
        comment = bmp.createComment(commenter, '', 'Interesting idea.')
        [job] = self.job_source.iterReady()
        self.assertEqual(job.branch_merge_proposal, bmp)
        self.assertIsInstance(job, CodeReviewCommentEmailJob)
        self.assertEqual(comment, job.code_review_comment)

    def test_iterReady_supports_updated_emails(self):
        # iterReady will also return pending MergeProposalUpdatedEmailJob.
        bmp = self.factory.makeBranchMergeProposal()
        self.completePendingJobs()
        old_merge_proposal = BranchMergeProposalDelta.snapshot(bmp)
        bmp.commit_message = 'new commit message'
        event = ObjectModifiedEvent(
            bmp, old_merge_proposal, [], bmp.registrant)
        merge_proposal_modified(bmp, event)
        [job] = self.job_source.iterReady()
        self.assertEqual(job.branch_merge_proposal, bmp)
        self.assertIsInstance(job, MergeProposalUpdatedEmailJob)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
