# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the modified branches script."""

__metaclass__ = type

from datetime import datetime
import os
import unittest

import pytz

from canonical.codehosting.scripts.modifiedbranches import (
    ModifiedBranchesScript)
from canonical.codehosting.vfs import branch_id_to_path
from canonical.config import config
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.testing import TestCase, TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.branch import BranchType


class TestModifiedBranchesLocations(TestCaseWithFactory):
    """Test the ModifiedBranchesScript.branch_locations method."""

    layer = DatabaseFunctionalLayer

    def assertHostedLocation(self, branch, location):
        """Assert that the location is the hosted location for the branch."""
        path = branch_id_to_path(branch.id)
        self.assertEqual(
            os.path.join(config.codehosting.hosted_branches_root, path),
            location)

    def assertMirroredLocation(self, branch, location):
        """Assert that the location is the mirror location for the branch."""
        path = branch_id_to_path(branch.id)
        self.assertEqual(
            os.path.join(config.codehosting.mirrored_branches_root, path),
            location)

    def test_hosted_branch(self):
        # A hosted branch prints both the hosted and mirrored locations.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        script = ModifiedBranchesScript('modified-branches', test_args=[])
        [mirrored, hosted] = script.branch_locations(branch)
        self.assertHostedLocation(branch, hosted)
        self.assertMirroredLocation(branch, mirrored)

    def test_mirrored_branch(self):
        # A mirrored branch prints only the mirrored location.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.MIRRORED)
        script = ModifiedBranchesScript('modified-branches', test_args=[])
        [mirrored] = script.branch_locations(branch)
        self.assertMirroredLocation(branch, mirrored)

    def test_imported_branch(self):
        # A mirrored branch prints only the mirrored location.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.IMPORTED)
        script = ModifiedBranchesScript('modified-branches', test_args=[])
        [mirrored] = script.branch_locations(branch)
        self.assertMirroredLocation(branch, mirrored)


class TestModifiedBranchesLastModifiedEpoch(TestCase):
    """Test the calculation of the last modifed date."""

    def test_no_args(self):
        # The script needs one of --since or --last-hours to be specified.
        script = ModifiedBranchesScript(
            'modified-branches', test_args=[])
        self.assertRaises(
            LaunchpadScriptFailure,
            script.get_last_modified_epoch)

    def test_both_args(self):
        # We don't like it if both --since and --last-hours are specified.
        script = ModifiedBranchesScript(
            'modified-branches',
            test_args=['--since=2009-03-02', '--last-hours=12'])
        self.assertRaises(
            LaunchpadScriptFailure,
            script.get_last_modified_epoch)

    def test_modified_since(self):
        # The --since parameter is parsed into a datetime using the fairly
        # standard YYYY-MM-DD format.
        script = ModifiedBranchesScript(
            'modified-branches', test_args=['--since=2009-03-02'])
        self.assertEqual(
            datetime(2009, 3, 2, tzinfo=pytz.UTC),
            script.get_last_modified_epoch())

    def test_modified_since_bad_format(self):
        # Passing in a bad format string for the --since parameter errors.
        script = ModifiedBranchesScript(
            'modified-branches', test_args=['--since=2009-03'])
        self.assertRaises(
            LaunchpadScriptFailure,
            script.get_last_modified_epoch)

    def test_modified_last_hours(self):
        # If last_hours is specified, that number of hours is removed from the
        # current timestamp to work out the selection epoch.
        script = ModifiedBranchesScript(
            'modified-branches', test_args=['--last-hours=12'])
        # Override the script's now_timestamp to have a definitive test.
        # 3pm on the first of January.
        script.now_timestamp = datetime(2009, 1, 1, 15, tzinfo=pytz.UTC)
        # The last modified should be 3am on the same day.
        self.assertEqual(
            datetime(2009, 1, 1, 3, tzinfo=pytz.UTC),
            script.get_last_modified_epoch())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

