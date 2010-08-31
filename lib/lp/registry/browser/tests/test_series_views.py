# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from storm.zope.interfaces import IResultSet
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.testing import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestDistroSeriesNeedsPackagesView(TestCaseWithFactory):
    """Test the distroseries +needs-packaging view."""

    layer = LaunchpadZopelessLayer

    def test_cached_unlinked_packages(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        distroseries = self.factory.makeDistroSeries(distribution=ubuntu)
        view = create_initialized_view(distroseries, '+needs-packaging')
        naked_packages = removeSecurityProxy(view.cached_unlinked_packages)
        self.assertTrue(
            IResultSet.providedBy(
                view.cached_unlinked_packages.currentBatch().list),
            '%s should batch IResultSet so that slicing will limit the '
            'query' % view.cached_unlinked_packages.currentBatch().list)


class TestDistroSeriesView(TestCaseWithFactory):
    """Test the distroseries +index view."""

    layer = LaunchpadZopelessLayer

    def test_needs_linking(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        distroseries = self.factory.makeDistroSeries(distribution=ubuntu)
        view = create_initialized_view(distroseries, '+index')
        self.assertEqual(view.needs_linking, None)


class TestMilestoneBatchNavigatorAttribute(TestCaseWithFactory):
    """Test the series.milestone_batch_navigator attribute."""

    layer = LaunchpadZopelessLayer

    def test_distroseries_milestone_batch_navigator(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        distroseries = self.factory.makeDistroSeries(distribution=ubuntu)
        for name in ('a', 'b', 'c', 'd'):
            distroseries.newMilestone(name)
        view = create_initialized_view(distroseries, name='+index')
        self._check_milestone_batch_navigator(view)

    def test_productseries_milestone_batch_navigator(self):
        product = self.factory.makeProduct()
        for name in ('a', 'b', 'c', 'd'):
            product.development_focus.newMilestone(name)
        view = create_initialized_view(
            product.development_focus, name='+index')
        self._check_milestone_batch_navigator(view)

    def _check_milestone_batch_navigator(self, view):
        config.push('default-batch-size', """
        [launchpad]
        default_batch_size: 2
        """)
        self.assert_(
            isinstance(view.milestone_batch_navigator, BatchNavigator),
            'milestone_batch_navigator is not a BatchNavigator object: %r'
            % view.milestone_batch_navigator)
        self.assertEqual(4, view.milestone_batch_navigator.batch.total())
        expected = [
            'd',
            'c',
            ]
        milestone_names = [
            item.name
            for item in view.milestone_batch_navigator.currentBatch()]
        self.assertEqual(expected, milestone_names)
        config.pop('default-batch-size')
