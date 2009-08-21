# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getMultiAdapter

from canonical.lazr.testing.menus import make_fake_request
from canonical.launchpad.webapp.publisher import RootObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class BaseBreadcrumbTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(BaseBreadcrumbTestCase, self).setUp()
        self.root = RootObject()

    def _getHierarchyView(self, url, traversed_objects):
        request = make_fake_request(url, traversed_objects)
        return getMultiAdapter((self.root, request), name='+hierarchy')

    def _getBreadcrumbs(self, url, traversed_objects):
        view = self._getHierarchyView(url, traversed_objects)
        return view.items()

    def _getBreadcrumbsTexts(self, url, traversed_objects):
        return [crumb.text
                for crumb in self._getBreadcrumbs(url, traversed_objects)]

    def _getBreadcrumbsURLs(self, url, traversed_objects):
        return [crumb.url
                for crumb in self._getBreadcrumbs(url, traversed_objects)]

