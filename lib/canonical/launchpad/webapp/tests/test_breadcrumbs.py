# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getMultiAdapter

from canonical.lazr.testing.menus import make_fake_request
from canonical.launchpad.webapp.publisher import canonical_url, RootObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import login, TestCaseWithFactory


class TestExtraVHostBreadcrumbsOnHierarchyView(TestCaseWithFactory):
    """How our breadcrumbs behave when using a vhost other the main one?

    When we go to bugs.lp.net/ubuntu, we only traversed the Ubuntu distro, so
    that's what we'd have a breadcrumb for, but we also want to generate a
    breadcrumb for bugs on Ubuntu, given that we're on the bugs vhost.

    The behaviour is similar to other vhosts; read on for more.
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('test@canonical.com')
        self.product = self.factory.makeProduct(name='crumb-tester')
        self.product_bug = self.factory.makeBug(product=self.product)
        self.product_bug_url = canonical_url(self.product_bug)
        self.source_package = self.factory.makeSourcePackage()
        self.package_bug = self.factory.makeBugTask(
            target=self.source_package)
        self.package_bug_url = canonical_url(self.package_bug)

    def _getBreadcrumbsURLs(self, url, traversed_objects):
        request = make_fake_request(url, traversed_objects)
        hierarchy = getMultiAdapter(
            (RootObject(), request), name='+hierarchy')
        return [crumb.url for crumb in hierarchy.items()]

    def test_root_on_mainsite(self):
        urls = self._getBreadcrumbsURLs('http://launchpad.dev/', [self.root])
        self.assertEquals(urls, [])

    def test_product_on_mainsite(self):
        urls = self._getBreadcrumbsURLs(
            'http://launchpad.dev/%s' % self.product.name,
            [self.root, self.product])
        self.assertEquals(urls, ['http://launchpad.dev/crumb-tester'])

    def test_root_on_vhost(self):
        urls = self._getBreadcrumbsURLs(
            'http://bugs.launchpad.dev/', [self.root])
        self.assertEquals(urls, [])

    def test_product_on_vhost(self):
        urls = self._getBreadcrumbsURLs(
            'http://bugs.launchpad.dev/%s' % self.product.name,
            [self.root, self.product])
        self.assertEquals(
            urls, ['http://launchpad.dev/crumb-tester',
                   'http://bugs.launchpad.dev/crumb-tester'])

    def test_product_bug(self):
        urls = self._getBreadcrumbsURLs(
            self.product_bug_url, [self.root, self.product, self.product_bug])
        self.assertEquals(
            urls, ['http://launchpad.dev/crumb-tester',
                   'http://bugs.launchpad.dev/crumb-tester'])

    def test_package_bug(self):
        target = self.package_bug.target
        distro_url = canonical_url(target.distribution)
        distroseries_url = canonical_url(target.distroseries)
        package_url = canonical_url(target)
        package_bugs_url = canonical_url(target, rootsite='bugs')
        urls = self._getBreadcrumbsURLs(
            self.package_bug_url,
            [self.root, target.distribution, target.distroseries, target,
             self.package_bug])
        self.assertEquals(
            urls,
            [distro_url, distroseries_url, package_url, package_bugs_url])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
