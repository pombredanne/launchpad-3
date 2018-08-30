# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An XMLRPC transport which uses requests."""

__metaclass__ = type
__all__ = [
    'RequestsTransport',
    ]


from io import BytesIO
from urlparse import (
    urlparse,
    urlunparse,
    )
from xmlrpclib import (
    ProtocolError,
    Transport,
    )

import requests
from requests.cookies import RequestsCookieJar

from lp.bugs.externalbugtracker.base import repost_on_redirect_hook
from lp.services.config import config
from lp.services.timeout import (
    override_timeout,
    urlfetch,
    )
from lp.services.utils import traceback_info


class RequestsTransport(Transport):
    """An XML-RPC transport which uses requests.

    This XML-RPC transport uses the Python requests module to make the
    request.  (In fact, it uses lp.services.timeout.urlfetch, which wraps
    requests and deals with timeout handling.)

    Note: this transport isn't fit for general XML-RPC use.  It is just good
    enough for some of our external bug tracker implementations.

    :param endpoint: The URL of the XML-RPC server.
    """

    verbose = False

    def __init__(self, endpoint, cookie_jar=None):
        Transport.__init__(self, use_datetime=True)
        self.scheme, self.host = urlparse(endpoint)[:2]
        assert self.scheme in ('http', 'https'), (
            "Unsupported URL scheme: %s" % self.scheme)
        if cookie_jar is None:
            cookie_jar = RequestsCookieJar()
        self.cookie_jar = cookie_jar
        self.timeout = config.checkwatches.default_socket_timeout

    def setCookie(self, cookie_str):
        """Set a cookie for the transport to use in future connections."""
        name, value = cookie_str.split('=')
        self.cookie_jar.set(
            name, value, domain=self.host, path='', expires=False,
            discard=None, rest=None)

    def request(self, host, handler, request_body, verbose=0):
        """Make an XMLRPC request.

        Uses the configured proxy server to make the connection.
        """
        url = urlunparse((self.scheme, host, handler, '', '', ''))
        # httplib can raise a UnicodeDecodeError when using a Unicode
        # URL, a non-ASCII body and a proxy. http://bugs.python.org/issue12398
        if not isinstance(url, bytes):
            url = url.encode('utf-8')
        try:
            with override_timeout(self.timeout):
                response = urlfetch(
                    url, method='POST', headers={'Content-Type': 'text/xml'},
                    data=request_body, cookies=self.cookie_jar,
                    hooks={'response': repost_on_redirect_hook},
                    use_proxy=True)
        except requests.HTTPError as e:
            raise ProtocolError(
                url.decode('utf-8'), e.response.status_code, e.response.reason,
                e.response.headers)
        else:
            traceback_info(response.text)
            return self.parse_response(BytesIO(response.content))
