# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)
from lp.testing import ANONYMOUS, login


class TestBugTaskBreadcrumb(BaseBreadcrumbTestCase):

    def setUp(self):
        super(TestBugTaskBreadcrumb, self).setUp()
        product = self.factory.makeProduct(
            name='crumb-tester', displayname="Crumb Tester")
        self.bug = self.factory.makeBug(product=product)
        self.bugtask_url = canonical_url(
            self.bug.default_bugtask, rootsite='bugs')
        self.traversed_objects = [
            self.root, product, self.bug.default_bugtask]

    def test_bugtask(self):
        urls = self._getBreadcrumbsURLs(
            self.bugtask_url, self.traversed_objects)
        self.assertEquals(urls[-1], self.bugtask_url)
        texts = self._getBreadcrumbsTexts(
            self.bugtask_url, self.traversed_objects)
        self.assertEquals(texts[-1], "Bug #%d" % self.bug.id)

    def test_bugtask_child(self):
        url = canonical_url(
            self.bug.default_bugtask, rootsite='bugs', view_name='+activity')
        urls = self._getBreadcrumbsURLs(url, self.traversed_objects)
        self.assertEquals(urls[-1], "%s/+activity" % self.bugtask_url)
        self.assertEquals(urls[-2], self.bugtask_url)
        texts = self._getBreadcrumbsTexts(url, self.traversed_objects)
        self.assertEquals(texts[-1], "+activity")
        self.assertEquals(texts[-2], "Bug #%d" % self.bug.id)

    def test_bugtask_private_bug(self):
        # A breadcrumb is not generated for a bug that the user does
        # not have permission to view.
        login('foo.bar@canonical.com')
        self.bug.setPrivate(True, self.bug.owner)
        login(ANONYMOUS)
        url = canonical_url(self.bug.default_bugtask, rootsite='bugs')
        self.assertEquals(
            ['http://launchpad.dev/crumb-tester',
             'http://bugs.launchpad.dev/crumb-tester'],
            self._getBreadcrumbsURLs(url, self.traversed_objects))
        self.assertEquals(
            ["Crumb Tester", "Bugs on crumb-tester"],
            self._getBreadcrumbsTexts(url, self.traversed_objects))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
