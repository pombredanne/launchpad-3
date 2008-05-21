# Copyright 2008 Canonical Ltd.  All rights reserved.

"""launchpadlib errors."""

__metaclass__ = type
__all__ = [
    'CredentialsFileError',
    ]


class LaunchpadError(Exception):
    """Base error for the Launchpad API library."""


class CredentialsFileError(LaunchpadError):
    """Error in credentials file."""
