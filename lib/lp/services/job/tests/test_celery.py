# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
if os.environ.get('CELERY_CONFIG_MODULE') is not None:
    raise AssertionError('CELERY_CONFIG_MODULE is set.')
os.environ['CELERY_CONFIG_MODULE'] = 'lp.services.job.tests.config1'

from lazr.jobrunner.tests.test_jobrunner import running
import transaction

from lp.code.model.branchjob import BranchScanJob
from lp.services.job.celery import CeleryRunJob
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessAppServerLayer


class TestCelery(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_run_scan_job(self):
        """Running a job via Celery succeeds and emits expected output."""
        cmd_args = ('--config', os.environ['CELERY_CONFIG_MODULE'])
        with running('bin/celeryd', cmd_args) as proc:
            self.useBzrBranches()
            db_branch, bzr_tree = self.create_branch_and_tree()
            bzr_tree.commit('First commit', rev_id='rev1')
            job = BranchScanJob.create(db_branch)
            transaction.commit()
            CeleryRunJob.delay(job.job_id).wait()
        self.assertIn(
            'Updating branch scanner status: 1 revs', proc.stderr.read())
        self.assertEqual(db_branch.revision_count, 1)
