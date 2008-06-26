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

"""Common support for web service collections."""

__metaclass__ = type
__all__ = [
    'Collection',
    'Entry',
    ]


from launchpadlib._utils.uri import URI
from launchpadlib.errors import HTTPError


class Entry:
    """Simple bag-like class for collection entry attributes."""

    def __init__(self, entry_dict, browser):
        """Create an `Entry` instance.

        :param entry_dict: a dictionary containing all the entry's attributes
            as received from the web service as a JSON dictonary.
        :type entry_dict: dict
        :param browser: the browser instance for talking to Launchpad
        :type browser: `Browser`
        """
        # Initialize this here in a semi-magical way so as to stop a
        # particular infinite loop that would follow.  Setting self._browser
        # calls __setattr__() but that turns around immediately and gets
        # self._attributes.  If this latter was not in the instance
        # dictionary, that would end up calling __getattr__(), which would
        # again reference self._attributes.  This is where the infloop would
        # occur.  Poking this directly into self.__dict__ means that the check
        # for self._attributes won't call __getattr__(), breaking the cycle.
        self.__dict__['_attributes'] = {}
        self._browser = browser
        self._initialize(entry_dict)

    def _initialize(self, entry_dict):
        """Initialize this entry from a JSON dictionary.

        :param entry_dict: a dictionary containing all the entry's attributes
            as received from the web service as a JSON dictonary.
        :type entry_dict: dict
        """
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
        if name in self._attributes:
            # This is a special web service attribute, so track it separately
            # and mark it as dirty for any future save().
            self._attributes[name] = value
            self._dirty_attributes.add(name)
        else:
            super(Entry, self).__setattr__(name, value)

    def __getattr__(self, name):
        # All normal attribute access bypasses __getattr__(), so the only
        # attributes that need special treatment are the web service ones.
        # We just need to turn missing attributes into AttributeErrors instead
        # of KeyErrors.
        try:
            return self._attributes[name]
        except KeyError:
            raise AttributeError(name)

    def _refresh(self, url):
        entry_dict = self._browser.get(URI(url))
        self._initialize(entry_dict)

    def save(self):
        """Save changes to the entry."""
        representation = {}
        # Find all the dirty attributes and build up a representation of them
        # to be set on the web service.
        for name in self._dirty_attributes:
            representation[name] = self._attributes[name]
        # PATCH the new representation to the 'self' link.  It's possible that
        # this will cause the object to be permanently moved.  Catch that
        # exception and refresh our representation.
        try:
            self._browser.patch(URI(self._links['self']), representation)
        except HTTPError, error:
            if error.response.status == 301:
                self._refresh(error.response['location'])
            else:
                raise
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
