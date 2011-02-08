# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Bugzilla BugTracker."""

__metaclass__ = type

from StringIO import StringIO

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.externalbugtracker.base import UnparsableBugData
from lp.bugs.externalbugtracker.bugzilla import Bugzilla
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


class TestBugzillaGetRemoteBugBatch(TestCaseWithFactory):
    """Test POSTs to Bugzilla's bug-search page."""
    layer = DatabaseFunctionalLayer

    base_url = "http://example.com/"

    def _makeInstrumentedBugzilla(self, page=None, content=None):
        """Create a `Bugzilla` with a fake urlopen."""
        if page is None:
            page = self.factory.getUniqueString()
        bugzilla = Bugzilla(self.base_url)
        if content is None:
            content = "<bugzilla>%s</bugzilla>" % (
                self.factory.getUniqueString())
        fake_page = StringIO(content)
        fake_page.url = self.base_url + page
        bugzilla.urlopen = FakeMethod(result=fake_page)
        return bugzilla

    def test_post_to_search_form_does_not_crash(self):
        page = self.factory.getUniqueString()
        bugzilla = self._makeInstrumentedBugzilla(page)
        bugzilla.getRemoteBugBatch([])

    def test_repost_on_redirect_does_not_crash(self):
        bugzilla = self._makeInstrumentedBugzilla()
        bugzilla.getRemoteBugBatch([])

    def test_reports_invalid_search_result(self):
        # Sometimes bug searches may go wrong, yielding an HTML page
        # instead.  getRemoteBugBatch rejects and reports search results
        # of the wrong page type.
        result_text = """
            <html>
                <body>
                    <h1>This is not actually a search result.</h1>
                </body>
            </html>
            """
        bugzilla = self._makeInstrumentedBugzilla(content=result_text)
        self.assertRaises(UnparsableBugData, bugzilla.getRemoteBugBatch, [])
