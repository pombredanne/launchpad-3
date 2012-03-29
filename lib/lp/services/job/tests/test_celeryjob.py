# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


import transaction

from lp.code.model.branchjob import BranchScanJob
from lp.services.job.tests import celeryd
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessAppServerLayer


class TestCelery(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_run_scan_job(self):
        """Running a job via Celery succeeds and emits expected output."""
        # Delay importing anything that uses Celery until RabbitMQLayer is
        # running, so that config.rabbitmq.host is defined when
        # lp.services.job.celeryconfig is loaded.
        from celery.exceptions import TimeoutError
        with celeryd() as proc:
            self.useBzrBranches()
            db_branch, bzr_tree = self.create_branch_and_tree()
            bzr_tree.commit(
                'First commit', rev_id='rev1', committer='me@example.org')
            job = BranchScanJob.create(db_branch)
            transaction.commit()
            try:
                job.runViaCelery().wait(30)
            except TimeoutError:
                pass
        self.assertIn(
            'Updating branch scanner status: 1 revs', proc.stderr.read())
        self.assertEqual(db_branch.revision_count, 1)
