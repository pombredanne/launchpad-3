# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from cStringIO import StringIO
import sys
from time import (
    sleep,
    time,
    )
from lazr.jobrunner.bin.clear_queues import clear_queues
from lp.code.model.branchjob import BranchScanJob
from lp.scripts.helpers import TransactionFreeOperation
from lp.services.features.testing import FeatureFixture
from lp.services.job.tests import (
    celeryd,
    drain_celery_queues,
    monitor_celery,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.layers import ZopelessAppServerLayer


class TestRunMissingJobs(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def setUp(self):
        super(TestRunMissingJobs, self).setUp()
        from lp.services.job.celeryjob import (
            find_missing_ready,
            RunMissingReady,
        )
        self.find_missing_ready = find_missing_ready
        self.RunMissingReady = RunMissingReady

    def createMissingJob(self):
        job = BranchScanJob.create(self.factory.makeBranch())
        self.addCleanup(drain_celery_queues)
        return job

    # XXX wgrant 2012-06-27 bug=1018235: Disabled due to intermittent
    # failure on buildbot.
    def disabled_test_find_missing_ready(self):
        """A job which is ready but not queued is "missing"."""
        job = self.createMissingJob()
        self.assertEqual([job], self.find_missing_ready(BranchScanJob))
        job.runViaCelery()
        self.assertEqual([], self.find_missing_ready(BranchScanJob))
        drain_celery_queues()
        self.assertEqual([job], self.find_missing_ready(BranchScanJob))

    def test_run_missing_ready_not_enabled(self):
        """run_missing_ready does nothing if the class isn't enabled."""
        self.createMissingJob()
        with monitor_celery() as responses:
            with dbuser('run_missing_ready'):
                with TransactionFreeOperation.require():
                    self.RunMissingReady().run(_no_init=True)
        self.assertEqual([], responses)

    def test_run_missing_ready(self):
        """run_missing_ready requests the job to run if not scheduled."""
        self.createMissingJob()
        self.useFixture(
            FeatureFixture({'jobs.celery.enabled_classes': 'BranchScanJob'}))
        with monitor_celery() as responses:
            with dbuser('run_missing_ready'):
                with TransactionFreeOperation.require():
                    self.RunMissingReady().run(_no_init=True)
        self.assertEqual(1, len(responses))

    def test_run_missing_ready_does_not_return_results(self):
        """The celerybeat task run_missing_ready does not create a
        result queue."""
        from lazr.jobrunner.celerytask import list_queued
        from lp.services.job.tests.celery_helpers import noop
        job_queue_name = 'celerybeat'
        request = self.RunMissingReady().apply_async(
            kwargs={'_no_init': True}, queue=job_queue_name)
        self.assertTrue(request.task_id.startswith('RunMissingReady_'))
        result_queue_name = request.task_id.replace('-', '')
        # Paranoia check: This test intends to prove that a Celery
        # result queue for the task created above will _not_ be created.
        # This would also happen when "with celeryd()" would do nothing.
        # So let's be sure that a task is queued...
        # Give the system some time to deliver the message
        for x in range(10):
            if list_queued(self.RunMissingReady.app, [job_queue_name]) > 0:
                break
            sleep(1)
        self.assertEqual(
            1, len(list_queued(self.RunMissingReady.app, [job_queue_name])))
        # Wait at most 60 seconds for celeryd to start and process
        # the task.
        with celeryd(job_queue_name):
            # Due to FIFO ordering, this will only return after
            # RunMissingReady has finished.
            noop.apply_async(queue=job_queue_name).wait(60)
        # But now the message has been consumed by celeryd.
        self.assertEqual(
            0, len(list_queued(self.RunMissingReady.app, [job_queue_name])))
        # No result queue was created for the task.
        try:
            real_stdout = sys.stdout
            real_stderr = sys.stderr
            sys.stdout = fake_stdout = StringIO()
            sys.stderr = fake_stderr = StringIO()
            clear_queues(
                ['script_name', '-c', 'lp.services.job.celeryconfig',
                 result_queue_name])
        finally:
            sys.stdout = real_stdout
            sys.stderr = real_stderr
        fake_stdout = fake_stdout.getvalue()
        fake_stderr = fake_stderr.getvalue()
        self.assertEqual(
            '', fake_stdout,
            "Unexpected output from clear_queues:\n"
            "stdout: %r\n"
            "stderr: %r" % (fake_stdout, fake_stderr))
        self.assertEqual(
            "NOT_FOUND - no queue '%s' in vhost '/'\n" % result_queue_name,
            fake_stderr,
            "Unexpected output from clear_queues:\n"
            "stdout: %r\n"
            "stderr: %r" % (fake_stdout, fake_stderr))
