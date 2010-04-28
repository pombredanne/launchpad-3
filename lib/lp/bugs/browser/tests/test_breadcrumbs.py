# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.publisher import canonical_url

from lp.bugs.interfaces.bugtracker import IBugTrackerSet
from lp.testing import login_person
from lp.testing.breadcrumbs import BaseBreadcrumbTestCase


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

    def test_bugtask_comment(self):
        login_person(self.bug.owner)
        comment = self.factory.makeBugComment(
            bug=self.bug, owner=self.bug.owner,
            subject="test comment subject", body="test comment body")
        expected_breadcrumbs = [
            ('Crumb Tester', 'http://launchpad.dev/crumb-tester'),
            ('Bugs', 'http://bugs.launchpad.dev/crumb-tester'),
            ('Bug #%s' % self.bug.id,
             'http://bugs.launchpad.dev/crumb-tester/+bug/%s' % self.bug.id),
            ('Comment #1',
             'http://bugs.launchpad.dev/crumb-tester/+bug/%s/comments/1' % self.bug.id),
            ]
        self.assertBreadcrumbs(comment, expected_breadcrumbs)


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
