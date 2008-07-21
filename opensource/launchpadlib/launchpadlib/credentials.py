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

"""launchpadlib credentials and authentication support."""

__metaclass__ = type
__all__ = [
    'AccessToken',
    'Consumer',
    'Credentials',
    ]

import httplib2
from urllib import urlencode

from ConfigParser import SafeConfigParser
from launchpadlib.errors import CredentialsFileError, HTTPError
from launchpadlib._oauth.oauth import OAuthConsumer, OAuthToken


CREDENTIALS_FILE_VERSION = '1'
WEB_ROOT = 'https://launchpad.net/'
request_token_page = '+request-token'
access_token_page = '+access-token'
authorize_token_page = '+authorize-token'


class Credentials:
    """Standard credentials storage and usage class.

    :ivar consumer: The consumer (application)
    :type consumer: `Consumer`
    :ivar access_token: Access information on behalf of the user
    :type access_token: `AccessToken`
    """
    _request_token = None

    def __init__(self, consumer=None, access_token=None):
        """The user's Launchpad API credentials.

        :param consumer: The consumer (application)
        :type consumer: `Consumer`
        :param access_token: The authenticated user access token
        :type access_token: `AccessToken`
        """
        self.consumer = consumer
        self.access_token = access_token

    def load(self, readable_file):
        """Load credentials from a file-like object.

        This overrides the consumer and access token given in the constructor
        and replaces them with the values read from the file.

        :param readable_file: A file-like object to read the credentials from
        :type readable_file: Any object supporting the file-like `read()`
            method
        """
        # Attempt to load the access token from the file.
        parser = SafeConfigParser()
        parser.readfp(readable_file)
        # Check the version number and extract the access token and
        # secret.  Then convert these to the appropriate instances.
        if not parser.has_section(CREDENTIALS_FILE_VERSION):
            raise CredentialsFileError('No configuration for version %s' %
                                       CREDENTIALS_FILE_VERSION)
        consumer_key = parser.get(
            CREDENTIALS_FILE_VERSION, 'consumer_key')
        consumer_secret = parser.get(
            CREDENTIALS_FILE_VERSION, 'consumer_secret')
        self.consumer = Consumer(consumer_key, consumer_secret)
        access_token = parser.get(
            CREDENTIALS_FILE_VERSION, 'access_token')
        access_secret = parser.get(
            CREDENTIALS_FILE_VERSION, 'access_secret')
        self.access_token = AccessToken(access_token, access_secret)

    def save(self, writable_file):
        """Write the credentials to the file-like object.

        :param writable_file: A file-like object to write the credentials to
        :type writable_file: Any object supporting the file-like `write()`
            method
        :raise CredentialsFileError: when there is either no consumer or no
            access token
        """
        if self.consumer is None:
            raise CredentialsFileError('No consumer')
        if self.access_token is None:
            raise CredentialsFileError('No access token')
        
        parser = SafeConfigParser()
        parser.add_section(CREDENTIALS_FILE_VERSION)
        parser.set(CREDENTIALS_FILE_VERSION,
                   'consumer_key', self.consumer.key)
        parser.set(CREDENTIALS_FILE_VERSION,
                   'consumer_secret', self.consumer.secret)
        parser.set(CREDENTIALS_FILE_VERSION,
                   'access_token', self.access_token.key)
        parser.set(CREDENTIALS_FILE_VERSION,
                   'access_secret', self.access_token.secret)
        parser.write(writable_file)

    def get_request_token(self):
        """Request an OAuth token to Launchpad.

        Also store the token in self._request_token. 

        This method must not be called on an object with no consumer
        specified or if an access token has already been obtained.

        :return: The URL for the user to authorize the `OAuthToken` provided
            by Launchpad.
        """
        assert self.consumer is not None, "Consumer not specified."
        assert self.access_token is None, "Access token already obtained."
        params = dict(
            oauth_consumer_key=self.consumer.key,
            oauth_signature_method='PLAINTEXT',
            oauth_signature='&')
        url = WEB_ROOT + request_token_page
        response, content = httplib2.Http().request(
            url, method='POST', body=urlencode(params))
        if response.status != 200:
            raise HTTPError(response, content)
        self._request_token = OAuthToken.from_string(content)
        url = '%s%s?oauth_token=%s' % (WEB_ROOT, authorize_token_page,
                                       self._request_token.key)
        return url

    def exchange_request_token_for_access_token(self):
        """Exchange the previously obtained request token for an access token.

        This method must not be called unless get_request_token() has been
        called and completed successfully.

        The access token will be stored as self.access_token.
        """
        assert self._request_token is not None, (
            "get_request_token() doesn't seem to have been called.")
        params = dict(
            oauth_consumer_key=self.consumer.key,
            oauth_signature_method='PLAINTEXT',
            oauth_token=self._request_token.key,
            oauth_signature='&%s' % self._request_token.secret)
        url = WEB_ROOT + access_token_page
        response, content = httplib2.Http().request(
            url, method='POST', body=urlencode(params))
        if response.status != 200:
            raise HTTPError(response, content)
        self.access_token = OAuthToken.from_string(content)


# These two classes are provided for convenience (so applications don't need
# to import from launchpadlib.oauth.oauth), and to provide a default argument
# for secret.

class Consumer(OAuthConsumer):
    """An OAuth consumer (application)."""

    def __init__(self, key, secret=''):
        super(Consumer, self).__init__(key, secret)


class AccessToken(OAuthToken):
    """An OAuth access key."""

    def __init__(self, key, secret=''):
        super(AccessToken, self).__init__(key, secret)
