# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Root Launchpad API class."""

__metaclass__ = type
__all__ = [
    'Launchpad',
    ]


import simplejson
from launchpadlib._browser import Browser


class Launchpad:
    """Root Launchpad API class.

    :ivar credentials: The credentials instance used to access Launchpad.
    :type credentials: `Credentials`
    """

    SERVICE_ROOT = 'http://api.launchpad.net/beta'

    def __init__(self, credentials):
        """Root access to the Launchpad API.

        :param credentials: The credentials used to access Launchpad.
        :type credentials: `Credentials`
        """
        self.credentials = credentials
        # Get the root resource.
        self._browser = Browser(self.credentials)
        response = simplejson.loads(self._browser.get(self.SERVICE_ROOT))
        self._person_set_link = response.get(
            'PersonSetCollectionAdapter_collection_link')
        self._bug_set_link = response.get(
            'BugCollection_collection_link')

    @property
    def people(self):
        # XXX Temporary
        if self._person_set_link is None:
            return None
        return []

    @property
    def bugs(self):
        # XXX Temporary
        if self._bug_set_link is None:
            return None
        return []
