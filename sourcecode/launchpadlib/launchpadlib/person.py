# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Person/team and people/teams sets."""

__metaclass__ = type
__all__ = [
    'People',
    ]


from launchpadlib.collection import Collection, Entry
from launchpadlib.errors import HTTPError


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
