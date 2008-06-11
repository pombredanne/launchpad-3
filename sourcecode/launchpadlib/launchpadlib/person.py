# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Person/team and people/teams sets."""

__metaclass__ = type
__all__ = [
    'People',
    ]


from launchpadlib._utils.uri import URI
from launchpadlib.collection import Collection, Entry
from launchpadlib.errors import HTTPError, UnexpectedResponseError


class People(Collection):
    """The set of all Launchpad people or teams."""

    def get(self, name, default=None):
        """Return the named person or team.

        :param name: The person's or team's name
        :type name: string
        :return: the person with the given name or None if there is no such
            person
        :rtype: `Person` or None
        """
        # For indexing by name, we can go directly to the person through our
        # seekrit magick URL.
        try:
            data = self._browser.get(self._base_url.resolve('~' + name))
        except HTTPError, error:
            if error.response.status == 404:
                return default
            raise
        return Entry(data)

    def newTeam(self, name, display_name):
        """Create a new team.

        :param name: The name of the team
        :type name: string
        :param display_name: The 'display name' of the team
        :type display_name: string
        :return: the new team
        :rtype: `Entry`
        :raises ResponseError: when an unexpected response occurred.
        """
        # If the team got created, a 201 status will be returned.  When that
        # happens, we dig the 'Location' header out of the response and create
        # a new Person instance with that base url.
        response, content = self._browser.post(
            self._base_url, 'newTeam', name=name, display_name=display_name)
        if response.status == 201:
            # We know this has to be a person, so create and return the
            # appropriate instance.
            data = self._browser.get(URI(response['location']))
            return Entry(data)
        raise UnexpectedResponseError(response, content)
