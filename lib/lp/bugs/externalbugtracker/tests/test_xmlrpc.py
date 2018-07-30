# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.bugs.externalbugtracker.xmlrpc`."""

__metaclass__ = type

import socket
from xml.parsers.expat import ExpatError

from fixtures import MockPatch
import requests
import responses

from lp.bugs.externalbugtracker.xmlrpc import RequestsTransport
from lp.bugs.tests.externalbugtracker import ensure_response_parser_is_expat
from lp.testing import TestCase


class TestRequestsTransport(TestCase):
    """Tests for `RequestsTransport`."""

    @responses.activate
    def test_expat_error(self):
        # Malformed XML-RPC responses cause xmlrpclib to raise an ExpatError.
        responses.add(
            "POST", "http://www.example.com/xmlrpc",
            body="<params><mis></match></params>")
        transport = RequestsTransport("http://not.real/")

        # The Launchpad production environment selects Expat at present. This
        # is quite strict compared to the other parsers that xmlrpclib can
        # possibly select.
        ensure_response_parser_is_expat(transport)

        self.assertRaises(
            ExpatError, transport.request,
            'www.example.com', 'xmlrpc', "<methodCall />")

    def test_unicode_url(self):
        # Python's httplib doesn't like Unicode URLs much. Ensure that
        # they don't cause it to crash, and we get a post-serialisation
        # connection error instead.
        self.useFixture(MockPatch(
            "socket.getaddrinfo",
            side_effect=socket.gaierror(
                socket.EAI_NONAME, "Name or service not known")))
        transport = RequestsTransport(u"http://test.invalid/")
        for proxy in (None, "http://squid.internal:3128/"):
            self.pushConfig("launchpad", http_proxy=proxy)
            e = self.assertRaises(
                requests.ConnectionError,
                transport.request, u"test.invalid", u"xmlrpc",
                u"\N{SNOWMAN}".encode('utf-8'))
            self.assertIn("Name or service not known", str(e))
