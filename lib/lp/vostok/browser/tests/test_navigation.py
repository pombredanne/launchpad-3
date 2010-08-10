# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Vostok's navigation classes."""

__metaclass__ = type

from zope.publisher.interfaces import NotFound

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory
from lp.testing.publication import test_traverse


# XXX: Should move the contents of lp/vostok/tests/test_navigation.py in here
# before merging.  Haven't done that yet because that file is not in trunk
# yet.
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
