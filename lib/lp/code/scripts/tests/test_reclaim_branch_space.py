# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the script that reclaims the disk space used by deleted branches."""

import datetime
import os
import shutil
import unittest

import transaction

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import ZopelessAppServerLayer

from lp.code.model.branchjob import BranchJob, BranchJobType
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
            'INFO    creating lockfile\n'
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
            'INFO    creating lockfile\n'
            'INFO    Reclaimed space for 1 branches.\n', stderr)
        self.assertEqual(0, retcode)
        self.assertFalse(
            os.path.exists(mirrored_path))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
