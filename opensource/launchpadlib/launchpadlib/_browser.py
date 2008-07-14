# Copyright 2008 Canonical Ltd.

# This file is part of launchpadlib.
#
# launchpadlib is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# launchpadlib is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# launchpadlib.  If not, see <http://www.gnu.org/licenses/>.

"""Browser object to make requests of Launchpad web service.

The `Browser` class implements OAuth authenticated communications with
Launchpad.  It is not part of the public launchpadlib API.
"""

__metaclass__ = type
__all__ = [
    'Browser',
    ]


import httplib2
import simplejson

from urllib import urlencode
from wadllib.application import Application
from launchpadlib.errors import HTTPError
from launchpadlib._oauth.oauth import (
    OAuthRequest, OAuthSignatureMethod_PLAINTEXT)
from launchpadlib._utils import uri

OAUTH_REALM = 'https://api.launchpad.net'


class Browser:
    """A class for making calls to Launchpad web services."""

    def __init__(self, credentials):
        self.credentials = credentials
        self._connection = httplib2.Http()

    def _request(self, url, data=None, method='GET',
                 media_type='application/json', extra_headers=None):
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
        headers = {'Accept' : media_type}
        headers.update(oauth_request.to_header(OAUTH_REALM))
        if extra_headers is not None:
            headers.update(extra_headers)
        # Make the request.
        response, content = self._connection.request(
            str(url), method=method, body=data, headers=headers)
        # Turn non-2xx responses into exceptions.
        if response.status // 100 != 2:
            raise HTTPError(response, content)
        return response, content

    def get(self, resource_or_uri):
        """GET a representation of the given resource or URI."""
        if isinstance(resource_or_uri, (basestring, uri.URI)):
            url = resource_or_uri
        else:
            method = resource_or_uri.get_method('get')
            url = method.build_request_url()
        response, content = self._request(url)
        return content

    def get_wadl_application(self, url):
        """GET a WADL representation of the resource at the requested url."""
        response, content = self._request(
            url, media_type='application/vd.sun.wadl+xml')
        return Application(str(url), content)

    def post(self, url, method_name, **kws):
        """POST a request to the web service."""
        kws['ws.op'] = method_name
        data = urlencode(kws)
        return self._request(url, data, 'POST')

    def patch(self, url, representation):
        """PATCH the object at url with the updated representation."""
        self._request(url, simplejson.dumps(representation), 'PATCH',
                      extra_headers={'Content-Type': 'application/json'})
