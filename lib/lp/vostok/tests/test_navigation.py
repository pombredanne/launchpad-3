# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for vostok's root navigation."""

__metaclass__ = type

from zope.component import getMultiAdapter
from zope.publisher.interfaces.browser import IBrowserPublisher

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory
from lp.vostok.publisher import VostokRootNavigation, VostokRoot


class TestRootNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    @property
    def _navigation(self):
        return getMultiAdapter(
            (VostokRoot(), LaunchpadTestRequest()), IBrowserPublisher,
            name='')

    def test_use_VostokRootNavigation(self):
        self.assertIsInstance(self._navigation, VostokRootNavigation)

    def test_traverse_to_distributions(self):
        distro = self.factory.makeDistribution()
        traversed = self._navigation.traverse(distro.name)
        self.assertEqual(distro, traversed)

    def test_traverse_to_distribution_aliases(self):
        # When we traverse to a distribution using one of its aliases, we're
        # redirected to the distribution's page.
        distro = self.factory.makeDistribution(aliases=['f00'])
        redirection_view = self._navigation.traverse('f00')
        self.assertEqual(canonical_url(distro), redirection_view.target)

    def test_can_not_traverse_to_projects(self):
        path = self.factory.makeProject().name
        self.assertRaises(NotFoundError, self._navigation.traverse, path)
