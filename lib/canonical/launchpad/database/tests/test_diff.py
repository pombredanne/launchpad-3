# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Diff, etc."""

from unittest import TestLoader

from canonical.launchpad.database.diff import *
from canonical.launchpad.testing import TestCaseWithFactory

__metaclass__ = type


class TestDiff(TestCaseWithFactory):

    def from_revision_ids(self):
        d = Diff.from_revision_ids()


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
