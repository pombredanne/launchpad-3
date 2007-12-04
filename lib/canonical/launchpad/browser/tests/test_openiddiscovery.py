# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenID discovery tests."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.browser.openiddiscovery import (
    XRDSContentNegotiationMixin)
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadFunctionalLayer


class SampleView(XRDSContentNegotiationMixin, LaunchpadView):
    def template(self):
        return 'Normal content'

    def xrds_template(self):
        return 'XRDS content'


class ContentNegotiationTests(unittest.TestCase):
    """Tests for XRDS content negotiation."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)

    def tearDown(self):
        logout()

    def createRequestAndView(self, host, path, query, accept):
        """Create a test request and matching view."""
        context = getUtility(IPersonSet).getByName('sabdfl')
        request = LaunchpadTestRequest(
            HTTP_HOST=host,
            SERVER_URL='http://%s' % host,
            PATH_INFO=path,
            QUERY_STRING=query,
            HTTP_ACCEPT=accept)
        view = SampleView(context, request)
        return request, view

    def test_prefer_html(self):
        """Test rendering when HTML is preferred to XRDS.

        As well as the normal content being rendered, an
        X-XRDS-Location header is added pointing at the XRDS document.
        """
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '',
            'text/html, application/xrds+xml;q=0.5, */*')
        content = view()
        self.assertEqual(content, 'Normal content')
        self.assertEqual(
            request.response.getHeader('vary'), 'Accept')
        self.assertEqual(
            request.response.getHeader('x-xrds-location'),
            'http://launchpad.dev/~sabdfl/+xrds')

    def test_prefer_xrds(self):
        """Test rendering when XRDS is preferred to HTML.

        In this case, no X-XRDS-Location header is added, as this
        would cause the client to make a second request for the XRDS.
        """
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '',
            'text/html;q=0.5, application/xrds+xml, */*')
        content = view()
        self.assertEqual(content, 'XRDS content')
        self.assertEqual(
            request.response.getHeader('vary'), 'Accept')
        self.assertEqual(
            request.response.getHeader('content-type'),
            'application/xrds+xml')
        # It is important that no X-XRDS-Location header is generated
        # in this case, since that would cause the client to make a
        # second request for the XRDS data.
        self.assertEqual(
            request.response.getHeader('x-xrds-location'), None)

    def test_no_accept(self):
        """Test that HTML is rendered when no Accept header is given."""
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '', '')
        content = view()
        self.assertEqual(content, 'Normal content')
        self.assertEqual(
            request.response.getHeader('x-xrds-location'),
            'http://launchpad.dev/~sabdfl/+xrds')

    def test_accept_neither(self):
        """Test that HTML is rendered if neither HTML or XRDS is preferred."""
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '', 'image/png')
        content = view()
        self.assertEqual(content, 'Normal content')
        self.assertEqual(
            request.response.getHeader('x-xrds-location'),
            'http://launchpad.dev/~sabdfl/+xrds')

    def test_call_xrds_method(self):
        """Test that the xrds() method renders the XRDS content."""
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '', '')
        content = view.xrds()
        self.assertEqual(content, 'XRDS content')
        self.assertEqual(
            request.response.getHeader('content-type'),
            'application/xrds+xml')
        self.assertEqual(
            request.response.getHeader('x-xrds-location'), None)

    def test_normalise_url(self):
        """Test that requests to non-canonical URLs redirect."""
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl/+index', 'foo=bar', '')
        content = view()
        self.assertEqual(content, '')
        self.assertEqual(request.response.getStatus(), 302)
        self.assertEqual(request.response.getHeader('Location'),
                         'http://launchpad.dev/~sabdfl')

    def test_disable_discovery(self):
        """Test enable_xrds_discovery=False case."""
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '', '')
        view.enable_xrds_discovery = False
        content = view()
        self.assertEqual(content, 'Normal content')
        self.assertEqual(
            request.response.getHeader('x-xrds-location'), None)
        # The same goes if application/xrds+xml is preferred to HTML
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '',
            'text/html;q=0.5, application/xrds+xml, */*')
        view.enable_xrds_discovery = False
        content = view()
        self.assertEqual(content, 'Normal content')
        self.assertEqual(
            request.response.getHeader('x-xrds-location'), None)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

