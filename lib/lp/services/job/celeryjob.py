# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Celery-specific Job code.

Because celery sets up configuration at import time, code that is not designed
to use Celery may break if this is used.
"""

__metaclass__ = type

__all__ = ['CeleryRunJob']

import os

os.environ.setdefault('CELERY_CONFIG_MODULE', 'lp.services.job.celeryconfig')
from celery.task import task
from lazr.jobrunner.celerytask import RunJob

from lp.services.job.model.job import UniversalJobSource
from lp.services.job.runner import BaseJobRunner


class CeleryRunJob(RunJob):
    """The Celery Task that runs a job."""

    job_source = UniversalJobSource

    def getJobRunner(self):
        """Return a BaseJobRunner, to support customization."""
        return BaseJobRunner()


@task
def pop_notifications():
    from lp.testing.mail_helpers import pop_notifications
    return pop_notifications()
