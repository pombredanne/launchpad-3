# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = ['celeryd']


from contextlib import contextmanager
from time import sleep


@contextmanager
def celeryd(queue):
    """Return a ContextManager for a celeryd instance.

    The celeryd instance will be configured to use the currently-configured
    BROKER_URL, and able to run CeleryRunJob tasks.
    """
    from lp.services.job.celeryjob import CeleryRunJob
    from lazr.jobrunner.tests.test_celerytask import running
    cmd_args = (
        '--config', 'lp.services.job.celeryconfig',
        '--broker', CeleryRunJob.app.conf['BROKER_URL'],
        '--concurrency', '1',
        '--loglevel', 'INFO',
        '--queues', queue,
    )
    with running('bin/celeryd', cmd_args) as proc:
        # Wait for celeryd startup to complete.
        sleep(1)
        yield proc
