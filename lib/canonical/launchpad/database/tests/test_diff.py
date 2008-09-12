# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Diff, etc."""

__metaclass__ = type


from unittest import TestLoader

from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.database.diff import *
from canonical.launchpad.interfaces import IDiff
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.testing import verifyObject


class TestDiff(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IDiff, Diff())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
