# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for job-running facilities."""


from __future__ import with_statement

import sys
from time import sleep
from unittest import TestLoader

import transaction
from canonical.testing import LaunchpadZopelessLayer
from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility
from zope.interface import implements

from lp.testing.mail_helpers import pop_notifications
from lp.services.job.runner import (
    JobRunner, BaseRunnableJob, JobRunnerProcess, TwistedJobRunner
)
from lp.services.job.interfaces.job import JobStatus, IRunnableJob
from lp.services.job.model.job import Job
from lp.testing import TestCaseWithFactory
from canonical.launchpad.webapp import errorlog


class NullJob(BaseRunnableJob):
    """A job that does nothing but append a string to a list."""

    implements(IRunnableJob)

    JOB_COMPLETIONS = []

    def __init__(self, completion_message, oops_recipients=None,
                 error_recipients=None):
        self.message = completion_message
        self.job = Job()
        self.oops_recipients = oops_recipients
        if self.oops_recipients is None:
            self.oops_recipients = []
        self.error_recipients = error_recipients
        if self.error_recipients is None:
            self.error_recipients = []

    def run(self):
        NullJob.JOB_COMPLETIONS.append(self.message)

    def getOopsRecipients(self):
        return self.oops_recipients

    def getOopsVars(self):
        return [('foo', 'bar')]

    def getErrorRecipients(self):
        return self.error_recipients

    def getOperationDescription(self):
        return 'appending a string to a list'


class RaisingJobException(Exception):
    """Raised by the RaisingJob when run."""


class RaisingJob(NullJob):
    """A job that raises when it runs."""

    def run(self):
        raise RaisingJobException(self.message)


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
        self.assertEqual(1, len(oops.req_vars))
        self.assertEqual("{'foo': 'bar'}", oops.req_vars[0][1])

    def test_oops_messages_used_when_handling(self):
        """Oops messages should appear even when exceptions are handled."""
        job_1, job_2 = self.makeTwoJobs()
        def handleError():
            reporter = errorlog.globalErrorUtility
            try:
                raise ValueError('Fake exception.  Foobar, I say!')
            except ValueError:
                reporter.handling(sys.exc_info())
        job_1.run = handleError
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        reporter = getUtility(IErrorReportingUtility)
        oops = reporter.getLastOopsReport()
        self.assertEqual(1, len(oops.req_vars))
        self.assertEqual("{'foo': 'bar'}", oops.req_vars[0][1])

    def test_runAll_aborts_transaction_on_error(self):
        """runAll should abort the transaction on oops."""

        class DBAlterJob(NullJob):

            def __init__(self):
                super(DBAlterJob, self).__init__('')

            def run(self):
                self.job.log = 'hello'
                raise ValueError

        job = DBAlterJob()
        runner = JobRunner([job])
        runner.runAll()
        # If the transaction was committed, job.log == 'hello'.  If it was
        # aborted, it is None.
        self.assertIs(None, job.job.log)

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
        self.assertEqual('Launchpad internal error', notification['subject'])

    def test_runAll_mails_user_errors(self):
        """User errors should be mailed out without oopsing.

        User errors are identified by the RunnableJob.user_error_types
        attribute.  They do not cause an oops to be recorded, and their
        error messages are mailed to interested parties verbatim.
        """
        job_1, job_2 = self.makeTwoJobs()
        class ExampleError(Exception):
            pass
        def raiseError():
            raise ExampleError('Fake exception.  Foobar, I say!')
        job_1.run = raiseError
        job_1.user_error_types = (ExampleError,)
        job_1.error_recipients = ['jrandom@example.org']
        runner = JobRunner([job_1, job_2])
        reporter = errorlog.globalErrorUtility
        old_oops = reporter.getLastOopsReport()
        runner.runAll()
        self.assertNoNewOops(old_oops)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        body = notifications[0].get_payload(decode=True)
        self.assertEqual(
            'Launchpad encountered an error during the following operation:'
            ' appending a string to a list.  Fake exception.  Foobar, I say!',
            body)
        self.assertEqual(
            'Launchpad error while appending a string to a list',
            notifications[0]['subject'])

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

    def test_runJob_records_failure(self):
        """When a job fails, the failure needs to be recorded."""
        job = RaisingJob('boom')
        runner = JobRunner([job])
        self.assertRaises(RaisingJobException, runner.runJob, job)
        # Abort the transaction to confirm that the update of the job status
        # has been committed.
        transaction.abort()
        self.assertEqual(JobStatus.FAILED, job.job.status)


class StuckJob(BaseRunnableJob):
    """Simulation of a job that stalls."""
    implements(IRunnableJob)

    done = False

    @classmethod
    def iterReady(cls):
        if not cls.done:
            yield StuckJob()
        cls.done = True

    @staticmethod
    def get(id):
        return StuckJob()

    def __init__(self):
        self.id = 1
        self.job = Job()

    def acquireLease(self):
        # Must be enough time for the setup to complete and runJobHandleError
        # to be called.  7 was the minimum that worked on my computer.
        # -- abentley
        return self.job.acquireLease(10)

    def run(self):
        sleep(30)


class StuckJobProcess(JobRunnerProcess):

    job_class = StuckJob


StuckJob.amp = StuckJobProcess


class ListLogger:

    def __init__(self):
        self.entries = []

    def info(self, input):
        self.entries.append(input)


class TestTwistedJobRunner(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    # XXX: salgado, 2010-01-11, bug=505913: Disabled because of intermittent
    # failures.
    def disabled_test_timeout(self):
        """When a job exceeds its lease, an exception is raised."""
        logger = ListLogger()
        runner = TwistedJobRunner.runFromSource(StuckJob, logger)
        self.assertEqual([], runner.completed_jobs)
        self.assertEqual(1, len(runner.incomplete_jobs))
        oops = errorlog.globalErrorUtility.getLastOopsReport()
        expected = [
            'Running through Twisted.', 'Job resulted in OOPS: %s' % oops.id]
        self.assertEqual(expected, logger.entries)
        self.assertEqual('TimeoutError', oops.type)
        self.assertIn('Job ran too long.', oops.value)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
