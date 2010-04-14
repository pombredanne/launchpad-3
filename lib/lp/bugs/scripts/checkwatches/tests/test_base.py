# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `base` module."""

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.adapter import (
    clear_request_started, get_request_statements, set_request_started)
from canonical.testing import LaunchpadZopelessLayer

from lp.testing import TestCaseWithFactory

from ..base import report_oops


class TestWorkingBase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_sql_log_cleared_in_oops_reporting(self):
        # The log of SQL statements is cleared after an OOPS has been
        # reported by report_oops().

        # Enable SQL statment logging.
        set_request_started()
        try:
            self.factory.makeBug()
            self.assertTrue(
                len(get_request_statements()) > 0,
                "We need at least one statement in the SQL log.")
            report_oops()
            self.assertTrue(
                len(get_request_statements()) == 0,
                "SQL statement log not cleared by report_oops().")
        finally:
            # Stop SQL statement logging.
            clear_request_started()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
