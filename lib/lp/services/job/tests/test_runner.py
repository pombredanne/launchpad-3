# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for job-running facilities."""

import logging
import sys
from textwrap import dedent
from time import sleep

import transaction
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.webapp import errorlog
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.code.interfaces.branchmergeproposal import IUpdatePreviewDiffJobSource
from lp.services.job.interfaces.job import (
    IRunnableJob,
    JobStatus,
    )
from lp.services.job.model.job import Job
from lp.services.job.runner import (
    BaseRunnableJob,
    JobCronScript,
    JobRunner,
    TwistedJobRunner,
    )
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.testing import (
    TestCaseWithFactory,
    ZopeTestInSubProcess,
    )
from lp.testing.mail_helpers import pop_notifications


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


class RaisingJobUserError(NullJob):
    """A job that raises a user error when it runs."""

    user_error_types = (RaisingJobException, )

    def run(self):
        raise RaisingJobException(self.message)


class RaisingJobRaisingNotifyOops(NullJob):
    """A job that raises when it runs, and when calling notifyOops."""

    def run(self):
        raise RaisingJobException(self.message)

    def notifyOops(self, oops):
        raise RaisingJobException('oops notifying oops')


class RaisingJobRaisingNotifyUserError(NullJob):
    """A job that raises when it runs, and when notifying user errors."""

    user_error_types = (RaisingJobException, )

    def run(self):
        raise RaisingJobException(self.message)

    def notifyUserError(self, error):
        raise RaisingJobException('oops notifying users')


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
        job_1, job_2 = self.makeTwoJobs()
        job_2.job.acquireLease()
        runner = JobRunner([job_1, job_2])
        runner.runAll()
        self.assertEqual(JobStatus.COMPLETED, job_1.job.status)
        self.assertEqual(JobStatus.WAITING, job_2.job.status)
        self.assertEqual([job_1], runner.completed_jobs)
        self.assertEqual([job_2], runner.incomplete_jobs)
        self.assertEqual([], self.oopses)

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
        oops = self.oopses[-1]
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
        oops = self.oopses[-1]
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
        oops = self.oopses[-1]
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
        runner.runAll()
        self.assertEqual([], self.oopses)
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

    def test_runJobHandleErrors_oops_generated(self):
        """The handle errors method records an oops for raised errors."""
        job = RaisingJob('boom')
        runner = JobRunner([job])
        runner.runJobHandleError(job)
        self.assertEqual(1, len(self.oopses))

    def test_runJobHandleErrors_user_error_no_oops(self):
        """If the job raises a user error, there is no oops."""
        job = RaisingJobUserError('boom')
        runner = JobRunner([job])
        runner.runJobHandleError(job)
        self.assertEqual(0, len(self.oopses))

    def test_runJobHandleErrors_oops_generated_notify_fails(self):
        """A second oops is logged if the notification of the oops fails."""
        job = RaisingJobRaisingNotifyOops('boom')
        runner = JobRunner([job])
        runner.runJobHandleError(job)
        self.assertEqual(2, len(self.oopses))

    def test_runJobHandleErrors_oops_generated_user_notify_fails(self):
        """A second oops is logged if the notification of the oops fails.

        In this test case the error is a user expected error, so the
        notifyUserError is called, and in this case the notify raises too.
        """
        job = RaisingJobRaisingNotifyUserError('boom')
        runner = JobRunner([job])
        runner.runJobHandleError(job)
        self.assertEqual(1, len(self.oopses))


class StuckJob(BaseRunnableJob):
    """Simulation of a job that stalls."""
    implements(IRunnableJob)

    done = False

    @classmethod
    def iterReady(cls):
        if not cls.done:
            yield StuckJob(1)
            yield StuckJob(2)
        cls.done = True

    @staticmethod
    def get(id):
        return StuckJob(id)

    def __init__(self, id):
        self.id = id
        self.job = Job()

    def acquireLease(self):
        if self.id == 2:
            lease_length = 1
        else:
            lease_length = 10000
        return self.job.acquireLease(lease_length)

    def run(self):
        if self.id == 2:
            sleep(30)
        else:
            store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
            assert (
                'user=branchscanner' in store._connection._raw_connection.dsn)


class TestTwistedJobRunner(ZopeTestInSubProcess, TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_timeout(self):
        """When a job exceeds its lease, an exception is raised.

        Unfortunately, timeouts include the time it takes for the zope
        machinery to start up, so we run a job that will not time out first,
        followed by a job that is sure to time out.
        """
        logger = BufferLogger()
        logger.setLevel(logging.INFO)
        runner = TwistedJobRunner.runFromSource(
            StuckJob, 'branchscanner', logger)

        self.assertEqual(1, len(runner.completed_jobs))
        self.assertEqual(1, len(runner.incomplete_jobs))
        oops = errorlog.globalErrorUtility.getLastOopsReport()
        self.assertEqual(dedent("""\
             INFO Running through Twisted.
             INFO Job resulted in OOPS: %s
             """) % oops.id, logger.getLogBuffer())
        self.assertEqual('TimeoutError', oops.type)
        self.assertIn('Job ran too long.', oops.value)


class TestJobCronScript(ZopeTestInSubProcess, TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_configures_oops_handler(self):
        """JobCronScript.main should configure the global error utility."""

        class DummyRunner:

            @classmethod
            def runFromSource(cls, source, dbuser, logger):
                expected_config = errorlog.ErrorReportingUtility()
                expected_config.configure('merge_proposal_jobs')
                # Check that the unique oops token was applied.
                self.assertEqual(
                    errorlog.globalErrorUtility.oops_prefix,
                    expected_config.oops_prefix)
                return cls()

            completed_jobs = []
            incomplete_jobs = []

        class JobCronScriptSubclass(JobCronScript):
            config_name = 'merge_proposal_jobs'
            source_interface = IUpdatePreviewDiffJobSource

            def __init__(self):
                super(JobCronScriptSubclass, self).__init__(
                    DummyRunner, test_args=[])
                self.logger = DevNullLogger()

        old_errorlog = errorlog.globalErrorUtility
        try:
            errorlog.globalErrorUtility = errorlog.ErrorReportingUtility()
            cronscript = JobCronScriptSubclass()
            cronscript.main()
        finally:
            errorlog.globalErrorUtility = old_errorlog
