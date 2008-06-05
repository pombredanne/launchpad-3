# Copyright 2008 Canonical Ltd.  All rights reserved.

"""launchpadlib errors."""

__metaclass__ = type
__all__ = [
    'CredentialsError',
    'CredentialsFileError',
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


class UnexpectedResponseError(ResponseError):
    """An unexpected response was received."""
