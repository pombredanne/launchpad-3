# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from storm.zope.interfaces import IResultSet
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
