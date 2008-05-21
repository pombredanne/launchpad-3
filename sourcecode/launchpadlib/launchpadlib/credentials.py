# Copyright 2008 Canonical Ltd.  All rights reserved.

"""launchpadlib credentials and authentication support."""

__metaclass__ = type
__all__ = [
    'Credentials',
    ]


import errno

from ConfigParser import SafeConfigParser
from launchpadlib.errors import CredentialsFileError


CREDENTIALS_FILE_VERSION = '1'


class Credentials:
    """Standard credentials storage and usage class.

    :ivar consumer_key: The consumer key
    :type consumer_key: string
    :ivar access_token: The access token, or None if no access token can be
        found or was given.
    :type access_token: string or None
    :ivar filename: The file name that the access token was stored in or
        retrieved from, or None if not available.
    :type filename: string or None.
    """

    consumer_key = None
    access_token = None
    filename = None

    def __init__(self, consumer_key, access_token=None, filename=None):
        """The user's Launchpad API credentials.

        There are several ways to use this class.  You must provide the
        consumer key.

        If you provide only the filename, this class will attempt to retrieve
        the access token from the file.  If the file is found and it contains
        an access token, it will be used.

        If you provide the access token explicitly, it will be used in lieu of
        any access token found in the credentials file.  If you provide both
        the filename and the access token, the explicit access token will be
        used, but the `save()` method can be used to store the access token
        for later (in plain text).

        :param consumer_key: The application consumer key.
        :type consumer_key: string
        :param access_token: The authenticated user access token.
        :type access_token: string
        :param filename: The path to the file to store and/or retrieve the
            user's credentials in.  Note that the credentials will be stored
            in plain text.
        :type filename: string
        """
        self.consumer_key = consumer_key
        self.access_token = access_token
        self.filename = filename

        if self.access_token is None and self.filename is not None:
            # Attempt to load the access token from the file.
            try:
                credentials_file = open(self.filename, 'r')
            except IOError, error:
                if error.errno != errno.ENOENT:
                    raise
                # The file didn't exist so there are no credentials to load.
                # That's okay, the application may provide the access token
                # later.
            else:
                try:
                    parser = SafeConfigParser()
                    parser.readfp(credentials_file)
                finally:
                    credentials_file.close()
                # Check the version number and extract the access token.
                self.access_token = parser.get(
                    CREDENTIALS_FILE_VERSION, 'access_token')

    def save(self, filename=None):
        """Save the credentials in the named file.

        :param filename: If given, overrides the file to save the credentials
            in.  Otherwise the previously given filename is used.
        :type filename: string
        """
        # Version 1 credentials files.
        if filename is None:
            filename = self.filename
        if filename is None:
            raise CredentialsFileError('No credentials file given')
        if self.access_token is None:
            raise CredentialsFileError('No access token to save')
        
        parser = SafeConfigParser()
        parser.add_section(CREDENTIALS_FILE_VERSION)
        parser.set(CREDENTIALS_FILE_VERSION,
                   'access_token', self.access_token)

        credentials_file = open(filename, 'w')
        try:
            parser.write(credentials_file)
        finally:
            credentials_file.close()
