# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the script that reclaims the disk space used by deleted branches."""

import os
import unittest

import transaction

from canonical.config import config
from canonical.launchpad.scripts.tests import run_script
from canonical.testing import ZopelessAppServerLayer
from lp.testing import TestCaseWithFactory


class TestReclaimBranchSpaceScript(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_reclaimbranchspace_script(self):
        # When the reclaimbranchspace script is run, it removes from the file
        # system any branches that have been deleted from the database.
        db_branch = self.factory.makeAnyBranch()
        mirrored_path = self.getBranchPath(
            db_branch, config.codehosting.mirrored_branches_root)
        os.makedirs(mirrored_path)
        db_branch.destroySelf()
        transaction.commit()
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
