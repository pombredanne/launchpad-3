# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


from contextlib import contextmanager
import os

import transaction

from lp.code.model.branchjob import BranchScanJob
from lp.services.job.runner import BaseRunnableJob
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessAppServerLayer


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


class TestCelery(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_run_scan_job(self):
        """Running a job via Celery succeeds and emits expected output."""
        # Delay importing anything that uses Celery until RabbitMQLayer is
        # running, so that config.rabbitmq.host is defined when
        # lp.services.job.celeryconfig is loaded.
        from lp.services.job.celeryjob import CeleryRunJob
        from celery.exceptions import TimeoutError
        from lazr.jobrunner.tests.test_celerytask import running
        cmd_args = ('--config', 'lp.services.job.tests.celeryconfig')
        env = dict(os.environ)
        env['BROKER_URL'] = CeleryRunJob.app.conf['BROKER_URL']
        with running('bin/celeryd', cmd_args, env=env) as proc:
            self.useBzrBranches()
            db_branch, bzr_tree = self.create_branch_and_tree()
            bzr_tree.commit(
                'First commit', rev_id='rev1', committer='me@example.org')
            job = BranchScanJob.create(db_branch)
            transaction.commit()
            try:
                CeleryRunJob.delay(job.job_id).wait(30)
            except TimeoutError:
                pass
        self.assertIn(
            'Updating branch scanner status: 1 revs', proc.stderr.read())
        self.assertEqual(db_branch.revision_count, 1)
