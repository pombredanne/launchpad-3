# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Test the script that reclaims the disk space used by deleted branches."""

import unittest
import transaction

from canonical.testing import ZopelessAppServerLayer
from lp.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script


class TestDiffBMPs(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_mpcreationjobs(self):
        """Ensure mpcreationjobs runs and generates diffs."""
        self.useTempBzrHome()
        branch, tree = self.createMirroredBranchAndTree()
        self.assertTrue(tree.branch._transport.has('.'))
        branch.destroySelf()
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/reclaimbranchspace.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Deleted 1 branch.\n', stderr)
        self.assertFalse(tree.branch._transport.has('.'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
