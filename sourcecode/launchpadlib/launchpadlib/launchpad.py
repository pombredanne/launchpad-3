# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Root Launchpad API class."""

__metaclass__ = type
__all__ = [
    'Launchpad',
    ]


from launchpadlib._browser import Browser
from launchpadlib.collection import Collection, Entry
from launchpadlib.person import People


class _FakeBugCollection(Collection):
    def _entry(self, entry_dict):
        return Entry(entry_dict)


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
        response = self._browser.get(self.SERVICE_ROOT)
        self._person_set_link = response.get(
            'PersonSetCollectionAdapter_collection_link')
        self._bug_set_link = response.get(
            'BugCollection_collection_link')

    @property
    def people(self):
        # XXX Temporary
        if self._person_set_link is None:
            return None
        return People(self._browser, self._person_set_link)

    @property
    def bugs(self):
        # XXX Temporary
        if self._bug_set_link is None:
            return None
        return _FakeBugCollection(self._browser, self._bug_set_link)
