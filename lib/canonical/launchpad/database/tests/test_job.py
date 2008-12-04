# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import datetime
import time
from unittest import TestLoader

import pytz
from canonical.database.constants import UTC_NOW
from canonical.testing import LaunchpadZopelessLayer
from storm.locals import Store

from canonical.launchpad.database.job import (
    InvalidTransition, Job, LeaseHeld)
from canonical.launchpad.interfaces import IJob, JobStatus
from canonical.launchpad.testing import TestCase
from canonical.launchpad.webapp.testing import verifyObject


class TestJob(TestCase):

    layer = LaunchpadZopelessLayer

    def test_implements_IJob(self):
        verifyObject(IJob, Job())

    def test_default_status(self):
        job = Job()
        self.assertEqual(job.status, JobStatus.WAITING)

    def test_start(self):
        job = Job(date_finished=UTC_NOW)
        self.assertEqual(None, job.date_started)
        self.assertNotEqual(None, job.date_finished)
        job.start()
        self.assertNotEqual(None, job.date_started)
        self.assertEqual(None, job.date_finished)
        self.assertEqual(job.status, JobStatus.RUNNING)

    def test_start_increments_attempt_count(self):
        job = Job(date_finished=UTC_NOW)
        self.assertEqual(0, job.attempt_count)
        job.start()
        self.assertEqual(1, job.attempt_count)
        job.queue()
        job.start()
        self.assertEqual(2, job.attempt_count)

    def test_start_when_completed(self):
        job = Job(status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.start)

    def test_start_when_failed(self):
        job = Job(status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.start)

    def test_start_when_running(self):
        job = Job(status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.start)

    def test_complete(self):
        job = Job(status=JobStatus.RUNNING)
        self.assertEqual(None, job.date_finished)
        job.complete()
        self.assertNotEqual(None, job.date_finished)
        self.assertEqual(job.status, JobStatus.COMPLETED)

    def test_complete_waiting(self):
        job = Job(status=JobStatus.WAITING)
        self.assertRaises(InvalidTransition, job.complete)

    def test_complete_completed(self):
        job = Job(status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.complete)

    def test_complete_failed(self):
        job = Job(status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.complete)

    def test_fail(self):
        job = Job(status=JobStatus.RUNNING)
        self.assertEqual(None, job.date_finished)
        job.fail()
        self.assertNotEqual(None, job.date_finished)
        self.assertEqual(job.status, JobStatus.FAILED)

    def test_fail_waiting(self):
        job = Job(status=JobStatus.WAITING)
        self.assertRaises(InvalidTransition, job.fail)

    def test_fail_completed(self):
        job = Job(status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.fail)

    def test_fail_failed(self):
        job = Job(status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.fail)

    def test_queue(self):
        job = Job(status=JobStatus.RUNNING)
        self.assertEqual(None, job.date_finished)
        job.queue()
        self.assertNotEqual(None, job.date_finished)
        self.assertEqual(job.status, JobStatus.WAITING)

    def test_queue_completed(self):
        job = Job(status=JobStatus.COMPLETED)
        self.assertRaises(InvalidTransition, job.queue)

    def test_queue_waiting(self):
        job = Job(status=JobStatus.WAITING)
        self.assertRaises(InvalidTransition, job.queue)

    def test_queue_failed(self):
        job = Job(status=JobStatus.FAILED)
        self.assertRaises(InvalidTransition, job.queue)


class TestReadiness(TestCase):

    layer = LaunchpadZopelessLayer

    def test_ready_jobs(self):
        job = Job()
        self.assertEqual(
            [(job.id,)], list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_started(self):
        job = Job(status=JobStatus.RUNNING)
        self.assertEqual(
            [], list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_lease_expired(self):
        UNIX_EPOCH=datetime.datetime.fromtimestamp(0, pytz.timezone('UTC'))
        job = Job(lease_expires=UNIX_EPOCH)
        self.assertEqual(
            [(job.id,)], list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_lease_in_future(self):
        future=datetime.datetime.fromtimestamp(
            time.time() + 1000, pytz.timezone('UTC'))
        job = Job(lease_expires=future)
        self.assertEqual([], list(Store.of(job).execute(Job.ready_jobs)))

    def test_acquireLease(self):
        job = Job()
        job.acquireLease()
        self.assertIsNot(None, job.lease_expires)

    def test_acquireHeldLease(self):
        job = Job()
        job.acquireLease()
        self.assertRaises(LeaseHeld, job.acquireLease)

    def test_acquireStaleLease(self):
        job = Job()
        job.acquireLease(-1)
        job.acquireLease()


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
