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
        request = self._make_request(url, traversed_objects)
        return getMultiAdapter((self.root, request), name='+hierarchy')

    def _getBreadcrumbs(self, url, traversed_objects):
        view = self._getHierarchyView(url, traversed_objects)
        return view.items

    def _getBreadcrumbsTexts(self, url, traversed_objects):
        crumbs = self._getBreadcrumbs(url, traversed_objects)
        return [crumb.text for crumb in crumbs]

    def _getBreadcrumbsURLs(self, url, traversed_objects):
        crumbs = self._getBreadcrumbs(url, traversed_objects)
        return [crumb.url for crumb in crumbs]

    def _make_request(self, url, traversed_objects):
        """Create and return a LaunchpadTestRequest.

        Set the given list of traversed objects as request.traversed_objects,
        also appending the view that the given URL points to, to mimic how
        request.traversed_objects behave in a real request.

        XXX: salgado, bug=432025, 2009-09-17: Instead of setting
        request.traversed_objects manually, we should duplicate parts of
        zope.publisher.publish.publish here (or in make_fake_request()) so
        that tests don't have to specify the list of traversed objects for us
        to set here.
        """
        request = make_fake_request(url, traversed_objects=traversed_objects)
        if self.request_layer is not None:
            setFirstLayer(request, self.request_layer)
        last_segment = request._traversed_names[-1]
        if traversed_objects:
            obj = traversed_objects[-1]
            # Assume the last_segment is the name of the view on the last
            # traversed object, and if we fail to find a view with that name,
            # use the default view.
            try:
                view = getMultiAdapter((obj, request), name=last_segment)
            except ComponentLookupError:
                default_view_name = zapi.getDefaultViewName(obj, request)
                view = getMultiAdapter((obj, request), name=default_view_name)
            request.traversed_objects.append(view)
        return request
