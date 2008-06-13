# Copyright 2008 Canonical Ltd.  All rights reserved.

"""launchpadlib errors."""

__metaclass__ = type
__all__ = [
    'CredentialsError',
    'CredentialsFileError',
    'HTTPError',
    'LaunchpadError',
    'ResponseError',
    'UnexpectedResponseError',
    ]


class LaunchpadError(Exception):
    """Base error for the Launchpad API library."""


class CredentialsError(LaunchpadError):
    """Base credentials/authentication error."""


class CredentialsFileError(CredentialsError):
    """Error in credentials file."""


class ResponseError(LaunchpadError):
    """Error in response."""

    def __init__(self, response, content):
        LaunchpadError.__init__(self)
        self.response = response
        self.content = content


class UnexpectedResponseError(ResponseError):
    """An unexpected response was received."""

    def __str__(self):
        return '%s: %s' % (self.response.status, self.response.reason)


class HTTPError(ResponseError):
    """An HTTP non-2xx response code was received."""

    def __str__(self):
        return 'HTTP Error %s: %s' % (
            self.response.status, self.response.reason)
