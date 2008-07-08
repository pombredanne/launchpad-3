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

from launchpadlib._browser import Browser
from launchpadlib._utils.uri import URI
from launchpadlib.resource import Resource, Collection, Entry
from launchpadlib.credentials import AccessToken, Consumer, Credentials

# XXX BarryWarsaw 05-Jun-2008 this is a placeholder to satisfy the interface
# required by the Launchpad.bugs property below.  It is temporary and will go
# away when we flesh out the bugs interface.
class _FakeBugCollection(Collection):
    def _entry(self, entry_dict):
        return Entry(entry_dict)


class Launchpad(Resource):
    """Root Launchpad API class.

    :ivar credentials: The credentials instance used to access Launchpad.
    :type credentials: `Credentials`
    """

    SERVICE_ROOT = 'http://api.launchpad.net/beta/'

    def __init__(self, credentials):
        """Root access to the Launchpad API.

        :param credentials: The credentials used to access Launchpad.
        :type credentials: `Credentials`
        """
        self._root = URI(self.SERVICE_ROOT)
        self.credentials = credentials
        # Get the WADL definition.
        self._browser = Browser(self.credentials)
        self.wadl = self._browser.getWADL(self._root)

        # Get the root resource.
        resource = self.wadl.get_resource_by_path('')
        bound_resource = resource.bind(
            self._browser.get(resource), 'application/json')
        super(Launchpad, self).__init__(None, bound_resource)

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
