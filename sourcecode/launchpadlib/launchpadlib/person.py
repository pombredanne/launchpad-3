# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Person/team and people/teams sets."""

__metaclass__ = type
__all__ = [
    'People',
    'Person',
    ]


from urlparse import urljoin

from launchpadlib.collection import Collection, Entry


class Person(Entry):
    """A Launchpad person or team."""


class People(Collection):
    """The set of all Launchpad people or teams."""

    def __init__(self, browser, base_url):
        """See `Collection`."""
        super(People, self).__init__(browser, base_url)
        # For random access, keep track of entries by the order in which they
        # are returned from the iterator, and by their name.
        self._peopleById = {}
        self._peopleByName = {}

    def _entry(self, entry_dict):
        """Return a new entry subclass."""
        # This must be a non-team.
        next_id = len(self._peopleById)
        person = Person(entry_dict)
        self._peopleById[next_id] = person
        self._peopleByName[person.name] = person
        return person

    def __getitem__(self, index):
        """Return the indexed person or team.

        :param index: The random access index
        :type index: integer or string
        :return: when `index` is an integer, return the index'th person in the
            collection.  When `index` is a string, return the person with a
            matching name.
        :rtype: `Person`
        :raise IndexError: when an integer is given and there is no index'th
            person in the collection.
        :raise KeyError: when a string is given and there is no named person
            in the collection.
        """
        # Fast track: we've already seen the person being requested.
        missing = object()
        if isinstance(index, basestring):
            person = self._peopleByName.get(index, missing)
            if person is not missing:
                return person
        else:
            person = self._peopleById.get(index, missing)
            if person is not missing:
                return person
        # The selected person either hasn't been seen yet or isn't in the
        # collection.  For indexing by name, we can go directly to the person
        # through our seekrit magick URL.
        if isinstance(index, basestring):
            data = self._browser.get(urljoin(self._base_url, '~' + index))
            person = Person(data)
            self._peopleByName[person.name] = person
            return person
        # For integers, unfortunately we need to iterate over all the people.
        ignore = [person for person in self]
        person = self._peopleById.get(index, missing)
        if person is missing:
            raise IndexError(index)
        return person
