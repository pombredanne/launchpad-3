# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Browser object to make requests of Launchpad web service.

The `Browser` class implements OAuth authenticated communications with
Launchpad.  It is not part of the public launchpadlib API.
"""

__metaclass__ = type
__all__ = [
    'Browser',
    ]


import httplib2
import urlparse
import simplejson

from launchpadlib._oauth.oauth import (
    OAuthRequest, OAuthSignatureMethod_PLAINTEXT)
from launchpadlib.errors import HTTPError


OAUTH_REALM = 'https://api.launchpad.net'
JOINER = '&'


class Browser:
    """A class for making calls to Launchpad web services."""

    def __init__(self, credentials):
        self.credentials = credentials
        self._connection = httplib2.Http()

    def _request(self, url, data=None, method='GET'):
        """Create an authenticated request object."""
        oauth_request = OAuthRequest.from_consumer_and_token(
            self.credentials.consumer,
            self.credentials.access_token,
            http_url=url)
        oauth_request.sign_request(
            OAuthSignatureMethod_PLAINTEXT(),
            self.credentials.consumer,
            self.credentials.access_token)
        # Calculate the headers for the request.
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
        if ':' in netloc:
            hostname, port = netloc.split(':', 1)
        else:
            hostname = netloc
        headers = dict(Host=hostname)
        headers.update(oauth_request.to_header(OAUTH_REALM))
        # Make the request.
        response, content = self._connection.request(
            url, method=method, body=data, headers=headers)
        # Turn non-2xx responses into exceptions.
        if response.status // 100 != 2:
            raise HTTPError(response.status, response.reason)
        return response, content

    def get(self, url):
        """Get the resource at the requested url."""
        response, content = self._request(url)
        return simplejson.loads(content)

    def post(self, url, method_name, **kws):
        """Post a request to the web service."""
        kws['ws.op'] = method_name
        data = JOINER.join('%s=%s' % (key, value)
                           for key, value in kws.items())
        return self._request(url, data, 'POST')
