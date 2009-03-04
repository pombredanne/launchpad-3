# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for traversal from the root branch object.."""

__metaclass__ = type

import unittest

from bzrlib.urlutils import join as urljoin

from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.browser.launchpad import LaunchpadRootNavigation
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.servers import LaunchpadTestRequest


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
        request = LaunchpadTestRequest(PATH_INFO=urljoin('/+branch', path))
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
        branch = self.factory.makeAnyBranch()
        product = removeSecurityProxy(branch.product)
        product.development_focus.user_branch = branch
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
        path = urljoin(branch.unique_name, '+edit')
        self.assertRedirects(path, canonical_url(branch, view_name='+edit'))

    # XXX: product series


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
