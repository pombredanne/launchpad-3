# Copyright 2008 Canonical Ltd.  All rights reserved.

"""launchpadlib testing helpers."""


__metaclass__ = type
__all__ = [
    'Launchpad',
    ]


from launchpadlib.credentials import AccessToken, Consumer, Credentials
from launchpadlib.launchpad import Launchpad as _Launchpad


class Launchpad(_Launchpad):
    """A base class for talking to the testing root service."""

    SERVICE_ROOT = 'http://api.launchpad.dev:8085/beta'

    class tokens:
        # Convenient placeholders for web service users.  Values are 2-tuples
        # of the user's access token and secret.
        salgado_change_anything = ('salgado-change-anything', 'test')
        salgado_read_nonprivate = ('salgado-read-nonprivate', 'secret')
        nopriv_read_nonprivate  = ('nopriv-read-nonprivate', 'mystery')

    def __init__(self, user):
        """Create the root service.

        :param user: One of the above hard coded access tokens.
        """
        consumer = Consumer('launchpad-library')
        access_token = AccessToken(user[0], user[1])
        credentials = Credentials(consumer, access_token)
        super(Launchpad, self).__init__(credentials)
