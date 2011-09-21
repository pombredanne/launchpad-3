# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime
import time

import pytz
from storm.locals import Store

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.services.job.interfaces.job import (
    IJob,
    JobStatus,
    )
from lp.services.job.model.job import (
    InvalidTransition,
    Job,
    LeaseHeld,
    )
from lp.services.longpoll.testing import (
    capture_longpoll_emissions,
    LongPollEventRecord,
    )
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )


class TestJob(TestCaseWithFactory):
    """Ensure Job behaves as intended."""

    layer = LaunchpadZopelessLayer

    def test_implements_IJob(self):
        """Job should implement IJob."""
        verifyObject(IJob, Job())

    def test_default_status(self):
        """The default status should be WAITING."""
        job = Job()
        self.assertEqual(job.status, JobStatus.WAITING)

    def test_stores_requester(self):
        job = Job()
        random_joe = self.factory.makePerson()
        job.requester = random_joe
        self.assertEqual(random_joe, job.requester)

    def test_createMultiple_creates_requested_number_of_jobs(self):
        job_ids = list(Job.createMultiple(IStore(Job), 3))
        self.assertEqual(3, len(job_ids))
        self.assertEqual(3, len(set(job_ids)))

    def test_createMultiple_returns_valid_job_ids(self):
        job_ids = list(Job.createMultiple(IStore(Job), 3))
        store = IStore(Job)
        for job_id in job_ids:
            self.assertIsNot(None, store.get(Job, job_id))

    def test_createMultiple_sets_status_to_WAITING(self):
        store = IStore(Job)
        job = store.get(Job, Job.createMultiple(store, 1)[0])
        self.assertEqual(JobStatus.WAITING, job.status)

    def test_createMultiple_sets_requester(self):
        store = IStore(Job)
        requester = self.factory.makePerson()
        job = store.get(Job, Job.createMultiple(store, 1, requester)[0])
        self.assertEqual(requester, job.requester)

    def test_createMultiple_defaults_requester_to_None(self):
        store = IStore(Job)
        job = store.get(Job, Job.createMultiple(store, 1)[0])
        self.assertEqual(None, job.requester)

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

    def test_suspend(self):
        """A job that is in the WAITING state can be suspended."""
        job = Job(_status=JobStatus.WAITING)
        job.suspend()
        self.assertEqual(
            job.status,
            JobStatus.SUSPENDED)

    def test_suspend_when_running(self):
        """When a job is running, attempting to suspend is valid."""
        job = Job(_status=JobStatus.RUNNING)
        job.suspend()
        self.assertEqual(JobStatus.SUSPENDED, job.status)

    def test_suspend_when_completed(self):
        """When a job is completed, attempting to suspend is invalid."""
        job = Job(_status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.suspend)

    def test_suspend_when_failed(self):
        """When a job is failed, attempting to suspend is invalid."""
        job = Job(_status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.suspend)

    def test_resume(self):
        """A job that is suspended can be resumed."""
        job = Job(_status=JobStatus.SUSPENDED)
        job.resume()
        self.assertEqual(
            job.status,
            JobStatus.WAITING)

    def test_resume_clears_lease_expiry(self):
        """A job that resumes should null out the lease_expiry."""
        job = Job(_status=JobStatus.SUSPENDED)
        job.lease_expires = UTC_NOW
        job.resume()
        self.assertIs(None, job.lease_expires)

    def test_resume_when_running(self):
        """When a job is running, attempting to resume is invalid."""
        job = Job(_status=JobStatus.RUNNING)
        self.assertRaises(InvalidTransition, job.resume)

    def test_resume_when_completed(self):
        """When a job is completed, attempting to resume is invalid."""
        job = Job(_status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.resume)

    def test_resume_when_failed(self):
        """When a job is failed, attempting to resume is invalid."""
        job = Job(_status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.resume)

    def test_is_pending(self):
        """is_pending is True when the job can possibly complete."""
        for status in JobStatus.items:
            job = Job(_status=status)
            self.assertEqual(
                status in Job.PENDING_STATUSES, job.is_pending)

    def test_status_change_events(self):
        job = Job()
        with capture_longpoll_emissions() as log:
            job.start()
            job.fail()
        expected = [
            LongPollEventRecord(
                'longpoll.event.job.%d' % job.id,
                {'event_key': 'longpoll.event.job.%s' % job.id,
                 'what': 'modified',
                 'edited_fields': ['status']}),
            LongPollEventRecord(
                'longpoll.event.job.%d' % job.id,
                {'event_key': 'longpoll.event.job.%s' % job.id,
                 'what': 'modified',
                 'edited_fields': ['status']}),
            ]
        self.assertEqual(expected, log)


class TestReadiness(TestCase):
    """Test the implementation of readiness."""

    layer = ZopelessDatabaseLayer

    def _sampleData(self):
        return list(IStore(Job).execute(Job.ready_jobs))

    def test_ready_jobs(self):
        """Job.ready_jobs should include new jobs."""
        preexisting = self._sampleData()
        job = Job()
        self.assertEqual(
            preexisting + [(job.id,)],
            list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_started(self):
        """Job.ready_jobs should not jobs that have been started."""
        preexisting = self._sampleData()
        job = Job(_status=JobStatus.RUNNING)
        self.assertEqual(
            preexisting, list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_lease_expired(self):
        """Job.ready_jobs should include jobs with expired leases."""
        preexisting = self._sampleData()
        UNIX_EPOCH = datetime.fromtimestamp(0, pytz.timezone('UTC'))
        job = Job(lease_expires=UNIX_EPOCH)
        self.assertEqual(
            preexisting + [(job.id,)],
            list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_lease_in_future(self):
        """Job.ready_jobs should not include jobs with active leases."""
        preexisting = self._sampleData()
        future = datetime.fromtimestamp(
            time.time() + 1000, pytz.timezone('UTC'))
        job = Job(lease_expires=future)
        self.assertEqual(
            preexisting, list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_not_jobs_scheduled_in_future(self):
        """Job.ready_jobs does not included jobs scheduled for a time in the
        future.
        """
        preexisting = self._sampleData()
        future = datetime.fromtimestamp(
            time.time() + 1000, pytz.timezone('UTC'))
        job = Job(scheduled_start=future)
        self.assertEqual(
            preexisting, list(Store.of(job).execute(Job.ready_jobs)))

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

    def test_acquireLeaseTimeout(self):
        """Test that getTimeout correctly calculates value from lease.

        The imprecision is because leases are relative to the current time,
        and the current time may have changed by the time we get to
        job.getTimeout() <= 300.
        """
        job = Job()
        job.acquireLease(300)
        self.assertTrue(job.getTimeout() > 0)
        self.assertTrue(job.getTimeout() <= 300)

    def test_acquireLeaseTimeoutExpired(self):
        """Expired leases don't produce negative timeouts."""
        job = Job()
        job.acquireLease(-300)
        self.assertEqual(0, job.getTimeout())
