# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Root Launchpad API class."""

__metaclass__ = type
__all__ = [
    'Launchpad',
    ]


from launchpadlib._browser import Browser


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

    @property
    def people(self):
        # Get the root resource.
        browser = Browser(self.credentials)
        return browser.get('http://api.launchpad.dev:8085/beta')
