# Copyright 2008 Canonical Ltd.  All rights reserved.

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
