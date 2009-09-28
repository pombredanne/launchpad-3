# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)
from lp.bugs.interfaces.bugtracker import IBugTrackerSet
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
            ["Crumb Tester", "Bugs"],
            self._getBreadcrumbsTexts(url, self.traversed_objects))


class TestBugTrackerBreadcrumbs(BaseBreadcrumbTestCase):

    def setUp(self):
        super(TestBugTrackerBreadcrumbs, self).setUp()
        self.bug_tracker_set = getUtility(IBugTrackerSet)
        self.bug_tracker_set_url = canonical_url(
            self.bug_tracker_set, rootsite='bugs')
        self.bug_tracker = self.factory.makeBugTracker()
        self.bug_tracker_url = canonical_url(
            self.bug_tracker, rootsite='bugs')

    def test_bug_tracker_set(self):
        # Check TestBugTrackerSetBreadcrumb.
        traversed_objects = [
            self.root, self.bug_tracker_set]
        urls = self._getBreadcrumbsURLs(
            self.bug_tracker_set_url, traversed_objects)
        self.assertEquals(self.bug_tracker_set_url, urls[-1])
        texts = self._getBreadcrumbsTexts(
            self.bug_tracker_set_url, traversed_objects)
        self.assertEquals("Bug trackers", texts[-1])

    def test_bug_tracker(self):
        # Check TestBugTrackerBreadcrumb (and
        # TestBugTrackerSetBreadcrumb).
        traversed_objects = [
            self.root, self.bug_tracker_set, self.bug_tracker]
        urls = self._getBreadcrumbsURLs(
            self.bug_tracker_url, traversed_objects)
        self.assertEquals(self.bug_tracker_url, urls[-1])
        self.assertEquals(self.bug_tracker_set_url, urls[-2])
        texts = self._getBreadcrumbsTexts(
            self.bug_tracker_url, traversed_objects)
        self.assertEquals(self.bug_tracker.title, texts[-1])
        self.assertEquals("Bug trackers", texts[-2])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
