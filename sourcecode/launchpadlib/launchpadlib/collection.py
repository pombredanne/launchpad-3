# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Common support for web service collections."""

__metaclass__ = type
__all__ = [
    'Collection',
    'Entry',
    ]


class Entry:
    """Simple bag-like class for collection entry attributes."""

    def __init__(self, entry_dict):
        self.__dict__.update(entry_dict)


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
            for entry_dict in current_page.get('entries', []):
                yield Entry(entry_dict)
            next_link = current_page.get('next_collection_link')
            if next_link is None:
                break
            current_page = self._browser.get(next_link)

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
