# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Root Launchpad API class."""

__metaclass__ = type
__all__ = [
    'Launchpad',
    ]


from urlparse import urljoin

from launchpadlib._browser import Browser
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
        if self._person_set_link is None:
            return None
        return People(self._browser, self._person_set_link)

    @property
    def bugs(self):
        # XXX Temporary
        if self._bug_set_link is None:
            return None
        return _FakeBugCollection(self._browser, self._bug_set_link)

    def create_team(self, name, display_name):
        """Create a new team.

        :param name: The name of the team
        :type name: string
        :param display_name: The 'display name' of the team
        :type display_name: string
        :return: the new team
        :rtype: `Entry`
        :raises ResponseError: when an unexpected response occurred.
        """
        url = urljoin(self.SERVICE_ROOT + '/', 'people')
        # If the team got created, a 201 status will be returned.  When that
        # happens, we dig the 'Location' header out of the response and create
        # a new Person instance with that base url.
        response, content = self._browser.post(
            url, 'create_team', name=name, display_name=display_name)
        if response.status == 201:
            # We know this has to be a person, so create and return the
            # appropriate instance.
            data = self._browser.get(response['location'])
            return Entry(data)
        raise UnexpectedResponseError(response, content)
