# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces for different kinds of HTTP resources."""

__metaclass__ = type
__all__ = [
    'ICollection',
    'ICollectionField',
    'ICollectionResource',
    'IEntry',
    'IEntryResource',
    'IHTTPResource',
    'IJSONPublishable',
    'IScopedCollection',
    'IServiceRootResource'
    ]

from zope.interface import Interface, Attribute
from zope.publisher.interfaces import IPublishTraverse
from zope.schema.interfaces import IObject
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

class ICollectionField(IObject):
    """A collection associated with an entry.

    This is a marker interface.
    """


class IHTTPResource(IPublishTraverse, ICanonicalUrlData):
    """An object published through HTTP."""

    def __call__(self):
        """Publish the object."""


class IJSONPublishable(Interface):
    """An object that can be published as a JSON data structure."""

    def toDataForJSON(self):
        """Return a representation that can be turned into JSON.

        The representation must consist entirely of simple data
        structures and IJSONPublishable objects.
        """

class IServiceRootResource(IHTTPResource):
    """A service root object that also acts as a resource."""


class IEntryResource(IHTTPResource):
    """A resource that represents an individual Launchpad object."""

    def path(self):
        """Find the URL fragment the entry uses for itself."""

    def do_GET(self):
        """Retrieve this entry.

        :return: A string representation.
        """


class ICollectionResource(IHTTPResource, IPublishTraverse):
    """A resource that represents a collection of entry resources."""

    def path(self):
        """Find the URL fragment that names this collection."""

    def do_GET(self):
        """Retrieve this collection.

        :return: A string representation.
        """


class IEntry(IJSONPublishable):
    """An entry, exposed as a resource by an IEntryResource."""

    parent_collection_name = Attribute("URI name of the parent collection.")

    def fragment(self):
        """Return a URI fragment that uniquely identifies this entry.

        This might be the entry's unique ID or some other unique identifier.
        It must be possible to use this fragment to find the entry again
        in a collection of all such entries.
        """


class ICollection(Interface):
    """A collection, driven by an ICollectionResource."""

    def lookupEntry(self, name):
        """Look up an entry in the collection by unique identifier.

        :return: An IEntry object.
        """

    def find(self):
        """Retrieve all entries in the collection under the given scope.

        :return: A list of IEntry objects.
        """


class IScopedCollection(ICollection):

    relationship = Attribute("The relationship between an entry and a"
                             "collection.")
    collection = Attribute("The collection scoped to an entry.")
