# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for traversal from the root branch object.."""

__metaclass__ = type

import unittest

from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.browser.launchpad import LaunchpadRootNavigation
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.url import urlappend


class TestBranchTraversal(TestCaseWithFactory):
    """Branches are traversed to from IPersons. Test we can reach them.

    This class tests the `PersonNavigation` class to see that we can traverse
    to branches from such objects.
    """

    layer = DatabaseFunctionalLayer

    def assertNotFound(self, path):
        self.assertRaises(NotFound, self.traverse, path)

    def assertRedirects(self, segments, url):
        redirection = self.traverse(segments)
        self.assertEqual(url, redirection.target)

    def traverse(self, path):
        """Traverse to 'segments' using a 'LaunchpadRootNavigation' object.

        Using the Zope traversal machinery, traverse to the path given by
        'segments', starting at a `LaunchpadRootNavigation` object.

        :param segments: A list of path segments.
        :return: The object found.
        """
        request = LaunchpadTestRequest(PATH_INFO=urlappend('/+branch', path))
        segments = reversed(path.split('/'))
        request.setTraversalStack(segments)
        traverser = LaunchpadRootNavigation(None, request=request)
        return traverser.publishTraverse(request, '+branch')

    def test_unique_name_traversal(self):
        # Traversing to /+branch/<unique_name> redirects to the page for that
        # branch.
        branch = self.factory.makeAnyBranch()
        self.assertRedirects(branch.unique_name, canonical_url(branch))

    def test_no_such_unique_name(self):
        # Traversing to /+branch/<unique_name> where 'unique_name' is for a
        # branch that doesn't exist will generate a 404.
        branch = self.factory.makeAnyBranch()
        self.assertNotFound(branch.unique_name + 'wibble')

    def test_product_alias(self):
        # Traversing to /+branch/<product> redirects to the page for the
        # branch that is the development focus branch for that product.
        branch = self.factory.makeProductBranch()
        product = removeSecurityProxy(branch.product)
        product.development_focus.branch = branch
        self.assertRedirects(product.name, canonical_url(branch))

    def test_nonexistent_product(self):
        # Traversing to /+branch/<no-such-product> generates a 404.
        self.assertNotFound('non-existent')

    def test_product_without_dev_focus(self):
        # Traversing to a product without a development focus generates a 404.
        product = self.factory.makeProduct()
        self.assertNotFound(product.name)

    def test_trailing_path_redirect(self):
        # If there are any trailing path segments after the branch identifier,
        # these stick around at the redirected URL.
        branch = self.factory.makeAnyBranch()
        path = urlappend(branch.unique_name, '+edit')
        self.assertRedirects(path, canonical_url(branch, view_name='+edit'))

    def test_product_series_redirect(self):
        # Traversing to /+branch/<product>/<series> redirects to the branch
        # for that series, if there is one.
        branch = self.factory.makeProductBranch()
        product = branch.product
        series = self.factory.makeProductSeries(product=product)
        removeSecurityProxy(series).branch = branch
        self.assertRedirects(
            '%s/%s' % (product.name, series.name), canonical_url(branch))

    def test_nonexistent_product_series(self):
        # /+branch/<product>/<series> generates a 404 if there is no such
        # series.
        product = self.factory.makeProduct()
        self.assertNotFound('%s/nonexistent' % product.name)

    def test_no_branch_for_series(self):
        # If there's no branch for a product series, generate a 404.
        series = self.factory.makeProductSeries()
        self.assertNotFound('%s/%s' % (series.product.name, series.name))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
