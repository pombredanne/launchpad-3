# Copyright 2008 Canonical Ltd.  All rights reserved.

"""launchpadlib credentials and authentication support."""

__metaclass__ = type
__all__ = [
    'AccessToken',
    'Consumer',
    'Credentials',
    ]


import errno

from ConfigParser import SafeConfigParser
from launchpadlib.errors import CredentialsFileError
from launchpadlib.oauth.oauth import OAuthConsumer, OAuthToken


CREDENTIALS_FILE_VERSION = '1'


class Credentials:
    """Standard credentials storage and usage class.

    :ivar consumer: The consumer (application)
    :type consumer: `Consumer`
    :ivar access_token: Access information on behalf of the user
    :type access_token: `AccessToken`
    """

    def __init__(self, consumer, access_token):
        """The user's Launchpad API credentials.

        :param consumer: The consumer (application)
        :type consumer: `Consumer`
        :param access_token: The authenticated user access token
        :type access_token: `AccessToken`
        """
        self.consumer = consumer
        self.access_token = access_token


class StorableCredentials(Credentials):
    """Credentials which can be stored and retrieved from the file system.

    :ivar filename: The file name that the access information is to be
        in or retrieved from.
    :type filename: string
    """

    def __init__(self, filename):
        """The user's stored Launchpad API credentials.

        If the given file exists and contains Launchpad API credentials, they
        are loaded and used.  Otherwise, after instantiating this class, just
        set the `consumer` and `access_token` instance variables and call
        `save()`.

        :param filename: The file name that the access information is to be
            in or retrieved from.
        :type filename: string
        """
        # Attempt to load the access token from the file.
        super(StorableCredentials, self).__init__(None, None)
        self.filename = filename
        try:
            credentials_file = open(self.filename, 'r')
        except IOError, error:
            if error.errno != errno.ENOENT:
                raise
            # The file didn't exist so there are no credentials to load.
            # That's okay, the application may provide the credentials later.
        else:
            try:
                parser = SafeConfigParser()
                parser.readfp(credentials_file)
            finally:
                credentials_file.close()
            # Check the version number and extract the access token and
            # secret.  Then convert these to the appropriate instances.
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

    def save(self):
        """Save the credentials on the file system."""
        # Version 1 credentials files.
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

        credentials_file = open(self.filename, 'w')
        try:
            parser.write(credentials_file)
        finally:
            credentials_file.close()


class Consumer(OAuthConsumer):
    """An OAuth consumer (application)."""

    def __init__(self, key, secret=''):
        super(Consumer, self).__init__(key, secret)


class AccessToken(OAuthToken):
    """An OAuth access key."""

    def __init__(self, key, secret=''):
        super(AccessToken, self).__init__(key, secret)
