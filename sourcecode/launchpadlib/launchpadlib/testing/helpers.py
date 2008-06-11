# Copyright 2008 Canonical Ltd.  All rights reserved.

"""launchpadlib testing helpers."""


__metaclass__ = type
__all__ = [
    'nopriv_read_nonprivate',
    'salgado_change_anything',
    'salgado_read_nonprivate',
    ]


from launchpadlib.credentials import AccessToken, Consumer, Credentials
from launchpadlib.launchpad import Launchpad as _Launchpad


class Launchpad(_Launchpad):
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
        return Launchpad.login(
            'launchpad-library', self.token_string, self.access_secret)


salgado_change_anything = KnownTokens('salgado-change-anything', 'test')
salgado_read_nonprivate = KnownTokens('salgado-read-nonprivate', 'secret')
nopriv_read_nonprivate = KnownTokens('nopriv-read-nonprivate', 'mystery')
