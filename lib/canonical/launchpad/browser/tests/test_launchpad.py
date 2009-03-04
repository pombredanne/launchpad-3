# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for traversal from the root branch object.."""

__metaclass__ = type

import unittest

from bzrlib.urlutils import join as urljoin

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

    def assertRedirects(self, segments, obj):
        redirection = self.traverse(segments)
        self.assertEqual(canonical_url(obj), redirection.target)

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
        # Traversing to +/branch/<unique_name> redirects to the page for that
        # branch.
        branch = self.factory.makeAnyBranch()
        self.assertRedirects(branch.unique_name, branch)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
