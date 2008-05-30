# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Person/team and people/teams sets."""

__metaclass__ = type
__all__ = [
    'People',
    'Person',
    ]


from urllib2 import HTTPError
from urlparse import urljoin

from launchpadlib.collection import Collection, Entry


class Person(Entry):
    """A Launchpad person or team."""


class People(Collection):
    """The set of all Launchpad people or teams."""

    def __init__(self, browser, base_url):
        """See `Collection`."""
        super(People, self).__init__(browser, base_url)
        # For random access, keep track of entries by name.
        self._peopleByName = {}

    def _entry(self, entry_dict):
        """Return a new entry subclass."""
        person = Person(entry_dict)
        self._peopleByName[person.name] = person
        return person

    def __getitem__(self, name):
        """Return the named person or team.

        :param index: The person's or team's name
        :type index: string
        :return: the person with the given name
        :rtype: `Person`
        :raise KeyError: when there is no named person in the collection.
        """
        # Fast track: we've already seen the person being requested.
        try:
            return self._peopleByName[name]
        except KeyError:
            pass
        # The selected person either hasn't been seen yet or isn't in the
        # collection.  For indexing by name, we can go directly to the person
        # through our seekrit magick URL.
        try:
            data = self._browser.get(urljoin(self._base_url, '~' + name))
        except HTTPError, error:
            if error.code == 404:
                raise KeyError(name)
            raise
        person = Person(data)
        self._peopleByName[person.name] = person
        return person
