# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test product releases and product release set."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.productrelease import IProductReleaseSet
from lp.testing import TestCaseWithFactory


class ProductReleaseSetTestcase(TestCaseWithFactory):
    """Tests for ProductReleaseSet."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ProductReleaseSetTestcase, self).setUp()
        self.product_release_set = getUtility(IProductReleaseSet)

    def test_getBySeriesAndVersion_match(self):
        # The release is returned when there is a matching release version.
        milestone = self.factory.makeMilestone(name='0.0.1')
        release = self.factory.makeProductRelease(milestone=milestone)
        found = self.product_release_set.getBySeriesAndVersion(
            milestone.series_target, '0.0.1')
        self.assertEqual(release, found)

    def test_getBySeriesAndVersion_none(self):
        # None is returned when there is no matching release version.
        milestone = self.factory.makeMilestone(name='0.0.1')
        found = self.product_release_set.getBySeriesAndVersion(
            milestone.series_target, '0.0.1')
        self.assertEqual(None, found)

    def test_getBySeriesAndVersion_caches_milestone(self):
        # The release's milestone was cached when the release was retrieved.
        milestone = self.factory.makeMilestone(name='0.0.1')
        self.factory.makeProductRelease(milestone=milestone)
        series = milestone.series_target
        IStore(series).invalidate()
        release = self.product_release_set.getBySeriesAndVersion(
            series, '0.0.1')
        self.assertStatementCount(0, getattr, release, 'milestone')
