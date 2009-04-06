# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the modified branches script."""

__metaclass__ = type

from datetime import datetime
import unittest

import pytz

from canonical.codehosting.scripts.modifiedbranches import (
    ModifiedBranchesScript)
from canonical.launchpad.scripts.base import LaunchpadScriptFailure
from canonical.launchpad.testing import TestCase
from canonical.testing.layers import DatabaseFunctionalLayer


class TestModifiedBranchesDateParsing(TestCase):
    """Test the calculation of the last modifed date."""

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
        self.assertEqual(
            datetime(2009, 3, 2, tzinfo=pytz.UTC),
            script.parse_last_modified())

    def test_modified_since_bad_format(self):
        # Passing in a bad format string for the --since parameter errors.
        script = ModifiedBranchesScript(
            'modified-branches', test_args=['--since=2009-03'])
        self.assertRaises(
            LaunchpadScriptFailure,
            script.parse_last_modified)

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
            script.parse_last_modified())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

