# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Root Launchpad API class."""

__metaclass__ = type
__all__ = [
    'Launchpad',
    ]


from launchpadlib._browser import Browser
from launchpadlib._utils.uri import URI
from launchpadlib.collection import Collection, Entry
from launchpadlib.errors import UnexpectedResponseError
from launchpadlib.person import People


# XXX BarryWarsaw 05-Jun-2008 this is a placeholder to satisfy the interface
# required by the Launchpad.bugs property below.  It is temporary and will go
# away when we flesh out the bugs interface.
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
        self._root = URI(self.SERVICE_ROOT)
        self.credentials = credentials
        # Get the root resource.
        self._browser = Browser(self.credentials)
        response = self._browser.get(self._root)
        self._person_set_link = response.get(
            'PersonSetCollectionAdapter_collection_link')
        self._bug_set_link = response.get(
            'MaloneApplicationCollectionAdapter_collection_link')

    @property
    def people(self):
        if self._person_set_link is None:
            return None
        return People(self._browser, URI(self._person_set_link))

    @property
    def bugs(self):
        # XXX Temporary
        if self._bug_set_link is None:
            return None
        return _FakeBugCollection(self._browser, URI(self._bug_set_link))
