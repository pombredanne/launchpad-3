# Copyright 2008 Canonical Ltd.

# This file is part of launchpadlib.
#
# launchpadlib is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# launchpadlib is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# launchpadlib.  If not, see <http://www.gnu.org/licenses/>.

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
        return Entry(data, self._browser)

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
            return Entry(data, self._browser)
        raise UnexpectedResponseError(response, content)
