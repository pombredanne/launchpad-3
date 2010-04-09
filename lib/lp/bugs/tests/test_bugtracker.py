# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest
from urllib2 import HTTPError, Request

from zope.testing.doctest import NORMALIZE_WHITESPACE, ELLIPSIS
from zope.testing.doctestunit import DocTestSuite

from lazr.lifecycle.snapshot import Snapshot

from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.testing import LaunchpadFunctionalLayer

from lp.bugs.externalbugtracker import (
    BugTrackerConnectError, Mantis, MantisLoginHandler)
from lp.bugs.interfaces.bugtracker import BugTrackerType, IBugTracker
from lp.bugs.tests.externalbugtracker import Urlib2TransportTestHandler
from lp.testing import TestCaseWithFactory


class TestBugTracker(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login(ANONYMOUS)

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

    def test_watches_not_in_snapshot(self):
        # A snapshot of an IBugTracker will not contain a copy of the
        # 'watches' property.
        marker = object()
        original = self.factory.makeBugTracker()
        self.failUnless(getattr(original, 'watches', marker) is not marker)
        snapshot = Snapshot(original, providing=IBugTracker)
        self.failUnless(getattr(snapshot, 'watches', marker) is marker)

    def test_mantis_login_redirects(self):
        # The Mantis bug tracker needs a special HTTP redirect handler
        # in order to login in. Ensure that redirects to the page with
        # the login form are indeed changed to redirects the form submit
        # URL.
        handler = MantisLoginHandler()
        request = Request('http://mantis.example.com/some/path')
        # Let's pretend that Mantis sent a redirect request to the
        # login page.
        new_request = handler.redirect_request(
            request, None, 302, None, None,
            'http://mantis.example.com/login_page.php'
            '?return=%2Fview.php%3Fid%3D3301')
        self.assertEqual(
            'http://mantis.example.com/login.php?'
            'username=guest&password=guest&return=%2Fview.php%3Fid%3D3301',
            new_request.get_full_url())

    def test_mantis_login_redirect_handler_is_used(self):
        # Ensure that the special Mantis login handler is used
        # by the Mantis tracker
        tracker = Mantis('http://mantis.example.com')
        test_handler = Urlib2TransportTestHandler()
        test_handler.setRedirect('http://mantis.example.com/login_page.php'
            '?return=%2Fsome%2Fpage')
        opener = tracker._opener
        opener.add_handler(test_handler)
        opener.open('http://mantis.example.com/some/page')
        # We should now have two entries in the test handler's list
        # of visited URLs: The original URL we wanted to visit and the
        # URL changed by the MantisLoginHandler.
        self.assertEqual(
            ['http://mantis.example.com/some/page',
             'http://mantis.example.com/login.php?'
             'username=guest&password=guest&return=%2Fsome%2Fpage'],
            test_handler.accessed_urls)

    def test_mantis_opener_can_handle_cookies(self):
        # Ensure that the OpenerDirector of the Mantis bug tracker
        # handles cookies.
        tracker = Mantis('http://mantis.example.com')
        test_handler = Urlib2TransportTestHandler()
        opener = tracker._opener
        opener.add_handler(test_handler)
        opener.open('http://mantis.example.com', '')
        cookies = list(tracker._cookie_handler.cookiejar)
        self.assertEqual(1, len(cookies))
        self.assertEqual('foo', cookies[0].name)
        self.assertEqual('bar', cookies[0].value)

    def test_mantis_csv_file_http_500_error(self):
        # If a Mantis bug tracker returns a HTTP 500 error when the
        # URL for CSV data is accessed, we treat this as an
        # indication that we should screen scrape the bug data and
        # thus set csv_data to None.
        tracker = Mantis('http://mantis.example.com')
        test_handler = Urlib2TransportTestHandler()
        opener = tracker._opener
        opener.add_handler(test_handler)
        test_handler.setError(
            HTTPError(
                'http://mantis.example.com/csv_export.php', 500,
                'Internal Error', {}, None),
            'http://mantis.example.com/csv_export.php')
        self.assertIs(None, tracker.csv_data)

    def test_mantis_csv_file_other_http_errors(self):
        # If the Mantis server returns other HTTP errors than 500,
        # they appear as BugTrackerConnectErrors.
        tracker = Mantis('http://mantis.example.com')
        test_handler = Urlib2TransportTestHandler()
        opener = tracker._opener
        opener.add_handler(test_handler)
        test_handler.setError(
            HTTPError(
                'http://mantis.example.com/csv_export.php', 503,
                'Service Unavailable', {}, None),
            'http://mantis.example.com/csv_export.php')
        self.assertRaises(BugTrackerConnectError, tracker._csv_data)

        test_handler.setError(
            HTTPError(
                'http://mantis.example.com/csv_export.php', 404,
                'Not Found', {}, None),
            'http://mantis.example.com/csv_export.php')
        self.assertRaises(BugTrackerConnectError, tracker._csv_data)


def test_suite():
    suite = unittest.TestSuite()
    doctest_suite = DocTestSuite(
        'lp.bugs.model.bugtracker',
        optionflags=NORMALIZE_WHITESPACE|ELLIPSIS)

    suite.addTest(unittest.makeSuite(TestBugTracker))
    suite.addTest(doctest_suite)
    return suite
