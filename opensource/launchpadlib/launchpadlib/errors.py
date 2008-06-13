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
