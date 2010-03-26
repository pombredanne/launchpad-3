# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from datetime import datetime, timedelta

from pytz import utc

from zope.security.proxy import removeSecurityProxy
from zope.testing.doctest import NORMALIZE_WHITESPACE, ELLIPSIS
from zope.testing.doctestunit import DocTestSuite

from lazr.lifecycle.snapshot import Snapshot

from canonical.launchpad.ftests import login_person
from canonical.testing import LaunchpadFunctionalLayer

from lp.bugs.interfaces.bugtracker import BugTrackerType, IBugTracker
from lp.testing import TestCaseWithFactory


class TestBugTracker(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def test_multi_product_constraints_observed(self):
        """BugTrackers for which multi_product=True should return None
        when no remote product is passed to getBugFilingURL().

        BugTrackers for which multi_product=False should still return a
        URL even when getBugFilingURL() is passed no remote product.
        """
        for type in BugTrackerType.items:
            bugtracker = self.factory.makeBugTracker(bugtrackertype=type)

            bugtracker_urls = bugtracker.getBugFilingAndSearchLinks(None)
            bug_filing_url = bugtracker_urls['bug_filing_url']
            bug_search_url = bugtracker_urls['bug_search_url']

            if bugtracker.multi_product:
                self.assertTrue(
                    bug_filing_url is None,
                    "getBugFilingAndSearchLinks() should return a "
                    "bug_filing_url of None for BugTrackers of type %s when "
                    "no remote product is passed." %
                    type.title)
                self.assertTrue(
                    bug_search_url is None,
                    "getBugFilingAndSearchLinks() should return a "
                    "bug_search_url of None for BugTrackers of type %s when "
                    "no remote product is passed." %
                    type.title)
            else:
                self.assertTrue(
                    bug_filing_url is not None,
                    "getBugFilingAndSearchLinks() should not return a "
                    "bug_filing_url of None for BugTrackers of type %s when "
                    "no remote product is passed." %
                    type.title)
                self.assertTrue(
                    bug_search_url is not None,
                    "getBugFilingAndSearchLinks() should not return a "
                    "bug_search_url of None for BugTrackers of type %s when "
                    "no remote product is passed." %
                    type.title)

    def test_attributes_not_in_snapshot(self):
        # A snapshot of an IBugTracker will not contain a copy of
        # several attributes.
        marker = object()
        original = self.factory.makeBugTracker()
        attributes = [
            'watches',
            'watches_needing_update',
            'watches_ready_to_check',
            'watches_with_unpushed_comments',
            ]
        for attribute in attributes:
            self.failUnless(
                getattr(original, attribute, marker) is not marker,
                "Attribute %s missing from bug tracker." % attribute)
        snapshot = Snapshot(original, providing=IBugTracker)
        for attribute in attributes:
            self.failUnless(
                getattr(snapshot, attribute, marker) is marker,
                "Attribute %s not missing from snapshot." % attribute)

    def test_watches_ready_to_check(self):
        bug_tracker = self.factory.makeBugTracker()
        # Initially there are no watches, so none need to be checked.
        self.failUnless(bug_tracker.watches_ready_to_check.is_empty())
        # A bug watch without a next_check set is not ready either.
        bug_watch = self.factory.makeBugWatch(bugtracker=bug_tracker)
        removeSecurityProxy(bug_watch).next_check = None
        self.failUnless(bug_tracker.watches_ready_to_check.is_empty())
        # If we set its next_check date, it will be ready.
        removeSecurityProxy(bug_watch).next_check = (
            datetime.now(utc) - timedelta(hours=1))
        self.failUnless(1, bug_tracker.watches_ready_to_check.count())
        self.failUnlessEqual(
            bug_watch, bug_tracker.watches_ready_to_check.one())

    def test_watches_with_unpushed_comments(self):
        bug_tracker = self.factory.makeBugTracker()
        # Initially there are no watches, so there are no unpushed
        # comments.
        self.failUnless(bug_tracker.watches_with_unpushed_comments.is_empty())
        # A new bug watch has no comments, so the same again.
        bug_watch = self.factory.makeBugWatch(bugtracker=bug_tracker)
        self.failUnless(bug_tracker.watches_with_unpushed_comments.is_empty())
        # A comment linked to the bug watch will be found.
        login_person(bug_watch.bug.owner)
        message = self.factory.makeMessage(owner=bug_watch.owner)
        bug_message = bug_watch.bug.linkMessage(message, bug_watch)
        self.failUnless(1, bug_tracker.watches_with_unpushed_comments.count())
        self.failUnlessEqual(
            bug_watch, bug_tracker.watches_with_unpushed_comments.one())
        # Once the comment has been pushed, it will no longer be found.
        removeSecurityProxy(bug_message).remote_comment_id = 'brains'
        self.failUnless(bug_tracker.watches_with_unpushed_comments.is_empty())


def test_suite():
    suite = unittest.TestSuite()
    doctest_suite = DocTestSuite(
        'lp.bugs.model.bugtracker',
        optionflags=NORMALIZE_WHITESPACE|ELLIPSIS)

    suite.addTest(unittest.makeSuite(TestBugTracker))
    suite.addTest(doctest_suite)
    return suite
