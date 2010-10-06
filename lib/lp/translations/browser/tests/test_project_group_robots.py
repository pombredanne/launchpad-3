# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


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


class TestRobots(TestCaseWithFactory):
    """Test the inclusion of the robots HEAD."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRobots, self).setUp()
        self.projectgroup = self.factory.makeProject()
        self.product = self.factory.makeProduct()
        self.factory.makePOTemplate(
            productseries=self.product.development_focus)
        self.naked_product = removeSecurityProxy(self.product)
        self.naked_product.project = self.projectgroup

    def _get_soup_and_robots(self, usage):
        self.naked_product.translations_usage = usage
        view = create_initialized_view(
            self.projectgroup, '+translations', rootsite='translations')
        soup = BeautifulSoup(view())
        robots = soup.find('meta', attrs={'name': 'robots'})
        return soup, robots

    def _verify_robots_not_blocked(self, usage):
        soup, robots = self._get_soup_and_robots(usage)
        self.assertEqual(1, self.projectgroup.translatables().count())
        self.assertIs(None, robots)

    def _verify_robots_are_blocked(self, usage):
        soup, robots = self._get_soup_and_robots(usage)
        self.assertEqual(0, self.projectgroup.translatables().count())
        self.assertEqual('noindex,nofollow', robots['content'])

    def test_UNKNOWN_blocks_robots(self):
        self._verify_robots_are_blocked(ServiceUsage.UNKNOWN)

    def test_EXTERNAL_blocks_robots(self):
        self._verify_robots_are_blocked(ServiceUsage.EXTERNAL)

    def test_NOT_APPLICABLE_blocks_robots(self):
        self._verify_robots_are_blocked(ServiceUsage.NOT_APPLICABLE)

    def test_LAUNCHPAD_does_not_block_robots(self):
        self._verify_robots_not_blocked(ServiceUsage.LAUNCHPAD)
