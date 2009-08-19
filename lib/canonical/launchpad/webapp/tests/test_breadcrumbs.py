# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests import BaseBreadcrumbTestCase
from lp.testing import login


class TestExtraVHostBreadcrumbsOnHierarchyView(BaseBreadcrumbTestCase):
    """How our breadcrumbs behave when using a vhost other than the main one?

    When we go to bugs.lp.net/ubuntu, we only traversed the Ubuntu distro, so
    that's what we'd have a breadcrumb for, but we also want to generate a
    breadcrumb for bugs on Ubuntu, given that we're on the bugs vhost.

    The behaviour is similar to other vhosts; read on for more.
    """

    def setUp(self):
        super(TestExtraVHostBreadcrumbsOnHierarchyView, self).setUp()
        login('test@canonical.com')
        self.product = self.factory.makeProduct(name='crumb-tester')
        self.product_url = canonical_url(self.product)
        self.product_bugs_url = canonical_url(self.product, rootsite='bugs')
        product_bug = self.factory.makeBug(product=self.product)
        self.product_bugtask = product_bug.default_bugtask
        self.product_bugtask_url = canonical_url(self.product_bugtask)
        self.source_package = self.factory.makeSourcePackage()
        self.package_bugtask = self.factory.makeBugTask(
            target=self.source_package)
        self.package_bugtask_url = canonical_url(self.package_bugtask)

    def test_root_on_mainsite(self):
        urls = self._getBreadcrumbsURLs('http://launchpad.dev/', [self.root])
        self.assertEquals(urls, [])

    def test_product_on_mainsite(self):
        urls = self._getBreadcrumbsURLs(
            self.product_url, [self.root, self.product])
        self.assertEquals(urls, [self.product_url])

    def test_root_on_vhost(self):
        urls = self._getBreadcrumbsURLs(
            'http://bugs.launchpad.dev/', [self.root])
        self.assertEquals(urls, [])

    def test_product_on_vhost(self):
        urls = self._getBreadcrumbsURLs(
            self.product_bugs_url, [self.root, self.product])
        self.assertEquals(urls, [self.product_url, self.product_bugs_url])

    def test_product_bugtask(self):
        urls = self._getBreadcrumbsURLs(
            self.product_bugtask_url,
            [self.root, self.product, self.product_bugtask])
        self.assertEquals(
            urls, [self.product_url, self.product_bugs_url,
                   self.product_bugtask_url])

    def test_package_bugtask(self):
        target = self.package_bugtask.target
        distro_url = canonical_url(target.distribution)
        distroseries_url = canonical_url(target.distroseries)
        package_url = canonical_url(target)
        package_bugs_url = canonical_url(target, rootsite='bugs')
        urls = self._getBreadcrumbsURLs(
            self.package_bugtask_url,
            [self.root, target.distribution, target.distroseries, target,
             self.package_bugtask])
        self.assertEquals(
            urls,
            [distro_url, distroseries_url, package_url, package_bugs_url,
             self.package_bugtask_url])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
