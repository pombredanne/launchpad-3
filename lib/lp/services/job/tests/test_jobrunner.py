# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for job-running facilities."""


from unittest import TestLoader

import transaction
from canonical.testing import LaunchpadZopelessLayer
from zope.interface import implements

from lp.testing.mail_helpers import pop_notifications
from lp.services.job.runner import JobRunner, BaseRunnableJob
from lp.services.job.interfaces.job import JobStatus, IRunnableJob
from lp.services.job.model.job import Job
from lp.testing import TestCaseWithFactory
from canonical.launchpad.webapp import errorlog


class NullJob(BaseRunnableJob):
    """A job that does nothing but append a string to a list."""

    implements(IRunnableJob)

    JOB_COMPLETIONS = []

    def __init__(self, completion_message, oops_recipients=None):
        self.message = completion_message
        self.job = Job()
        self.oops_recipients = oops_recipients
        if self.oops_recipients is None:
            self.oops_recipients = []

    def run(self):
        NullJob.JOB_COMPLETIONS.append(self.message)

    def getOopsRecipients(self):
        return self.oops_recipients

    def getOperationDescription(self):
        return 'appending a string to a list'


class TestJobRunner(TestCaseWithFactory):
    """Ensure JobRunner behaves as expected."""

    layer = LaunchpadZopelessLayer

    def makeTwoJobs(self):
        """Test fixture.  Create two jobs."""
        return NullJob("job 1"), NullJob("job 2")

    def test_runJob(self):
        """Ensure status is set to completed when a job runs to completion."""
        job_1, job_2 = self.makeTwoJobs()
        runner = JobRunner(job_1)
        runner.runJob(job_1)
        self.assertEqual(JobStatus.COMPLETED, job_1.job.status)
        self.assertEqual([job_1], runner.completed_jobs)

    def test_runAll(self):
        """Ensure runAll works in the normal case."""
        job_1, job_2 = self.makeTwoJobs()
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        self.assertEqual(JobStatus.COMPLETED, job_1.job.status)
        self.assertEqual(JobStatus.COMPLETED, job_2.job.status)
        msg1 = NullJob.JOB_COMPLETIONS.pop()
        msg2 = NullJob.JOB_COMPLETIONS.pop()
        self.assertEqual(msg1, "job 2")
        self.assertEqual(msg2, "job 1")
        self.assertEqual([job_1, job_2], runner.completed_jobs)

    def test_runAll_skips_lease_failures(self):
        """Ensure runAll skips jobs whose leases can't be acquired."""
        last_oops = errorlog.globalErrorUtility.getLastOopsReport()
        job_1, job_2 = self.makeTwoJobs()
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
        job_1, job_2 = self.makeTwoJobs()
        def raiseError():
            # Ensure that jobs which call transaction.abort work, too.
            transaction.abort()
            raise Exception('Fake exception.  Foobar, I say!')
        job_1.run = raiseError
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        self.assertEqual([], pop_notifications())
        self.assertEqual([job_2], runner.completed_jobs)
        self.assertEqual([job_1], runner.incomplete_jobs)
        self.assertEqual(JobStatus.FAILED, job_1.job.status)
        self.assertEqual(JobStatus.COMPLETED, job_2.job.status)
        reporter = errorlog.globalErrorUtility
        oops = reporter.getLastOopsReport()
        self.assertIn('Fake exception.  Foobar, I say!', oops.tb_text)

    def test_runAll_mails_oopses(self):
        """Email interested parties about OOPses."""
        job_1, job_2 = self.makeTwoJobs()
        def raiseError():
            # Ensure that jobs which call transaction.abort work, too.
            transaction.abort()
            raise Exception('Fake exception.  Foobar, I say!')
        job_1.run = raiseError
        job_1.oops_recipients = ['jrandom@example.org']
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        (notification,) = pop_notifications()
        reporter = errorlog.globalErrorUtility
        oops = reporter.getLastOopsReport()
        self.assertIn(
            'Launchpad encountered an internal error during the following'
            ' operation: appending a string to a list.  It was logged with id'
            ' %s.  Sorry for the inconvenience.' % oops.id,
            notification.get_payload(decode=True))
        self.assertNotIn('Fake exception.  Foobar, I say!',
                         notification.get_payload(decode=True))

    def test_runAll_requires_IRunnable(self):
        """Supplied classes must implement IRunnableJob.

        If they don't, we get a TypeError.  If they do, then we get an
        AttributeError, because we don't actually implement the interface.
        """
        runner = JobRunner([object()])
        self.assertRaises(TypeError, runner.runAll)
        class Runnable:
            implements(IRunnableJob)
        runner = JobRunner([Runnable()])
        self.assertRaises(AttributeError, runner.runAll)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
