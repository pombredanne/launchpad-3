# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Diff, etc."""

__metaclass__ = type


from unittest import TestLoader

from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.database.diff import *
from canonical.launchpad.testing import TestCaseWithFactory


class TestDiff(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_from_revision_ids(self):
        d = Diff.from_revision_ids()


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
