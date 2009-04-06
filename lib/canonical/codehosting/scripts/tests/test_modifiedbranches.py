# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the modified branches script.."""

__metaclass__ = type

from datetime import datetime
import unittest

from canonical.codehosting.scripts.modifiedbranches import (
    ModifiedBranchesScript)
from canonical.launchpad.scripts.base import LaunchpadScriptFailure
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.layers import DatabaseFunctionalLayer


class TestModifiedBranches(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_no_args(self):
        # The script needs one of --since or --last-hours to be specified.
        script = ModifiedBranchesScript(
            'modified-branches', test_args=[])
        self.assertRaises(
            LaunchpadScriptFailure,
            script.parse_last_modified)

    def test_both_args(self):
        # We don't like it if both --since and --last-hours are specified.
        script = ModifiedBranchesScript(
            'modified-branches',
            test_args=['--since=2009-03-02', '--last-hours=12'])
        self.assertRaises(
            LaunchpadScriptFailure,
            script.parse_last_modified)

    def test_modified_since(self):
        # The --since parameter is parsed into a datetime using the fairly
        # standard YYYY-MM-DD format.
        script = ModifiedBranchesScript(
            'modified-branches', test_args=['--since=2009-03-02'])
        self.assertEqual(datetime(2009, 3, 2), script.parse_last_modified())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

