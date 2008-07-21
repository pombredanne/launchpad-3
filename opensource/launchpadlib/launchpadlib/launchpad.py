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

"""Root Launchpad API class."""

__metaclass__ = type
__all__ = [
    'Launchpad',
    ]

import os
import sys

from launchpadlib._browser import Browser
from launchpadlib._utils.uri import URI
from launchpadlib.errors import BrowserNotFoundError
from launchpadlib.resource import Resource
from launchpadlib.credentials import AccessToken, Consumer, Credentials


class Launchpad(Resource):
    """Root Launchpad API class.

    :ivar credentials: The credentials instance used to access Launchpad.
    :type credentials: `Credentials`
    """

    SERVICE_ROOT = 'https://api.launchpad.net/beta/'

    def __init__(self, credentials):
        """Root access to the Launchpad API.

        :param credentials: The credentials used to access Launchpad.
        :type credentials: `Credentials`
        """
        self._root = URI(self.SERVICE_ROOT)
        self.credentials = credentials
        # Get the WADL definition.
        self._browser = Browser(self.credentials)
        self._wadl = self._browser.get_wadl_application(self._root)

        # Get the root resource.
        root_resource = self._wadl.get_resource_by_path('')
        bound_root = root_resource.bind(
            self._browser.get(root_resource), 'application/json')
        super(Launchpad, self).__init__(None, bound_root)

    @classmethod
    def login(cls, consumer_name, token_string, access_secret):
        """Convenience for setting up access credentials.

        When all three pieces of credential information (the consumer
        name, the access token and the access secret) are available, this
        method can be used to quickly log into the service root.

        :param consumer_name: the consumer name, as appropriate for the
            `Consumer` constructor
        :type consumer_name: string
        :param token_string: the access token, as appropriate for the
            `AccessToken` constructor
        :type token_string: string
        :param access_secret: the access token's secret, as appropriate for
            the `AccessToken` constructor
        :type access_secret: string
        :return: The web service root
        :rtype: `Launchpad`
        """
        consumer = Consumer(consumer_name)
        access_token = AccessToken(token_string, access_secret)
        credentials = Credentials(consumer, access_token)
        return cls(credentials)

    @classmethod
    def get_token_and_login(cls, consumer_name):
        """Get credentials from Launchpad and log into the service root.

        This method will negotiate an OAuth access token with the service
        provider, but to complete it we will need the user to log into
        Launchpad and authorize us, so we'll open the authorization page in
        a web browser and ask the user to come back here and tell us when they
        finished the authorization process.
        """
        credentials = Credentials(Consumer(consumer_name))
        request_token, authorization_url = credentials.get_request_token()
        try:
            open_url_in_browser(authorization_url)
            print ("The authorization page (%s) should be opening in your "
                   "browser. After you have authorized this program to "
                   "access Launchpad on your behalf you should come back "
                   "here and press <Enter> to finish the authentication "
                   "process." % authorization_url)
        except BrowserNotFoundError:
            print ("Please open %s in your browser to authorize this program "
                   "to access Launchpad on your behalf. Once that is done "
                   "you should press <Enter> here to finish the "
                   "authentication process." % authorization_url)
        sys.stdin.readline()
        credentials.exchange_request_token_for_access_token()
        return cls(credentials)


def open_url_in_browser(url):
    """Open the given URL in a web browser."""
    if os.environ.get('DISPLAY'):
        # Use x-www-browser if it exists, falling back to firefox.
        browsers = ['x-www-browser', 'firefox']
    else:
        # Use www-browser if it exists, falling back to links.
        browsers = ['www-browser', 'w3m', 'links', 'lynx']
    for browser in browsers:
        if not os.system('%s "%s" &' % (browser, url)):
            return
    raise BrowserNotFoundError("Could not find browser to open %s" % url)
