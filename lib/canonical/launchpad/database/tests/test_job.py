# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import datetime
import time
from unittest import TestLoader

import pytz
from canonical.database.constants import UTC_NOW
from canonical.testing import LaunchpadZopelessLayer
from storm.locals import Store

from canonical.launchpad.database import InvalidTransition, Job, JobDependency
from canonical.launchpad.interfaces import IJob, JobStatus
from canonical.launchpad.testing import TestCase
from canonical.launchpad.webapp.testing import verifyObject


class TestJob(TestCase):

    layer = LaunchpadZopelessLayer

    def test_implements_IJob(self):
        verifyObject(IJob, Job())

    def test_dependencies(self):
        job1 = Job()
        job2 = Job()
        job2.prerequisites.add(job1)
        self.assertTrue(job2 in job1.dependants)

    def test_destroySelf_of_prerequisite(self):
        job1 = Job()
        job2 = Job()
        job2.prerequisites.add(job1)
        job1.destroySelf()
        self.assertEqual(0, job2.prerequisites.count())

    def test_destroySelf_of_dependant(self):
        job1 = Job()
        job2 = Job()
        job2.dependants.add(job1)
        job1.destroySelf()
        self.assertEqual(0, job2.dependants.count())

    def test_default_status(self):
        job = Job()
        self.assertEqual(job.status, JobStatus.WAITING)

    def test_start(self):
        job = Job(date_ended=UTC_NOW)
        self.assertEqual(None, job.date_started)
        self.assertNotEqual(None, job.date_ended)
        job.start()
        self.assertNotEqual(None, job.date_started)
        self.assertEqual(None, job.date_ended)
        self.assertEqual(job.status, JobStatus.RUNNING)

    def test_start_increments_attempt_count(self):
        job = Job(date_ended=UTC_NOW)
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
        self.assertEqual(None, job.date_ended)
        job.complete()
        self.assertNotEqual(None, job.date_ended)
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
        self.assertEqual(None, job.date_ended)
        job.fail()
        self.assertNotEqual(None, job.date_ended)
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
        self.assertEqual(None, job.date_ended)
        job.queue()
        self.assertNotEqual(None, job.date_ended)
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


class TestJobDependency(TestCase):

    layer = LaunchpadZopelessLayer

    def test_correct_columns(self):
        job1 = Job()
        job2 = Job()
        JobDependency(prerequisite=job1.id, dependant=job2.id)
        self.assertTrue(job1 in job2.prerequisites)
        self.assertTrue(job1 not in job2.dependants)
        self.assertTrue(job2 in job1.dependants)
        self.assertTrue(job2 not in job1.prerequisites)

    def test_ready_jobs(self):
        job = Job()
        self.assertEqual(
            [(job.id,)], list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_started(self):
        job = Job(status=JobStatus.RUNNING)
        self.assertEqual(
            [], list(Store.of(job).execute(Job.ready_jobs)))

    def test_ready_jobs_waiting_prereqisite(self):
        job = Job()
        prerequisite = Job()
        job.addPrerequisite(prerequisite)
        self.assertEqual(
            [(prerequisite.id,)], list(Store.of(job).execute(Job.ready_jobs)))

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

    def test_blocked_jobs(self):
        job = Job()
        prerequisite_1 = Job()
        job.addPrerequisite(prerequisite_1)
        prerequisite_2 = Job()
        job.addPrerequisite(prerequisite_2)
        self.assertEqual(
            [(job.id,)], list(Store.of(job).execute(Job.blocked_jobs)))
        prerequisite_1.status = JobStatus.COMPLETED
        self.assertEqual(
            [(job.id,)], list(Store.of(job).execute(Job.blocked_jobs)))
        prerequisite_2.status = JobStatus.FAILED
        self.assertEqual(
            [], list(Store.of(job).execute(Job.blocked_jobs)))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
