# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.i18nmessageid import Message
from zope.interface import implements

from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from lp.app.browser.launchpad import Hierarchy
from lp.testing import (
    login,
    TestCase,
    )
from lp.testing.breadcrumbs import BaseBreadcrumbTestCase


class Cookbook:
    implements(ICanonicalUrlData)
    rootsite = None


class TestBreadcrumb(TestCase):

    def test_rootsite_defaults_to_mainsite(self):
        # When a class' ICanonicalUrlData doesn't define a rootsite, our
        # Breadcrumb adapter will use 'mainsite' as the rootsite.
        cookbook = Cookbook()
        self.assertIs(cookbook.rootsite, None)
        self.assertEquals(Breadcrumb(cookbook).rootsite, 'mainsite')

    def test_urldata_rootsite_is_honored(self):
        # When a class' ICanonicalUrlData defines a rootsite, our Breadcrumb
        # adapter will use it.
        cookbook = Cookbook()
        cookbook.rootsite = 'cooking'
        self.assertEquals(Breadcrumb(cookbook).rootsite, 'cooking')


class TestExtraBreadcrumbForLeafPageOnHierarchyView(BaseBreadcrumbTestCase):
    """When the current page is not the object's default one (+index), we add
    an extra breadcrumb for it.
    """

    def setUp(self):
        super(TestExtraBreadcrumbForLeafPageOnHierarchyView, self).setUp()
        login('test@canonical.com')
        self.product = self.factory.makeProduct(name='crumb-tester')
        self.product_url = canonical_url(self.product)

    def test_default_page(self):
        self.assertBreadcrumbUrls([self.product_url], self.product)

    def test_non_default_page(self):
        crumbs = self.getBreadcrumbsForObject(self.product, '+download')
        downloads_url = "%s/+download" % self.product_url
        self.assertEquals(
            [self.product_url, downloads_url],
            [crumb.url for crumb in crumbs])
        self.assertEquals(
            '%s project files' % self.product.displayname,
            crumbs[-1].text)

    def test_zope_i18n_Messages_are_interpolated(self):
        # Views can use zope.i18nmessageid.Message as their title when they
        # want to i18n it, but when that's the case we need to
        # translate/interpolate the string.
        class TestView:
            """A test view that uses a Message as its page_title."""
            page_title = Message(
                '${name} test', mapping={'name': 'breadcrumb'})
            __name__ = 'test-page'
        test_view = TestView()
        request = LaunchpadTestRequest()
        request.traversed_objects = [self.product, test_view]
        hierarchy_view = Hierarchy(self.product, request)
        breadcrumb = hierarchy_view.makeBreadcrumbForRequestedPage()
        self.assertEquals(breadcrumb.text, 'breadcrumb test')


class TestExtraFacetBreadcrumbsOnHierarchyView(BaseBreadcrumbTestCase):
    """How our breadcrumbs behave when using a facet other than the main one?

    When we go to lp.net/ubuntu/+bugs, we only traversed the Ubuntu distro, so
    that's what we'd have a breadcrumb for, but we also want to generate a
    breadcrumb for bugs on Ubuntu, given that we're in the bugs facet.
    """

    def setUp(self):
        super(TestExtraFacetBreadcrumbsOnHierarchyView, self).setUp()
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
        crumbs = self.getBreadcrumbsForUrl('http://launchpad.dev/')
        self.assertEquals(crumbs, [])

    def test_product_on_mainsite(self):
        self.assertBreadcrumbUrls([self.product_url], self.product)

    def test_root_on_vhost(self):
        crumbs = self.getBreadcrumbsForUrl('http://bugs.launchpad.dev/')
        self.assertEquals(crumbs, [])

    def test_product_on_vhost(self):
        self.assertBreadcrumbUrls(
            [self.product_url, self.product_bugs_url],
            self.product, rootsite='bugs')

    def test_product_bugtask(self):
        self.assertBreadcrumbUrls(
            [self.product_url, self.product_bugs_url,
             self.product_bugtask_url],
            self.product_bugtask)

    def test_package_bugtask(self):
        target = self.package_bugtask.target
        distro_url = canonical_url(target.distribution)
        distroseries_url = canonical_url(target.distroseries)
        package_url = canonical_url(target)
        package_bugs_url = canonical_url(target, rootsite='bugs')

        self.assertBreadcrumbUrls(
            [distro_url, distroseries_url, package_url, package_bugs_url,
             self.package_bugtask_url],
            self.package_bugtask)
