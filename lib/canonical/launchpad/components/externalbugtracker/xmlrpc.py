# Copyright 2008 Canonical Ltd.  All rights reserved.

"""An XMLRPC transport which uses Launchpad's HTTP proxy."""

from xmlrpclib import Transport
from urllib2 import build_opener, HTTPCookieProcessor, Request
from urlparse import urlparse, urlunparse

class UrlLib2Transport(Transport):
    """An XMLRPC transport which uses Launchpad's HTTP proxy.

    This XMLRPC transport uses the Python urllib2 module to make the
    request, and connects via the HTTP proxy specified in the
    environment variable `http_proxy`, i present. It also handles
    cookies correctly, and in addition allows specifying the cookie
    explicitly by setting `self.auth_cookie`.

    Note: this transport isn't fit for general XML-RPC use. It is just
    good enough for some of our extrnal bug tracker implementations.
    """

    verbose = False
    auth_cookie = None

    def __init__(self, endpoint):
        self.scheme = urlparse(endpoint)[0]
        assert (
            self.scheme in ('http', 'https'),
            "Unsupported URL schene: %s" % self.scheme)
        self.cookie_processor = HTTPCookieProcessor()
        self.opener = build_opener(self.cookie_processor)

    def setCookie(self, auth_cookie):
        self.cookie_processor.cookiejar.set_cookie(self.auth_cookie)

    def request(self, host, handler, request_body, verbose=0):
        """Make an XMLRPC request.

        Uses the configured proxy server to make the connection.
        """
        url = urlunparse((self.scheme, host, handler, '', '', ''))
        headers = {'Content-type': 'text/xml'}
        request = Request(url, request_body, headers)
        response = self._parse_response(self.opener.open(request), None)
        return response
