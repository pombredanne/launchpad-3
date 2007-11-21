# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.servers import LaunchpadTestRequest

from canonical.launchpad.browser.openiddiscovery import (
    XRDSContentNegotiationMixin)

class SampleView(XRDSContentNegotiationMixin, LaunchpadView):
    def template(self):
        return 'Normal content'

    def xrds_template(self):
        return 'XRDS content'


class ContentNegotiationTests(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)

    def tearDown(self):
        logout()

    def createRequestAndView(self, host, path, query, accept):
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
        # Test that the normal content is published if HTML is
        # preferred to XRDS.  An X-XRDS-Location header is added in
        # this case.
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
        # Test that the XRDS content is returned if XRDS is preferred
        # to HTML.  In this case, the content type is set, and no
        # X-XRDS-Location header is generated.
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
        self.assertEqual(
            request.response.getHeader('x-xrds-location'), None)

    def test_no_accept(self):
        # If no accept header is sent, HTML is preferred.
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '', '')
        content = view()
        self.assertEqual(content, 'Normal content')
        self.assertEqual(
            request.response.getHeader('x-xrds-location'),
            'http://launchpad.dev/~sabdfl/+xrds')

    def test_accept_neither(self):
        # If an accept header is sent that does not include HTML or
        # XRDS, send HTML.
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl', '', 'image/png')
        content = view()
        self.assertEqual(content, 'Normal content')
        self.assertEqual(
            request.response.getHeader('x-xrds-location'),
            'http://launchpad.dev/~sabdfl/+xrds')

    def test_call_xrds_method(self):
        # Calling the xrds() method results in rendering the XRDS
        # content.
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
        # Check that requests with a non-canonical URL result in a redirect.
        request, view = self.createRequestAndView(
            'launchpad.dev', '/~sabdfl/+index', 'foo=bar', '')
        content = view()
        self.assertEqual(content, '')
        self.assertEqual(request.response.getStatus(), 302)
        self.assertEqual(request.response.getHeader('Location'),
                         'http://launchpad.dev/~sabdfl')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

