# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Common support for web service collections."""

__metaclass__ = type
__all__ = [
    'Collection',
    'Entry',
    ]


from launchpadlib._utils.uri import URI


class Entry:
    """Simple bag-like class for collection entry attributes."""

    def __init__(self, entry_dict, browser):
        self._browser = browser
        # The entry_dict contains lots of information mixed up in the same
        # namespace.  Everything that's a link to other information is
        # contained in a key ending with '_link'.  We'll treat everything else
        # as an attribute of this object.  Settable attributes (unless they're
        # read-only but we don't yet know that) are the names of all the
        # non-link keys.
        self._links = {}
        self._attributes = {}
        self._dirty_attributes = set()
        for key, value in entry_dict.items():
            if key.endswith('_link'):
                self._links[key[:-5]] = value
            else:
                self._attributes[key] = value

    def __setattr__(self, name, value):
        if name.startswith('_'):
            # Short-circuit any non-public attributes.  We have to do this so
            # our own implementation-specific attributes will work.
            super(Entry, self).__setattr__(name, value)
        elif name in self._attributes:
            self._attributes[name] = value
            self._dirty_attributes.add(name)
        else:
            # It's a 'plain' attribute that the web service doesn't know
            # about, so just set it like normal.
            super(Entry, self).__setattr__(name, value)

    def __getattr__(self, name):
        if name in self._attributes:
            return self._attributes[name]
        else:
            return super(Entry, self).__getattr__(name)

    def save(self):
        representation = {}
        # Find all the dirty attributes and build up a representation of them
        # to be set on the web service.
        for name in self._dirty_attributes:
            representation[name] = self._attributes[name]
        # PATCH the new representation to the 'self' link.
        self._browser.patch(URI(self._links['self']), representation)
        self._dirty_attributes.clear()


class Collection:
    """Base class for web service collections."""

    def __init__(self, browser, base_url):
        """Create a collection object.

        :param browser: The credentialed web service browser
        :type browser: `Browser`
        :param base_url: The base URL of the collection
        :type base_url: string
        """
        self._browser = browser
        self._base_url = base_url
        self._cached_info = None

    @property
    def _info(self):
        """Retrieve and cache the JSON information for the collection."""
        if self._cached_info is None:
            self._cached_info = self._browser.get(self._base_url)
        return self._cached_info

    def __len__(self):
        """The number of items in the collection.

        :return: length of the collection
        :rtype: int
        """
        try:
            return self._info['total_size']
        except KeyError:
            raise TypeError('collection size is not available')

    def __iter__(self):
        """Iterate over the items in the collection.

        :return: iterator
        :rtype: sequence of `Person`
        """
        current_page = self._info
        while True:
            for entry_dict in current_page.get('entries', {}):
                yield Entry(entry_dict, self._browser)
            next_link = current_page.get('next_collection_link')
            if next_link is None:
                break
            current_page = self._browser.get(URI(next_link))

    def __getitem__(self, name):
        """Return the named entry.

        :param name: The collection entry's name
        :type name: string
        :return: the named Entry
        :rtype: `Entry`
        :raise KeyError: when there is no named entry in the collection.
        """
        missing = object()
        result = self.get(name, missing)
        if result is missing:
            raise KeyError(name)
        return result

    def get(self, name, default=None):
        """Return the named entry.

        :param name: The collection entry's name
        :type name: string
        :return: the entry with the given name or None if there is no such
            entry
        :rtype: `Entry` or None
        """
        raise NotImplementedError
