# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Milestone related test helper."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    logout,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer

from lp.app.errors import NotFoundError
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.milestone import IMilestoneSet
from lp.registry.interfaces.product import IProductSet


class MilestoneTest(unittest.TestCase):
    """Milestone tests."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)

    def tearDown(self):
        logout()

    def testMilestoneSetIterator(self):
        """Test of MilestoneSet.__iter__()."""
        all_milestones_ids = set(
            milestone.id for milestone in getUtility(IMilestoneSet))
        self.assertEqual(all_milestones_ids,
                         set((1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)))

    def testMilestoneSetGet(self):
        """Test of MilestoneSet.get()"""
        milestone_set = getUtility(IMilestoneSet)
        self.assertEqual(milestone_set.get(1).id, 1)
        self.assertRaises(NotFoundError, milestone_set.get, 100000)

    def testMilestoneSetGetByNameAndProduct(self):
        """Test of MilestoneSet.getByNameAndProduct()"""
        firefox = getUtility(IProductSet).getByName('firefox')
        milestone_set = getUtility(IMilestoneSet)
        milestone = milestone_set.getByNameAndProduct('1.0', firefox)
        self.assertEqual(milestone.name, '1.0')
        self.assertEqual(milestone.target, firefox)

        marker = object()
        milestone = milestone_set.getByNameAndProduct(
            'does not exist', firefox, default=marker)
        self.assertEqual(milestone, marker)

    def testMilestoneSetGetByNameAndDistribution(self):
        """Test of MilestoneSet.getByNameAndDistribution()"""
        debian = getUtility(IDistributionSet).getByName('debian')
        milestone_set = getUtility(IMilestoneSet)
        milestone = milestone_set.getByNameAndDistribution('3.1', debian)
        self.assertEqual(milestone.name, '3.1')
        self.assertEqual(milestone.target, debian)

        marker = object()
        milestone = milestone_set.getByNameAndDistribution(
            'does not exist', debian, default=marker)
        self.assertEqual(milestone, marker)

    def testMilestoneSetGetVisibleMilestones(self):
        all_visible_milestones_ids = [
            milestone.id
            for milestone in getUtility(IMilestoneSet).getVisibleMilestones()]
        self.assertEqual(
            all_visible_milestones_ids,
            [1, 2, 3])


def test_suite():
    """Return the test suite for the tests in this module."""
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main()
