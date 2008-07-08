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


import simplejson
from urlparse import urlparse

from launchpadlib._utils.uri import URI
from launchpadlib.errors import HTTPError
from wadllib.application import Resource as WadlResource

class Resource:

    def __init__(self, root, wadl_resource):
        if root is None:
            # This _is_ the root.
            root = self
        self.__dict__['root'] = root
        self.__dict__['wadl_resource'] = wadl_resource

    def has_param(self, param_name):
        """Does this resource have a paramater with the given name?"""
        for suffix in ['_link', '_collection_link', '']:
            if self.wadl_resource.get_param(param_name + suffix):
                return True
        return False

    def param(self, param_name):
        """Get the value of one of the resource's parameters.

        :return: A scalar value if the parameter is not a link. A new
                 Resource object, whose resource is bound to a
                 representation, if the parameter is a link.
        """
        for suffix in ['_link', '_collection_link']:
            param = self.wadl_resource.get_param(param_name + suffix)
            if param is not None:
                return self._wrap_resource(param.linked_resource, param.name)
        param = self.wadl_resource.get_param(param_name)
        if param is None:
            raise KeyError("No such parameter: %s" % param_name)
        return param.get_value()

    def _wrap_resource(self, resource, param_name=None):
        # Get a representation of the linked resource.
        representation = self.root._browser.get(resource)

        # We happen to know that all Launchpad resource types are
        # defined in a single document. Turn the resource's type_url
        # into an anchor into that document: this is its resource
        # type. Then look up a client-side class that corresponds to
        # the resource type.
        type_url = resource.type_url
        resource_type = urlparse(type_url)[-1]
        default = Entry
        if param_name is not None:
            if param_name.endswith('_collection_link'):
                default = Collection
        r_class = RESOURCE_TYPE_CLASSES.get(resource_type, default)
        return r_class(self.root, resource.bind(
                representation, 'application/json'))

    def refresh(self, new_url=None):
        if new_url is not None:
            self.wadl_resource._url = new_url
        representation = self.root._browser.get(self.wadl_resource)
        self.wadl_resource = self.wadl_resource.bind(
            representation, 'application/json')

    def __getattr__(self, attr):
        """Try to retrive a parameter of the given name."""
        try:
            return self.param(attr)
        except KeyError:
            raise AttributeError("'%s' object has no attribute '%s'"
                                 % (self.__class__.__name__, attr))

    def get(self, key, default=None):
        """Look up a subordinate resource by unique ID."""
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        """Look up a subordinate resource by unique ID."""
        try:
            url = self.uniqueIdToUrlPath(key)
        except NotImplementedError:
            raise TypeError("unsubscriptable object")
        if url is None:
            raise KeyError(key)
        resource = WadlResource(self.root.wadl, url,
                                self.subordinate_resource_type)
        return self._wrap_resource(resource)

    def uniqueIdToUrlPath(self, key):
        raise NotImplementedError()

    @property
    def subordinate_resource_type(self):
        raise NotImplementedError()


class Entry(Resource):
    """Simple bag-like class for collection entry attributes."""

    def __init__(self, root, wadl_resource):
        super(Entry, self).__init__(root, wadl_resource)
        # Initialize this here in a semi-magical way so as to stop a
        # particular infinite loop that would follow.  Setting
        # self._dirty_attributes would call __setattr__(), which would
        # turn around immediately and get self._dirty_attributes.  If
        # this latter was not in the instance dictionary, that would
        # end up calling __getattr__(), which would again reference
        # self._dirty_attributes.  This is where the infloop would
        # occur.  Poking this directly into self.__dict__ means that
        # the check for self._dirty_attributes won't call __getattr__(),
        # breaking the cycle.
        self.__dict__['_dirty_attributes'] = {}
        super(Entry, self).__init__(root, wadl_resource)

    def __getattr__(self, name):
        """Try to retrive a parameter of the given name."""
        if name != '_dirty_attributes':
            if name in self._dirty_attributes:
                return self._dirty_attributes[name]
        return super(Entry, self).__getattr__(name)

    def __setattr__(self, name, value):
        if not self.has_param(name):
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.__class__.__name__, name))
        self._dirty_attributes[name] = value

    def refresh(self, new_url=None):
        super(Entry, self).refresh(new_url)
        self._dirty_attributes.clear()

    def save(self):
        """Save changes to the entry."""
        representation = self._dirty_attributes
        # PATCH the new representation to the 'self' link.  It's possible that
        # this will cause the object to be permanently moved.  Catch that
        # exception and refresh our representation.
        try:
            self.root._browser.patch(URI(self.self_link), representation)
        except HTTPError, error:
            if error.response.status == 301:
                self.refresh(error.response['location'])
            else:
                raise
        self._dirty_attributes.clear()


class Collection(Resource):
    """Base class for web service collections."""

    def __init__(self, root, wadl_resource):
        """Create a collection object."""
        super(Collection, self).__init__(root, wadl_resource)

    def __len__(self):
        """The number of items in the collection.

        :return: length of the collection
        :rtype: int
        """
        try:
            return int(self.total_size)
        except AttributeError:
            raise TypeError('collection size is not available')

    def __iter__(self):
        """Iterate over the items in the collection.

        :return: iterator
        :rtype: sequence of `Person`
        """
        current_page = self.wadl_resource.representation
        while True:
            for entry_dict in current_page.get('entries', {}):
                resource_url = entry_dict['self_link']
                resource_type_link = entry_dict['resource_type_link']
                wadl_application = self.wadl_resource.application
                resource_type = wadl_application.get_resource_type(
                    resource_type_link)
                resource_type_name = urlparse(resource_type_link)[-1]
                entry_class = RESOURCE_TYPE_CLASSES.get(
                    resource_type_name, Entry)
                resource = WadlResource(
                    self.wadl_resource.application, resource_url,
                    resource_type.tag, entry_dict, 'application/json')
                yield entry_class(self.root, resource)
            next_link = current_page.get('next_collection_link')
            if next_link is None:
                break
            current_page = simplejson.loads(
                self.root._browser.get(URI(next_link)))


class PersonSet(Collection):
    """A custom subclass capable of person lookup by username."""

    def uniqueIdToUrlPath(self, key):
        return self.root.SERVICE_ROOT + '~' + str(key)

    @property
    def subordinate_resource_type(self):
        return '#person'


# A mapping of resource type IDs to the client-side classes that handle
# those resource types.
RESOURCE_TYPE_CLASSES = { 'people' : PersonSet }
