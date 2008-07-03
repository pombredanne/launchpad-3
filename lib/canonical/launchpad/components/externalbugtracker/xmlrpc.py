# Copyright 2008 Canonical Ltd.  All rights reserved.

"""An XMLRPC transport which uses urllib2."""


from cookielib import Cookie
from urllib2 import build_opener, HTTPCookieProcessor, Request
from urlparse import urlparse, urlunparse
from xmlrpclib import Transport

class UrlLib2Transport(Transport):
    """An XMLRPC transport which uses urllib2.

    This XMLRPC transport uses the Python urllib2 module to make the
    request, and connects via the HTTP proxy specified in the
    environment variable `http_proxy`, i present. It also handles
    cookies correctly, and in addition allows specifying the cookie
    explicitly by setting `self.auth_cookie`.

    Note: this transport isn't fit for general XML-RPC use. It is just
    good enough for some of our extrnal bug tracker implementations.

    :param endpoint: The URL of the XMLRPC server.
    """

    verbose = False

    def __init__(self, endpoint):
        self.scheme, self.host = urlparse(endpoint)[:2]
        assert (
            self.scheme in ('http', 'https'),
            "Unsupported URL schene: %s" % self.scheme)
        self.cookie_processor = HTTPCookieProcessor()
        self.opener = build_opener(self.cookie_processor)

    def setCookie(self, cookie_str):
        """Set a cookie for the transport to use in future connections."""
        name, value = cookie_str.split('=')
        cookie = Cookie(
            version=0, name=name, value=value,
            port=None, port_specified=False,
            domain=self.host, domain_specified=True,
            domain_initial_dot=None,
            path=None, path_specified=False,
            secure=False, expires=False, discard=None,
            comment=None, comment_url=None, rest=None)
        self.cookie_processor.cookiejar.set_cookie(cookie)

    def request(self, host, handler, request_body, verbose=0):
        """Make an XMLRPC request.

        Uses the configured proxy server to make the connection.
        """
        url = urlunparse((self.scheme, host, handler, '', '', ''))
        headers = {'Content-type': 'text/xml'}
        request = Request(url, request_body, headers)
        response = self._parse_response(self.opener.open(request), None)
        return response
