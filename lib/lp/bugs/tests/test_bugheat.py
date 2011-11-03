# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugJobs."""

__metaclass__ = type

import unittest

from zope.interface import implements

from storm.store import Store

from lazr.delegates import delegates

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from lp.testing import TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory


class BugUpdateHeat(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_updateHeat_calls_recalculateBugHeatCache(self):
        # This requires some instrumentation. The updateHeat() method is
        # called by many methods that may be involved in setting up a bug
        # target.
        class TestTarget:
            implements(IDistributionSourcePackage)
            delegates(IDistributionSourcePackage, context='target')

            def __init__(self, target):
                self.target = target
                self.called = False

            def recalculateBugHeatCache(self):
                self.called = True

        distro = self.factory.makeDistribution()
        target = TestTarget(
            self.factory.makeDistributionSourcePackage(
                distribution=distro, with_db=True))
        dsp = self.factory.makeDistributionSourcePackage(distribution=distro)
        bugtask = self.factory.makeBugTask(target=dsp)
        another_task = bugtask.bug.addTask(bugtask.bug.owner, target)
        another_task.bug.updateHeat()
        self.assertTrue(target.called)


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


class DistributionSourcePackageNullBugHeatCacheTest(TestCaseWithFactory):
    """Ensure distro source package cache values start at None."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.target = self.factory.makeDistributionSourcePackage()

    def test_null_max_bug_heat(self):
        self.assertEqual(None, self.target.max_bug_heat)

    def test_null_total_bug_heat(self):
        self.assertEqual(None, self.target.total_bug_heat)

    def test_null_bug_count(self):
        self.assertEqual(None, self.target.bug_count)


class DistributionSourcePackageZeroRecalculateBugHeatCacheTest(
    TestCaseWithFactory):
    """Ensure distro source package cache values become zero properly."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.target = self.factory.makeDistributionSourcePackage()
        self.target.recalculateBugHeatCache()

    def test_zero_max_bug_heat(self):
        self.assertEqual(0, self.target.max_bug_heat)

    def test_zero_total_bug_heat(self):
        self.assertEqual(0, self.target.total_bug_heat)

    def test_zero_bug_count(self):
        self.assertEqual(0, self.target.bug_count)


class DistributionSourcePackageMultipleBugsRecalculateBugHeatCacheTest(
    TestCaseWithFactory):
    """Ensure distro source package cache values are set properly."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.target = self.factory.makeDistributionSourcePackage(with_db=True)
        self.bugtask1 = self.factory.makeBugTask(target=self.target)
        self.bugtask2 = self.factory.makeBugTask(target=self.target)
        self.bugtask3 = self.factory.makeBugTask(target=self.target)
        self.bugtask4 = self.factory.makeBugTask(target=self.target)
        # A closed bug is not include in DSP bug heat calculations.
        self.bugtask3.transitionToStatus(
            BugTaskStatus.FIXRELEASED, self.target.distribution.owner)
        # A duplicate bug is not include in DSP bug heat calculations.
        self.bugtask4.bug.markAsDuplicate(self.bugtask1.bug)
        # Bug heat gets calculated by complicated rules in a db
        # stored procedure. We will override them here to avoid
        # testing inconsitencies if those values are calculated
        # differently in the future.
        # target.recalculateBugHeatCache() should be called
        # automatically by bug.setHeat().
        bug1 = self.bugtask1.bug
        bug2 = self.bugtask2.bug
        bug3 = self.bugtask3.bug
        bug1.setHeat(7)
        bug2.setHeat(19)
        bug3.setHeat(11)
        Store.of(bug1).flush()
        self.max_heat = max(bug1.heat, bug2.heat)
        self.total_heat = sum([bug1.heat, bug2.heat])

    def test_max_bug_heat(self):
        self.assertEqual(self.max_heat, self.target.max_bug_heat)

    def test_total_bug_heat(self):
        self.assertEqual(self.total_heat, self.target.total_bug_heat)
        self.failUnless(
            self.target.total_bug_heat > self.target.max_bug_heat,
            "Total bug heat should be more than the max bug heat, "
            "since we know that multiple bugs have nonzero heat.")

    def test_bug_count(self):
        self.assertEqual(2, self.target.bug_count)


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
