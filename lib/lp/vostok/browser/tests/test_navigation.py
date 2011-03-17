# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Vostok's navigation classes."""

__metaclass__ = type

from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import (
    canonical_url,
    urlparse,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.testing.publication import test_traverse


class TestRootNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_traverse_to_distributions(self):
        # We can traverse to a distribution by name from the vostok
        # root.
        distro = self.factory.makeDistribution()
        obj, view, request = test_traverse('http://vostok.dev/' + distro.name)
        self.assertEqual(distro, obj)

    def test_traverse_to_distribution_aliases(self):
        # When we traverse to a distribution using one of its aliases, we're
        # redirected to the distribution's page on the vostok vhost.
        distro = self.factory.makeDistribution(aliases=['f00'])
        obj, view, request = test_traverse('http://vostok.dev/f00')
        naked_view = removeSecurityProxy(view)
        parse_result = urlparse(naked_view.target)
        self.assertEqual('vostok.dev', parse_result.netloc)
        self.assertEqual('/' + distro.name, parse_result.path)

    def test_can_not_traverse_to_projects(self):
        # We cannot traverse to a project from the vostok root.
        path = self.factory.makeProject().name
        self.assertRaises(
            NotFound, test_traverse, 'http://vostok.dev/' + path)


class TestDistributionNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_traverse_to_source_package(self):
        # We can traverse to a source package by name from a distribution on
        # the vostok vhost.
        source_package = self.factory.makeDistributionSourcePackage()
        obj, view, request = test_traverse(
            canonical_url(source_package, rootsite='vostok'))
        self.assertEqual(source_package, obj)

    def test_traverse_to_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        obj, view, request = test_traverse(
            canonical_url(distroseries, rootsite='vostok'))
        self.assertEqual(distroseries, obj)

    def test_can_not_traverse_to_bug(self):
        bug = self.factory.makeBugTask(target=self.factory.makeDistribution())
        url = canonical_url(bug, rootsite='vostok')
        self.assertRaises(NotFound, test_traverse, url)
