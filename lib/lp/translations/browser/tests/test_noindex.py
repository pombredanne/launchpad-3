# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import unittest

from BeautifulSoup import BeautifulSoup

from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.enums import ServiceUsage
from lp.testing import (
    TestCaseWithFactory,
    )
from lp.testing.views import (
    create_initialized_view,
    )


class TestRobotsBase(TestCaseWithFactory):
    """Test the inclusion of the meta "noindex,nofollow" directives.

    setUp must define the naked_translatable attribute.
    """

    layer = DatabaseFunctionalLayer

    def set_usage(self, usage):
        self.naked_translatable.translations_usage = usage

    def get_view(self):
        """Return an initialized view."""
        raise NotImplementedError

    def get_soup_and_robots(self, usage):
        self.set_usage(usage)
        view = self.get_view()
        soup = BeautifulSoup(view())
        robots = soup.find('meta', attrs={'name': 'robots'})
        return soup, robots

    def verify_robots_are_blocked(self, usage):
        soup, robots = self.get_soup_and_robots(usage)
        self.assertEqual('noindex,nofollow', robots['content'])

    def verify_robots_not_blocked(self, usage):
        soup, robots = self.get_soup_and_robots(usage)
        self.assertIs(None, robots)

    def test_UNKNOWN_blocks_robots(self):
        self.verify_robots_are_blocked(ServiceUsage.UNKNOWN)

    def test_EXTERNAL_blocks_robots(self):
        self.verify_robots_are_blocked(ServiceUsage.EXTERNAL)

    def test_NOT_APPLICABLE_blocks_robots(self):
        self.verify_robots_are_blocked(ServiceUsage.NOT_APPLICABLE)

    def test_LAUNCHPAD_does_not_block_robots(self):
        self.verify_robots_not_blocked(ServiceUsage.LAUNCHPAD)


class TestRobotsProjectGroup(TestRobotsBase):
    """Test noindex,nofollow for project groups."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRobotsProjectGroup, self).setUp()
        self.projectgroup = self.factory.makeProject()
        self.product = self.factory.makeProduct()
        self.factory.makePOTemplate(
            productseries=self.product.development_focus)
        self.naked_translatable = removeSecurityProxy(self.product)
        self.naked_translatable.project = self.projectgroup

    def get_view(self):
        return create_initialized_view(
            self.projectgroup, '+translations', rootsite='translations')

    def test_has_translatables_true(self):
        self.set_usage(ServiceUsage.LAUNCHPAD)
        view = self.get_view()
        self.assertTrue(view.has_translatables)

    def test_has_translatables_false(self):
        self.set_usage(ServiceUsage.UNKNOWN)
        view = self.get_view()
        self.assertFalse(view.has_translatables)

from lp.registry.interfaces.distribution import IDistributionSet
from zope.component import getUtility

class TestRobotsDistroSeries(TestRobotsBase):
    """Test noindex,nofollow for distro series."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRobotsDistroSeries, self).setUp()
        #self.distro = self.factory.makeDistribution(name="whobuntu")
        self.distro = getUtility(IDistributionSet).getByName('ubuntu')
        self.distroseries = self.factory.makeDistroSeries(
            name="zephyr", distribution=self.distro)
        new_sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makePOTemplate(
            distroseries=self.distroseries,
            sourcepackagename=new_sourcepackagename)
        self.naked_translatable = removeSecurityProxy(self.distro)

    def get_view(self):
        return create_initialized_view(
            self.distroseries, '+translations', rootsite='translations')

    def test_LAUNCHPAD_does_not_block_robots(self):
        self.verify_robots_not_blocked(ServiceUsage.LAUNCHPAD)


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    # Add the tests that should run, excluding TestRobotsBase.
    suite.addTest(loader.loadTestsFromTestCase(TestRobotsProjectGroup))
    suite.addTest(loader.loadTestsFromTestCase(TestRobotsDistroSeries))
    return suite
