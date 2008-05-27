# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Browser object to make requests of Launchpad web service.

The `Browser` class implements OAuth authenticated communications with
Launchpad.  It is not part of the public launchpadlib API.
"""

__metaclass__ = type
__all__ = [
    'Browser',
    ]


import urllib2
import urlparse

from launchpadlib.oauth.oauth import (
    OAuthRequest, OAuthSignatureMethod_PLAINTEXT)

OAUTH_REALM = 'https://api.launchpad.net'


class Browser:
    """A class for making calls to Launchpad web services."""

    def __init__(self, credentials):
        self.credentials = credentials

    def get(self, url):
        """Get the resource at the requested url."""
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
        full_headers = dict(Host=hostname)
        full_headers.update(oauth_request.to_header(OAUTH_REALM))
        # Make the request.
        url_request = urllib2.Request(url, headers=full_headers)
        f = urllib2.urlopen(url_request)
        try:
            data = f.read()
        finally:
            f.close()
        return data
