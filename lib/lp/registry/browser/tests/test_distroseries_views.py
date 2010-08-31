# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from storm.zope.interfaces import IResultSet
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing import LaunchpadZopelessLayer
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
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


class DistroSeriesLocalPackageDiffsTestCase(TestCaseWithFactory):
    """Test the distroseries +localpackagediffs view."""

    layer = LaunchpadZopelessLayer

    def makeDerivedSeries(self, derived_name=None, parent_name=None):
        # Helper that creates a derived distro series.
        parent = self.factory.makeDistroSeries(name=parent_name)
        derived_series = self.factory.makeDistroSeries(
            name=derived_name, parent_series=parent)
        return derived_series

    def test_label(self):
        # The view label includes the names of both series.
        derived_series = self.makeDerivedSeries(
            parent_name='lucid', derived_name='derilucid')

        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        self.assertEqual(
            "Package differences between 'Derilucid' and parent series "
            "'Lucid'",
            view.label)

    def test_ignored_packages_url(self):
        # The ignored_packages_url is provided by the view.
        derived_series = self.makeDerivedSeries('derilucid')

        view = create_initialized_view(
            derived_series, '+localpackagediffs',
            server_url='https://launchpad.dev/ubuntu/derilucid/'
                       '+localpackagediffs')

        self.assertEqual(
            "https://launchpad.dev/ubuntu/derilucid/+localpackagediffs"
            "?include_ignored=1",
            view.ignored_packages_url)

    def test_ignored_packages_count(self):
        # The number of ignored differences is returned.
        derived_series = self.makeDerivedSeries('derilucid')
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.IGNORED)
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.IGNORED_ALWAYS)

        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        self.assertEqual(2, view.ignored_packages_count)

    def test_ignored_packages_doesnt_include_other_types(self):
        # Only diffs of the right type for the current derived series
        # are counted.
        # The following difference won't count as it is a different type
        # of difference (not relevant to this view).
        derived_series = self.makeDerivedSeries('derilucid')
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            difference_type=(
                DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES))
        # The following difference won't count as it is for a different
        # series.
        self.factory.makeDistroSeriesDifference(
            status=DistroSeriesDifferenceStatus.IGNORED)

        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        self.assertEqual(0, view.ignored_packages_count)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
