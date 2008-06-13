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

    def _entry(self, entry_dict):
        """Return an entry instance.

        :param entry_dict: The entry's JSON dictionary
        :type entry_dict: dict
        :return: A subclass of `Entry` or None if the `entry_dict` does not
            correspond to the correct type of entry (e.g. it's a team for a
            person collection).
        :rtype: `Entry` subclass or None
        """
        raise NotImplementedError

    def __iter__(self):
        """Iterate over the items in the collection.

        :return: iterator
        :rtype: sequence of `Person`
        """
        current_page = self._info
        while True:
            for entry_dict in current_page.get('entries', []):
                entry = self._entry(entry_dict)
                if entry is not None:
                    yield entry
            next_link = current_page.get('next_collection_link')
            if next_link is None:
                break
            current_page = self._browser.get(next_link)
