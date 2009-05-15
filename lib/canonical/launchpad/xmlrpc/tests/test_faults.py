# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for `canonical.launchpad.xmlrpc.faults`."""

__metaclass__ = type

import unittest

from lp.testing import TestCase
from canonical.launchpad.xmlrpc import faults


class TestFaultOne(faults.LaunchpadFault):
    """An arbitrary subclass of `LaunchpadFault`.

    This class and `TestFaultTwo` are a pair of distinct `LaunchpadFault`
    subclasses to use in tests.
    """

    error_code = 1001
    msg_template = "Fault one."


class TestFaultTwo(faults.LaunchpadFault):
    """Another arbitrary subclass of `LaunchpadFault`.

    This class and `TestFaultOne` are a pair of distinct `LaunchpadFault`
    subclasses to use in tests.
    """

    error_code = 1002
    msg_template = "Fault two."


class TestTrapFault(TestCase):
    """Tests for `check_fault`."""

    def test_wrong_fault(self):
        # check_fault returns False if the passed fault does not have the code
        # of one of the passed classes.
        self.assertFalse(
            faults.check_fault(TestFaultOne(), TestFaultTwo))

    def test_no_fault_classes(self):
        # check_fault returns False if there are no passed classes.
        self.assertFalse(
            faults.check_fault(TestFaultOne()))

    def test_matches(self):
        # check_fault returns True if the passed fault has the code of the
        # passed class.
        self.assertTrue(
            faults.check_fault(TestFaultOne(), TestFaultOne))

    def test_matches_one_of_set(self):
        # check_fault returns True if the passed fault has the code of one of
        # the passed classes.
        self.assertTrue(faults.check_fault(
            TestFaultOne(), TestFaultOne, TestFaultTwo))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

