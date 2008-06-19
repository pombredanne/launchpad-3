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

"""launchpadlib testing helpers."""


__metaclass__ = type
__all__ = [
    'TestableLaunchpad',
    'nopriv_read_nonprivate',
    'salgado_read_nonprivate',
    'salgado_with_full_permissions',
    ]


from launchpadlib.launchpad import Launchpad


class TestableLaunchpad(Launchpad):
    """A base class for talking to the testing root service."""

    # Use our test service root.
    SERVICE_ROOT = 'http://api.launchpad.dev:8085/beta'


class KnownTokens:
    """Known access token/secret combinations."""

    def __init__(self, token_string, access_secret):
        self.token_string = token_string
        self.access_secret = access_secret

    def login(self):
        """Login using these credentials."""
        return TestableLaunchpad.login(
            'launchpad-library', self.token_string, self.access_secret)


salgado_with_full_permissions = KnownTokens('salgado-change-anything', 'test')
salgado_read_nonprivate = KnownTokens('salgado-read-nonprivate', 'secret')
nopriv_read_nonprivate = KnownTokens('nopriv-read-nonprivate', 'mystery')
