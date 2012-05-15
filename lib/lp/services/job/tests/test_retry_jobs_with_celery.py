# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for running jobs via Celery."""


import transaction
from lazr.delegates import delegates
from zope.interface import implements

from lp.services.config import config
from lp.services.database.lpstorm import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import (
    IJob,
    IRunnableJob,
    )
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.job.tests import block_on_job
from lp.testing import TestCaseWithFactory
from lp.testing.layers import CeleryJobLayer


class TestJob(BaseRunnableJob):
    """A dummy job."""

    implements(IRunnableJob)
    delegates(IJob, 'job')

    config = config.launchpad

    def __init__(self, job_id=None):
        if job_id is not None:
            store = IStore(Job)
            self.job = store.find(Job, id=job_id)[0]
        else:
            self.job = Job(max_retries=2)

    def run(self):
        pass

    @classmethod
    def makeInstance(cls, ujob_id):
        return cls(ujob_id)

    @classmethod
    def getDBClass(cls):
        return cls


class RetryException(Exception):
    """An exception used as a retry exception in TestJobWithRetryError."""

class TestJobWithRetryError(TestJob):
    """A dummy job."""

    retry_error_types = (RetryException, )

    def run(self):
        if self.job.attempt_count < 2:
            raise RetryException


class TestRetryJobsViaCelery(TestCaseWithFactory):
    """Tests for running jobs via Celery."""

    layer = CeleryJobLayer

    def test_TestJob(self):
        # TestJob can be run via Celery.
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'TestJob'
        }))
        with block_on_job(self):
            job = TestJob()
            job.celeryRunOnCommit()
            job_id = job.job_id
            transaction.commit()
        store = IStore(Job)
        dbjob = store.find(Job, id=job_id)[0]
        self.assertEqual(JobStatus.COMPLETED, dbjob.status)

    def test_jobs_with_retry_exceptions_are_queued_again(self):
        # TestJob can be run via Celery.
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'TestJobWithRetryError'
        }))
        with block_on_job(self):
            job = TestJobWithRetryError()
            job.celeryRunOnCommit()
            job_id = job.job_id
            import pdb; pdb.set_trace()
            transaction.commit()
            import pdb; pdb.set_trace()
        store = IStore(Job)
        store.invalidate()
        dbjob = store.find(Job, id=job_id)[0]
        self.assertEqual(2, dbjob.attempt_count)
        self.assertEqual(JobStatus.COMPLETED, dbjob.status)
