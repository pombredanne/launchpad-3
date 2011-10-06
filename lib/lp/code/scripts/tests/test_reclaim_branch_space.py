# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the script that reclaims the disk space used by deleted branches."""

import datetime
import os
import shutil

import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.testing.layers import ZopelessAppServerLayer
from lp.code.model.branchjob import (
    BranchJob,
    BranchJobType,
    )
from lp.testing import TestCaseWithFactory


class TestReclaimBranchSpaceScript(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_reclaimbranchspace_script(self):
        # When the reclaimbranchspace script is run, it removes from the file
        # system any branches that were deleted from the database more than a
        # week ago.
        db_branch = self.factory.makeAnyBranch()
        mirrored_path = self.getBranchPath(
            db_branch, config.codehosting.mirrored_branches_root)
        if os.path.exists(mirrored_path):
            shutil.rmtree(mirrored_path)
        os.makedirs(mirrored_path)
        db_branch.destroySelf()
        transaction.commit()
        # The first run doesn't remove anything yet.
        retcode, stdout, stderr = run_script(
            'cronscripts/reclaimbranchspace.py', [])
        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    Creating lockfile: /var/lock/launchpad-reclaimbranchspace.lock\n'
            'INFO    Reclaimed space for 0 branches.\n', stderr)
        self.assertEqual(0, retcode)
        self.assertTrue(
            os.path.exists(mirrored_path))
        # Now pretend that the branch was deleted 8 days ago.
        store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)
        reclaim_job = store.find(
            BranchJob,
            BranchJob.job_type == BranchJobType.RECLAIM_BRANCH_SPACE).one()
        reclaim_job.job.scheduled_start -= datetime.timedelta(days=8)
        transaction.commit()
        # The script will now remove the branch from disk.
        retcode, stdout, stderr = run_script(
            'cronscripts/reclaimbranchspace.py', [])
        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    Creating lockfile: /var/lock/launchpad-reclaimbranchspace.lock\n'
            'INFO    Running ReclaimBranchSpaceJob (ID %d) in status Waiting\n'
            'INFO    Reclaimed space for 1 branches.\n' % reclaim_job.job.id,
            stderr)
        self.assertEqual(0, retcode)
        self.assertFalse(
            os.path.exists(mirrored_path))


    def test_reclaimbranchspace_script_logs_oops(self):
        # If the job fails, an oops is logged.
        db_branch = self.factory.makeAnyBranch()
        mirrored_path = self.getBranchPath(
            db_branch, config.codehosting.mirrored_branches_root)
        if os.path.exists(mirrored_path):
            shutil.rmtree(mirrored_path)
        os.makedirs(mirrored_path)
        self.addCleanup(lambda: shutil.rmtree(mirrored_path))
        os.chmod(mirrored_path, 0)
        self.addCleanup(lambda: os.chmod(mirrored_path, 0777))
        db_branch.destroySelf()
        # Now pretend that the branch was deleted 8 days ago.
        store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)
        reclaim_job = store.find(
            BranchJob,
            BranchJob.job_type == BranchJobType.RECLAIM_BRANCH_SPACE).one()
        reclaim_job.job.scheduled_start -= datetime.timedelta(days=8)
        transaction.commit()
        # The script will now remove the branch from disk.
        retcode, stdout, stderr = run_script(
            'cronscripts/reclaimbranchspace.py', [])
        self.assertIn('INFO    Creating lockfile: ', stderr)
        self.assertIn('INFO    Job resulted in OOPS:', stderr)
        self.assertIn('INFO    Reclaimed space for 0 branches.\n', stderr)
