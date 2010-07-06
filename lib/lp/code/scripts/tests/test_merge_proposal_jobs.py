#! /usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the sendbranchmail script"""

import unittest

from canonical.testing import ZopelessAppServerLayer
from lp.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script


class TestMergeProposalJobScript(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_script_runs(self):
        """Ensure merge-proposal-jobs script runs."""
        retcode, stdout, stderr = run_script(
            'cronscripts/merge-proposal-jobs.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    Creating lockfile:'
            ' /var/lock/launchpad-merge-proposal-jobs.lock\n'
            'INFO    Running through Twisted.\n', stderr)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
