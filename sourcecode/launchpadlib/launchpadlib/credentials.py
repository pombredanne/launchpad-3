# Copyright 2008 Canonical Ltd.  All rights reserved.

"""launchpadlib credentials and authentication support."""

__metaclass__ = type
__all__ = [
    'AccessToken',
    'Consumer',
    'Credentials',
    ]


from ConfigParser import SafeConfigParser
from launchpadlib.errors import CredentialsFileError
from launchpadlib._oauth.oauth import OAuthConsumer, OAuthToken


CREDENTIALS_FILE_VERSION = '1'


class Credentials:
    """Standard credentials storage and usage class.

    :ivar consumer: The consumer (application)
    :type consumer: `Consumer`
    :ivar access_token: Access information on behalf of the user
    :type access_token: `AccessToken`
    """

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
