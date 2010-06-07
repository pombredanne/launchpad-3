# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugJobs."""

__metaclass__ = type

import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.testing.factory import LaunchpadObjectFactory


class MaxHeatByTargetBase:
    """Base class for testing a bug target's max_bug_heat attribute."""

    layer = LaunchpadZopelessLayer

    factory = LaunchpadObjectFactory()

    # The target to test.
    target = None

    # Does the target have a set method?
    delegates_setter = False

    def test_target_max_bug_heat_default(self):
        self.assertEqual(self.target.max_bug_heat, None)

    def test_set_target_max_bug_heat(self):
        if self.delegates_setter:
            self.assertRaises(
                NotImplementedError, self.target.setMaxBugHeat, 1000)
        else:
            self.target.setMaxBugHeat(1000)
            self.assertEqual(self.target.max_bug_heat, 1000)


class ProjectMaxHeatByTargetTest(MaxHeatByTargetBase, unittest.TestCase):
    """Ensure a project has a max_bug_heat value that can be set."""

    def setUp(self):
        self.target = self.factory.makeProduct()


class DistributionMaxHeatByTargetTest(MaxHeatByTargetBase, unittest.TestCase):
    """Ensure a distribution has a max_bug_heat value that can be set."""

    def setUp(self):
        self.target = self.factory.makeDistribution()


class DistributionSourcePackageMaxHeatByTargetTest(
    MaxHeatByTargetBase, unittest.TestCase):
    """Ensure distro source package has max_bug_heat value that can be set."""

    def setUp(self):
        self.target = self.factory.makeDistributionSourcePackage()


class SourcePackageMaxHeatByTargetTest(
    MaxHeatByTargetBase, unittest.TestCase):
    """Ensure a source package has a max_bug_heat value that can be set."""

    def setUp(self):
        self.target = self.factory.makeSourcePackage()
        self.delegates_setter = True


class ProductSeriesMaxHeatByTargetTest(
    MaxHeatByTargetBase, unittest.TestCase):
    """Ensure a product series has a max_bug_heat value that can be set."""

    def setUp(self):
        self.target = self.factory.makeProductSeries()
        self.delegates_setter = True


class DistroSeriesMaxHeatByTargetTest(
    MaxHeatByTargetBase, unittest.TestCase):
    """Ensure a distro series has a max_bug_heat value that can be set."""

    def setUp(self):
        self.target = self.factory.makeDistroSeries()
        self.delegates_setter = True


class ProjectGroupMaxHeatByTargetTest(
    MaxHeatByTargetBase, unittest.TestCase):
    """Ensure a project group has a max_bug_heat value that can be set."""

    def setUp(self):
        self.target = self.factory.makeProject()

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
