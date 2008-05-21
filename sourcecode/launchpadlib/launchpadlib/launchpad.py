# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Root Launchpad API class."""

__metaclass__ = type
__all__ = [
    'Launchpad',
    ]


from launchpadlib.errors import LaunchpadError


class Launchpad:
    """Root Launchpad API class.

    :ivar credentials: The credentials instance used to access Launchpad.
    :type credentials: `Credentials`
    """

    def __init__(self, credentials):
        """Root access to the Launchpad API.

        :param credentials: The credentials used to access Launchpad.
        :type credentials: `Credentials`
        """
        self.credentials = credentials
        if (self.credentials.consumer_key == 'launchpadlib-example' and
            self.credentials.access_token == 'hgm2VK35vXD6rLg5pxWw'):
            self.people = ['jim']
        else:
            raise LaunchpadError('BADNESS')
