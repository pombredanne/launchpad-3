# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.app import zapi
from zope.component import ComponentLookupError, getMultiAdapter

from canonical.lazr.testing.menus import make_fake_request
from canonical.launchpad.layers import setFirstLayer
from canonical.launchpad.webapp.publisher import RootObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class BaseBreadcrumbTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer
    request_layer = None

    def setUp(self):
        super(BaseBreadcrumbTestCase, self).setUp()
        self.root = RootObject()

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
