# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery-specific Job code.

Because celery sets up configuration at import time, code that is not designed
to use Celery may break if this is used.
"""

__metaclass__ = type

__all__ = [
    'CeleryRunJob',
    'CeleryRunJobIgnoreResult',
    ]

from logging import info
import os


os.environ.setdefault('CELERY_CONFIG_MODULE', 'lp.services.job.celeryconfig')
from celery.task import task
from lazr.jobrunner.celerytask import RunJob
from storm.zope.interfaces import IZStorm
import transaction
from zope.component import getUtility

from lp.code.model.branchjob import BranchScanJob
from lp.scripts.helpers import TransactionFreeOperation
from lp.services.config import dbconfig
from lp.services.database.lpstorm import IStore
from lp.services.features import (
    install_feature_controller,
    make_script_feature_controller,
    )
from lp.services.job.model.job import (
    Job,
    UniversalJobSource,
    )
from lp.services.job.runner import (
    BaseJobRunner,
    celery_enabled,
    )
from lp.services import scripts


class CeleryRunJob(RunJob):
    """The Celery Task that runs a job."""

    job_source = UniversalJobSource

    def getJobRunner(self):
        """Return a BaseJobRunner, to support customization."""
        return BaseJobRunner()

    def run(self, job_id, dbuser):
        """Run the specified job.

        :param job_id: The job to run, as expected by UniversalJobSource.
            (Job.id, module_name, class_name)
        :param dbuser: The database user to run under.  This should match the
            dbuser specified by the job's config.
        """
        task_init(dbuser)
        super(CeleryRunJob, self).run(job_id)


class CeleryRunJobIgnoreResult(CeleryRunJob):

    ignore_result = True


def find_missing_ready(job_source):
    """Find ready jobs that are not queued."""
    from lp.services.job.celeryjob import CeleryRunJob
    from lazr.jobrunner.celerytask import list_queued
    queued_job_ids = set(task[1][0][0] for task in list_queued(
        CeleryRunJob.app, [job_source.task_queue]))
    return [job for job in job_source.iterReady() if job.job_id not in
            queued_job_ids]


@task
def run_missing_ready(_no_init=False):
    """Task to run any jobs that are ready but not scheduled.

    Currently supports only BranchScanJob.
    :param _no_init: For tests.  If True, do not perform the initialization.
    """
    if not _no_init:
        task_init('run_missing_ready')
    with TransactionFreeOperation():
        count = 0
        for job in find_missing_ready(BranchScanJob):
            if not celery_enabled(job.__class__.__name__):
                continue
            job.celeryCommitHook(True)
            count += 1
        info('Scheduled %d missing jobs.', count)
        transaction.commit()


needs_zcml = True


def ensure_zcml():
    """Ensure the zcml has been executed for the current process."""
    global needs_zcml
    if not needs_zcml:
        return
    transaction.abort()
    scripts.execute_zcml_for_scripts(use_web_security=False)
    needs_zcml = False


def task_init(dbuser):
    """Prepare to run a task.

    :param dbuser: The database user to use for running the task.
    """
    ensure_zcml()
    transaction.abort()
    store = IStore(Job)
    getUtility(IZStorm).remove(store)
    store.close()
    dbconfig.override(dbuser=dbuser, isolation_level='read_committed')
    install_feature_controller(make_script_feature_controller('celery'))
