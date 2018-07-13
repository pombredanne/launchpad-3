# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Bugzilla BugTracker."""

__metaclass__ = type

from xml.parsers.expat import ExpatError
import xmlrpclib

import responses
import transaction

from lp.bugs.externalbugtracker.base import UnparsableBugData
from lp.bugs.externalbugtracker.bugzilla import Bugzilla
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import ZopelessLayer


class TestBugzillaGetRemoteBugBatch(TestCaseWithFactory):
    """Test POSTs to Bugzilla's bug-search page."""

    layer = ZopelessLayer

    base_url = "http://example.com/"

    @responses.activate
    def test_post_to_search_form_does_not_crash(self):
        responses.add(
            "POST", self.base_url + "xml.cgi",
            body="<bugzilla>%s</bugzilla>" % self.factory.getUniqueString())
        bugzilla = Bugzilla(self.base_url)
        bugzilla.getRemoteBugBatch([])

    @responses.activate
    def test_repost_on_redirect_does_not_crash(self):
        responses.add(
            "POST", self.base_url + "xml.cgi", status=302,
            headers={"Location": self.base_url + "buglist.cgi"})
        responses.add(
            "POST", self.base_url + "buglist.cgi",
            body="<bugzilla>%s</bugzilla>" % self.factory.getUniqueString())
        bugzilla = Bugzilla(self.base_url)
        bugzilla.getRemoteBugBatch([])

    @responses.activate
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
        responses.add("POST", self.base_url + "xml.cgi", body=result_text)
        bugzilla = Bugzilla(self.base_url)
        self.assertRaises(UnparsableBugData, bugzilla.getRemoteBugBatch, [])


class TestBugzillaSniffing(TestCase):
    """Tests for sniffing remote Bugzilla capabilities."""

    layer = ZopelessLayer

    def test_expat_error(self):
        # If an `ExpatError` is raised when sniffing for XML-RPC capabilities,
        # it is taken to mean that no XML-RPC capabilities exist.
        bugzilla = Bugzilla("http://not.real")

        class Transport(xmlrpclib.Transport):
            def request(self, host, handler, request, verbose=None):
                raise ExpatError("mismatched tag")

        bugzilla._test_xmlrpc_proxy = xmlrpclib.ServerProxy(
            '%s/xmlrpc.cgi' % bugzilla.baseurl, transport=Transport())

        # We must abort any existing transactions before attempting to call
        # the _remoteSystemHas*() functions because they require that none be
        # in progress.
        transaction.abort()

        self.assertFalse(bugzilla._remoteSystemHasBugzillaAPI())
        self.assertFalse(bugzilla._remoteSystemHasPluginAPI())
