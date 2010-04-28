# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.app import zapi
from zope.component import ComponentLookupError, getMultiAdapter

from canonical.lazr.testing.menus import make_fake_request
from canonical.launchpad.layers import setFirstLayer
from canonical.launchpad.webapp.publisher import canonical_url, RootObject
from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view
from lp.testing.publication import test_traverse


class BaseBreadcrumbTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer
    request_layer = None

    def setUp(self):
        super(BaseBreadcrumbTestCase, self).setUp()
        self.root = RootObject()

    def assertBreadcrumbs(self, obj, expected):
        """Assert that the breadcrumbs for obj match the expected values.

        :param expected: A list of tuples containing (text, url) pairs.
        """
        crumbs = self.getBreadcrumbsForObject(obj)
        self.assertEqual(
            expected,
            [(crumb.text, crumb.url) for crumb in crumbs])

    def assertBreadcrumbTexts(self, obj, expected):
        """The text of the breadcrumbs for obj match the expected values."""
        crumbs = self.getBreadcrumbsForObject(obj)
        self.assertEqual(expected, [crumb.text for crumb in crumbs])

    def assertBreadcrumbUrls(self, obj, expected):
        """The urls of the breadcrumbs for obj match the expected values."""
        crumbs = self.getBreadcrumbsForObject(obj)
        self.assertEqual(expected, [crumb.url for crumb in crumbs])

    def getBreadcrumbsForObject(self, obj):
        """Get the breadcrumbs for the specified object.

        Traverse to the canonical_url of the object, and use the request from
        that to feed into the initialized hierarchy view so we get the
        traversed objects.
        """
        url = canonical_url(obj)
        obj, view, request = test_traverse(url)
        view = create_initialized_view(obj, '+hierarchy', request=request)
        return view.items

    def _getHierarchyView(self, url, traversed_objects):
        obj, view, request = test_traverse(url)
        return create_initialized_view(obj, '+hierarchy', request=request)

    def _getBreadcrumbs(self, url, traversed_objects):
        view = self._getHierarchyView(url, traversed_objects)
        return view.items

    def _getBreadcrumbsTexts(self, url, traversed_objects):
        crumbs = self._getBreadcrumbs(url, traversed_objects)
        return [crumb.text for crumb in crumbs]

    def _getBreadcrumbsURLs(self, url, traversed_objects):
        crumbs = self._getBreadcrumbs(url, traversed_objects)
        return [crumb.url for crumb in crumbs]
