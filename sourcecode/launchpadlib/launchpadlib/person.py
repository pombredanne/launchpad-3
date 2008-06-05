# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Person/team and people/teams sets."""

__metaclass__ = type
__all__ = [
    'People',
    'Person',
    ]


from urlparse import urljoin

from launchpadlib.collection import Collection, Entry
from launchpadlib.errors import HTTPError


class Person(Entry):
    """A Launchpad person or team."""


class People(Collection):
    """The set of all Launchpad people or teams."""

    def _entry(self, entry_dict):
        """Return a new entry subclass."""
        return Person(entry_dict)

    def __getitem__(self, name):
        """Return the named person or team.

        :param name: The person's or team's name
        :type name: string
        :return: the person with the given name
        :rtype: `Person`
        :raise KeyError: when there is no named person in the collection.
        """
        missing = object()
        result = self.get(name, missing)
        if result is missing:
            raise KeyError(name)
        return result

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
            data = self._browser.get(urljoin(self._base_url, '~' + name))
        except HTTPError, error:
            if error.status == 404:
                return default
            raise
        return Person(data)
