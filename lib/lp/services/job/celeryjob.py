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
import transaction

from lp.code.model.branchjob import BranchScanJob

from lp.services.features import (
    install_feature_controller,
    make_script_feature_controller,
    )
from lp.services.job.model.job import UniversalJobSource
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
    if not _no_init:
        task_init()
    count = 0
    for job in find_missing_ready(BranchScanJob):
        if not celery_enabled(job.__class__.__name__):
            continue
        job.celeryCommitHook(True)
        count += 1
    info('Scheduled %d missing jobs.', count)
    return


needs_zcml = True


def ensure_zcml():
    global needs_zcml
    if not needs_zcml:
        return
    transaction.abort()
    scripts.execute_zcml_for_scripts(use_web_security=False)
    needs_zcml = False

def task_init():
    ensure_zcml()
    install_feature_controller(make_script_feature_controller('celery'))
