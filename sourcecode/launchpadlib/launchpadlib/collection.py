# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Common support for web service collections."""

__metaclass__ = type
__all__ = [
    'Collection',
    'Entry',
    ]


from launchpadlib._utils.uri import URI


class EntryAttributeDescriptor:
    """Descriptor for Entry attributes settable via the web service."""

    def __init__(self, attribute_name):
        self._attribute_name = attribute_name
        self._value_key = '_%s_value' % attribute_name
        self.is_dirty = False

    def __get__(self, instance, owner):
        if instance is None:
            raise AttributeError('Class attribute: %s' % self._attribute_name)
        return getattr(instance, self._value_key)

    def __set__(self, instance, value):
        setattr(instance, self._value_key, value)
        self.is_dirty = True


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
        for key, value in entry_dict.items():
            if key.endswith('_link'):
                self._links[key[:-5]] = value
            else:
                descriptor = EntryAttributeDescriptor(key)
                # Store the descriptor into the class's dictionary so that it
                # will act like a descriptor.
                setattr(Entry, key, descriptor)
                # Now set the value on the instance, invoking the descriptor,
                # but be sure to reset the dirty flag, since it's not
                # appropriate to set it in the constructor.
                setattr(self, key, value)
                descriptor.is_dirty = False

    def save(self):
        representation = {}
        # Find all the dirty attributes and build up a representation of them
        # to be set on the web service.  Reset the dirty flags while we're at
        # it.
        for name, descriptor in self.__class__.__dict__.items():
            if getattr(descriptor, 'is_dirty', False):
                representation[name] = getattr(self, name)
                descriptor.is_dirty = False
        # PATCH the new representation to the 'self' link.
        self._browser.patch(URI(self._links['self']), representation)


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
