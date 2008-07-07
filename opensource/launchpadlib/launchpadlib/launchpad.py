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

"""Root Launchpad API class."""

__metaclass__ = type
__all__ = [
    'Launchpad',
    ]

from urlparse import urlparse
from launchpadlib._browser import Browser
from launchpadlib._utils.uri import URI
from launchpadlib.collection import Collection, Entry
from launchpadlib.credentials import AccessToken, Consumer, Credentials
from launchpadlib.person import People
from wadllib.application import Resource

# XXX BarryWarsaw 05-Jun-2008 this is a placeholder to satisfy the interface
# required by the Launchpad.bugs property below.  It is temporary and will go
# away when we flesh out the bugs interface.
class _FakeBugCollection(Collection):
    def _entry(self, entry_dict):
        return Entry(entry_dict)


class Resource:

    def __init__(self, root, resource):
        self.root = root
        self.resource = resource

    def param(self, param_name):
        """Get the value of one of the resource's parameters.

        :return: A scalar value if the parameter is not a link. A new
                 CorrespondsToResource object, whose resource is bound
                 to a representation, if the parameter is a link.
        """
        for suffix in ['_link', '_collection_link']:
            param = self.resource.get_param(param_name + suffix)
            if param is not None:
                return self._wrap_resource(param.linked_resource, param.name)
        param = self.resource.get_param(param_name)
        if param is not None:
            return param.get_value()
        return None

    def _wrap_resource(self, resource, param_name=None):
        # Get a representation of the linked resource.
        representation = self.root._browser.get(resource)

        # We know that all Launchpad resource types are
        # defined in a single document. Turn the resource's
        # type_url into an anchor into that document: this is
        # its resource type. Then look up a client-side class
        # that corresponds to the resource type.
        type_url = resource.type_url
        resource_type = urlparse(type_url)[-1]
        default = Resource
        if param_name is not None:
            if param_name.endswith('_collection_link'):
                default = Collection
            elif param_name.endswith('_link'):
                default = Entry
        r_class = RESOURCE_TYPE_CLASSES.get(resource_type, default)
        return r_class(self.root, resource.bind(
                representation, 'application/json'))

    def __getattr__(self, attr):
        """Try to retrive a parameter of the given name."""
        result = self.param(attr)
        if result is None:
            raise AttributeError("'%s' object has no attribute '%s'"
                                 % (self.__class__.__name__, attr))
        return result

    def __getitem__(self, key):
        """Look up a subordinate resource by unique ID."""
        try:
            url = self.uniqueIdToUrlPath(key)
        except NotImplementedError:
            raise TypeError("unsubscriptable object")
        import pdb; pdb.set_trace()
        resource = Resource(self.root.wadl, url,
                            self.subordinate_resource_type)
        return self._wrap_resource(resource)

    def uniqueIdToUrlPath(self, key):
        raise NotImplementedError()

    @property
    def subordinate_resource_type(self):
        raise NotImplementedError()

class Entry(Resource):
    pass


class Collection(Resource):

    def __iter__(self):
        import pdb; pdb.set_trace()


class Launchpad(Resource):
    """Root Launchpad API class.

    :ivar credentials: The credentials instance used to access Launchpad.
    :type credentials: `Credentials`
    """

    SERVICE_ROOT = 'http://api.launchpad.net/beta/'

    def __init__(self, credentials):
        """Root access to the Launchpad API.

        :param credentials: The credentials used to access Launchpad.
        :type credentials: `Credentials`
        """
        self._root = URI(self.SERVICE_ROOT)
        self.credentials = credentials
        # Get the WADL definition.
        self._browser = Browser(self.credentials)
        self.wadl = self._browser.getWADL(self._root)

        # Get the root resource.
        resource = self.wadl.get_resource_by_path('')
        bound_resource = resource.bind(
            self._browser.get(resource), 'application/json')
        super(Launchpad, self).__init__(self, bound_resource)

    @classmethod
    def login(cls, consumer_name, token_string, access_secret):
        """Convenience for setting up access credentials.

        When all three pieces of credential information (the consumer
        name, the access token and the access secret) are available, this
        method can be used to quickly log into the service root.

        :param consumer_name: the consumer name, as appropriate for the
            `Consumer` constructor
        :type consumer_name: string
        :param token_string: the access token, as appropriate for the
            `AccessToken` constructor
        :type token_string: string
        :param access_secret: the access token's secret, as appropriate for
            the `AccessToken` constructor
        :type access_secret: string
        :return: The web service root
        :rtype: `Launchpad`
        """
        consumer = Consumer(consumer_name)
        access_token = AccessToken(token_string, access_secret)
        credentials = Credentials(consumer, access_token)
        return cls(credentials)


class PersonSet(Collection):
    """A custom subclass capable of person lookup by username."""

    def uniqueIdToUrlPath(self, key):
        return self.root.SERVICE_ROOT + '~' + strkey

    @property
    def subordinate_resource_type(self):
        return '#person'


# A mapping of resource type IDs to the client-side classes that handle
# those resource types.
RESOURCE_TYPE_CLASSES = { 'people' : PersonSet }
