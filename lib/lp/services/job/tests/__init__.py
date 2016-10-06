# Copyright 2012-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'block_on_job',
    'celery_worker',
    'monitor_celery',
    'pop_remote_notifications',
    ]


from contextlib import contextmanager
import subprocess

from testtools.content import text_content

from lp.services.job.runner import BaseRunnableJob
from lp.testing.fixture import CaptureOops


@contextmanager
def celery_worker(queue, cwd=None):
    """Return a ContextManager for a "celery worker" instance.

    The "celery worker" instance will be configured to use the
    currently-configured BROKER_URL, and able to run CeleryRunJob tasks.
    """
    from lp.services.job.celeryjob import CeleryRunJob
    # convert config params to a URL, so they can be passed as --broker.
    with CeleryRunJob.app.broker_connection() as connection:
        broker_uri = connection.as_uri(include_password=True)
    cmd_args = (
        'worker',
        '--config', 'lp.services.job.celeryconfig',
        '--broker', broker_uri,
        '--concurrency', '1',
        '--loglevel', 'INFO',
        '--queues', queue,
        '--include', 'lp.services.job.tests.celery_helpers',
    )
    # Mostly duplicated from lazr.jobrunner.tests.test_celerytask.running,
    # but we throw away stdout.
    with open('/dev/null', 'w') as devnull:
        proc = subprocess.Popen(
            ('bin/celery',) + cmd_args, stdout=devnull,
            stderr=subprocess.PIPE, cwd=cwd)
        try:
            yield proc
        finally:
            proc.terminate()
            proc.wait()


@contextmanager
def monitor_celery():
    """Context manager that provides a list of Celery responses."""
    responses = []
    old_responses = BaseRunnableJob.celery_responses
    BaseRunnableJob.celery_responses = responses
    try:
        yield responses
    finally:
        BaseRunnableJob.celery_responses = old_responses


@contextmanager
def block_on_job(test_case=None):
    with CaptureOops() as capture:
        with monitor_celery() as responses:
            yield
        if len(responses) == 0:
            raise Exception('No Job was requested to run via Celery.')
        try:
            responses[-1].wait(30)
        finally:
            if test_case is not None and responses[-1].traceback is not None:
                test_case.addDetail(
                    'Worker traceback', text_content(responses[-1].traceback))
        if test_case is not None:
            capture.sync()
            for oops in capture.oopses:
                test_case.addDetail(
                    'oops', text_content(str(oops)))


def drain_celery_queues():
    from lazr.jobrunner.celerytask import drain_queues
    from lp.services.job.celeryjob import CeleryRunJob
    drain_queues(CeleryRunJob.app, CeleryRunJob.app.conf.CELERY_QUEUES.keys())


def pop_remote_notifications():
    """Pop the notifications from a celery worker."""
    from lp.services.job.tests.celery_helpers import pop_notifications
    return pop_notifications.delay().get(30)
