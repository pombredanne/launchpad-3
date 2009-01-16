# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Job-running facilities."""


from unittest import TestLoader

from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility

from canonical.testing import (LaunchpadFunctionalLayer)

from canonical.codehosting.jobs import JobRunner
from canonical.launchpad.database import RevisionMailJob
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel)
from canonical.launchpad.interfaces.branchsubscription import (
    BranchSubscriptionDiffSize,)
from canonical.launchpad.interfaces.job import JobStatus, LeaseHeld
from canonical.launchpad.tests.mail_helpers import pop_notifications
from canonical.launchpad.testing import TestCaseWithFactory


class TestJobRunner(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def makeBranchAndJobs(self):
        branch = self.factory.makeBranch()
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL)
        job_1 = RevisionMailJob.create(
            branch, 0, 'from@example.org', 'body', False, 'foo')
        job_2 = RevisionMailJob.create(
            branch, 1, 'from@example.org', 'body', False, 'bar')
        return branch, job_1, job_2

    def test_runJob(self):
        """Ensure status is set to completed when a job runs to completion."""
        branch, job_1, job_2 = self.makeBranchAndJobs()
        runner = JobRunner(job_1)
        runner.runJob(job_1)
        self.assertEqual(JobStatus.COMPLETED, job_1.job.status)
        self.assertEqual([job_1], runner.completed_jobs)

    def test_runAll(self):
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
        branch, job_1, job_2 = self.makeBranchAndJobs()
        def raise_lease_held():
            raise LeaseHeld()
        job_2.job.acquireLease = raise_lease_held
        runner = JobRunner.fromReady(RevisionMailJob)
        runner.runAll()
        self.assertEqual(JobStatus.COMPLETED, job_1.job.status)
        self.assertEqual(JobStatus.WAITING, job_2.job.status)
        self.assertEqual([job_1], runner.completed_jobs)
        self.assertEqual([job_2], runner.incomplete_jobs)

    def test_runAll_reports_oopses(self):
        branch, job_1, job_2 = self.makeBranchAndJobs()
        def raiseError():
            raise Exception('Fake exception.  Foobar, I say!')
        job_1.run = raiseError
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        self.assertEqual([job_2], runner.completed_jobs)
        self.assertEqual([job_1], runner.incomplete_jobs)
        self.assertEqual([], list(RevisionMailJob.iterReady()))
        self.assertEqual(JobStatus.FAILED, job_1.job.status)
        self.assertEqual(JobStatus.COMPLETED, job_2.job.status)
        reporter = getUtility(IErrorReportingUtility)
        oops = reporter.getLastOopsReport()
        self.assertIn('Fake exception.  Foobar, I say!', oops.tb_text)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
