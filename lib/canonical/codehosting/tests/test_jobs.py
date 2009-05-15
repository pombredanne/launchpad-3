# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for Job-running facilities."""


from unittest import TestLoader

import transaction
from canonical.testing import (LaunchpadZopelessLayer)

from canonical.config import config
from canonical.codehosting.jobs import JobRunner
from lp.code.model.branchjob import RevisionMailJob
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel)
from canonical.launchpad.database.diff import StaticDiff
from lp.code.interfaces.branchsubscription import (
    BranchSubscriptionDiffSize,)
from canonical.launchpad.interfaces.job import JobStatus
from lp.testing.mail_helpers import pop_notifications
from lp.testing import TestCaseWithFactory
from canonical.launchpad.webapp import errorlog


class TestJobRunner(TestCaseWithFactory):
    """Ensure JobRunner behaves as expected."""

    layer = LaunchpadZopelessLayer

    def makeBranchAndJobs(self):
        """Test fixture.  Create a branch and two jobs that use it."""
        branch = self.factory.makeBranch()
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL)
        job_1 = RevisionMailJob.create(
            branch, 0, 'from@example.org', 'body', False, 'foo')
        job_2 = RevisionMailJob.create(
            branch, 1, 'from@example.org', 'body', False, 'bar')
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(config.sendbranchmail.dbuser)
        return branch, job_1, job_2

    def test_runJob(self):
        """Ensure status is set to completed when a job runs to completion."""
        branch, job_1, job_2 = self.makeBranchAndJobs()
        runner = JobRunner(job_1)
        runner.runJob(job_1)
        self.assertEqual(JobStatus.COMPLETED, job_1.job.status)
        self.assertEqual([job_1], runner.completed_jobs)

    def test_runJob_generates_diff(self):
        """Ensure that a diff is actually generated in this environment."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL)
        tree_transport = tree.bzrdir.root_transport
        tree_transport.put_bytes("hello.txt", "Hello World\n")
        tree.add('hello.txt')
        to_revision_id = tree.commit('rev1', timestamp=1e9, timezone=0)
        job = RevisionMailJob.create(
            branch, 1, 'from@example.org', 'body', True, 'subject')
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(config.sendbranchmail.dbuser)
        runner = JobRunner(job)
        runner.runJob(job)
        existing_diff = StaticDiff.selectOneBy(
            from_revision_id='null:', to_revision_id=to_revision_id)
        self.assertIsNot(None, existing_diff)

    def test_runAll(self):
        """Ensure runAll works in the normal case."""
        branch, job_1, job_2 = self.makeBranchAndJobs()
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        self.assertEqual(JobStatus.COMPLETED, job_1.job.status)
        self.assertEqual(JobStatus.COMPLETED, job_2.job.status)
        (mail1, mail2) = pop_notifications()
        self.assertEqual(
            set(['foo', 'bar']), set([mail1['Subject'], mail2['Subject']]))
        self.assertEqual([job_1, job_2], runner.completed_jobs)

    def test_runAll_skips_lease_failures(self):
        """Ensure runAll skips jobs whose leases can't be acquired."""
        last_oops = errorlog.globalErrorUtility.getLastOopsReport()
        branch, job_1, job_2 = self.makeBranchAndJobs()
        job_2.job.acquireLease()
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        self.assertEqual(JobStatus.COMPLETED, job_1.job.status)
        self.assertEqual(JobStatus.WAITING, job_2.job.status)
        self.assertEqual([job_1], runner.completed_jobs)
        self.assertEqual([job_2], runner.incomplete_jobs)
        new_last_oops = errorlog.globalErrorUtility.getLastOopsReport()
        self.assertEqual(last_oops.id, new_last_oops.id)

    def test_runAll_reports_oopses(self):
        """When an error is encountered, report an oops and continue."""
        branch, job_1, job_2 = self.makeBranchAndJobs()
        def raiseError():
            # Ensure that jobs which call transaction.abort work, too.
            transaction.abort()
            raise Exception('Fake exception.  Foobar, I say!')
        job_1.run = raiseError
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        self.assertEqual([job_2], runner.completed_jobs)
        self.assertEqual([job_1], runner.incomplete_jobs)
        self.assertEqual([], list(RevisionMailJob.iterReady()))
        self.assertEqual(JobStatus.FAILED, job_1.job.status)
        self.assertEqual(JobStatus.COMPLETED, job_2.job.status)
        reporter = errorlog.globalErrorUtility
        oops = reporter.getLastOopsReport()
        self.assertIn('Fake exception.  Foobar, I say!', oops.tb_text)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
