# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for the test helper machinery defined in helpers.py.
"""

__metaclass__ = type


from unittest import TestCase, TestLoader

from canonical.authserver.tests.test_database import XMLRPCTestHelper
from canonical.codehosting.tests.helpers import FakeLaunchpad


class TestFakeLaunchpad(TestCase, XMLRPCTestHelper):
    """Tests for the FakeLaunchpad fake authserver implementation."""

    def test_failing_branch_name(self):
        # When failing_branch_name is set on a FakeLaunchpad instance and
        # createBranch is called with that branch_name, a Fault with the
        # expected code and message is raised.
        authserver = FakeLaunchpad()
        message = "Branch exploding, as requested."
        authserver.failing_branch_name = 'explode!'
        authserver.failing_branch_code = 666
        authserver.failing_branch_string = message
        self.assertRaisesFault(
            666, message,
            authserver.createBranch,
            1, 'testuser', 'thunderbird', 'explode!')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
