# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime
import time
from unittest import TestLoader

import pytz
from canonical.database.constants import UTC_NOW
from canonical.testing import LaunchpadZopelessLayer
from storm.locals import Store

from canonical.launchpad.database.job import (
    InvalidTransition, Job, LeaseHeld)
from canonical.launchpad.interfaces.job import IJob, JobStatus
from lp.testing import TestCase
from canonical.launchpad.webapp.testing import verifyObject


class TestJob(TestCase):
    """Ensure Job behaves as intended."""

    layer = LaunchpadZopelessLayer

    def test_implements_IJob(self):
        """Job should implement IJob."""
        verifyObject(IJob, Job())

    def test_default_status(self):
        """The default status should be WAITING."""
        job = Job()
        self.assertEqual(job.status, JobStatus.WAITING)

    def test_start(self):
        """Job.start should update the object appropriately.

        It should set date_started, clear date_finished, and set the status to
        RUNNING."""
        job = Job(date_finished=UTC_NOW)
        self.assertEqual(None, job.date_started)
        self.assertNotEqual(None, job.date_finished)
        job.start()
        self.assertNotEqual(None, job.date_started)
        self.assertEqual(None, job.date_finished)
        self.assertEqual(job.status, JobStatus.RUNNING)

    def test_start_increments_attempt_count(self):
        """Job.start should increment the attempt count."""
        job = Job(date_finished=UTC_NOW)
        self.assertEqual(0, job.attempt_count)
        job.start()
        self.assertEqual(1, job.attempt_count)
        job.queue()
        job.start()
        self.assertEqual(2, job.attempt_count)

    def test_start_when_completed_is_invalid(self):
        """When a job is completed, attempting to start is invalid."""
        job = Job(_status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.start)

    def test_start_when_failed_is_invalid(self):
        """When a job is failed, attempting to start is invalid."""
        job = Job(_status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.start)

    def test_start_when_running_is_invalid(self):
        """When a job is running, attempting to start is invalid."""
        job = Job(_status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.start)

    def test_complete(self):
        """Job.complete should update the Job appropriately.

        It should set date_finished and set the job status to COMPLETED.
        """
        job = Job(_status=JobStatus.RUNNING)
        self.assertEqual(None, job.date_finished)
        job.complete()
        self.assertNotEqual(None, job.date_finished)
        self.assertEqual(job.status, JobStatus.COMPLETED)

    def test_complete_when_waiting_is_invalid(self):
        """When a job is waiting, attempting to complete is invalid."""
        job = Job(_status=JobStatus.WAITING)
        self.assertRaises(InvalidTransition, job.complete)

    def test_complete_when_completed_is_invalid(self):
        """When a job is completed, attempting to complete is invalid."""
        job = Job(_status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.complete)

    def test_complete_when_failed_is_invalid(self):
        """When a job is failed, attempting to complete is invalid."""
        job = Job(_status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.complete)

    def test_fail(self):
        """Job.fail should update the Job appropriately.

        It should set date_finished and set the job status to FAILED.
        """
        job = Job(_status=JobStatus.RUNNING)
        self.assertEqual(None, job.date_finished)
        job.fail()
        self.assertNotEqual(None, job.date_finished)
        self.assertEqual(job.status, JobStatus.FAILED)

    def test_fail_when_waiting_is_invalid(self):
        """When a job is waiting, attempting to fail is invalid."""
        job = Job(_status=JobStatus.WAITING)
        self.assertRaises(InvalidTransition, job.fail)

    def test_fail_when_completed_is_invalid(self):
        """When a job is completed, attempting to fail is invalid."""
        job = Job(_status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.fail)

    def test_fail_when_failed_is_invalid(self):
        """When a job is failed, attempting to fail is invalid."""
        job = Job(_status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.fail)

    def test_queue(self):
        """Job.queue should update the job appropriately.

        It should set date_finished, and set status to WAITING.
        """
        job = Job(_status=JobStatus.RUNNING)
        self.assertEqual(None, job.date_finished)
        job.queue()
        self.assertNotEqual(None, job.date_finished)
        self.assertEqual(job.status, JobStatus.WAITING)

    def test_queue_when_completed_is_invalid(self):
        """When a job is completed, attempting to queue is invalid."""
        job = Job(_status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.queue)

    def test_queue_when_waiting_is_invalid(self):
        """When a job is waiting, attempting to queue is invalid."""
        job = Job(_status=JobStatus.WAITING)
        self.assertRaises(InvalidTransition, job.queue)

    def test_queue_when_failed_is_invalid(self):
        """When a job is failed, attempting to queue is invalid."""
        job = Job(_status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.queue)


class TestReadiness(TestCase):
    """Test the implementation of readiness."""

    layer = LaunchpadZopelessLayer

    def test_ready_jobs(self):
        """Job.ready_jobs should include new jobs."""
        job = Job()
        self.assertEqual(
            [(job.id,)], list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_started(self):
        """Job.ready_jobs should not jobs that have been started."""
        job = Job(_status=JobStatus.RUNNING)
        self.assertEqual(
            [], list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_lease_expired(self):
        """Job.ready_jobs should include jobs with expired leases."""
        UNIX_EPOCH = datetime.fromtimestamp(0, pytz.timezone('UTC'))
        job = Job(lease_expires=UNIX_EPOCH)
        self.assertEqual(
            [(job.id,)], list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_lease_in_future(self):
        """Job.ready_jobs should not include jobs with active leases."""
        future = datetime.fromtimestamp(
            time.time() + 1000, pytz.timezone('UTC'))
        job = Job(lease_expires=future)
        self.assertEqual([], list(Store.of(job).execute(Job.ready_jobs)))

    def test_acquireLease(self):
        """Job.acquireLease should set job.lease_expires."""
        job = Job()
        job.acquireLease()
        self.assertIsNot(None, job.lease_expires)

    def test_acquireHeldLease(self):
        """Job.acquireLease should raise LeaseHeld if repeated."""
        job = Job()
        job.acquireLease()
        self.assertRaises(LeaseHeld, job.acquireLease)

    def test_acquireStaleLease(self):
        """Job.acquireLease should work when a lease is expired."""
        job = Job()
        job.acquireLease(-1)
        job.acquireLease()


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
