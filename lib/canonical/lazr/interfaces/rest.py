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
from zope.schema import List
from zope.schema.interfaces import IObject
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

class ICollectionField(IObject):
    """A collection associated with an entry.

    This is a marker interface.
    """


class IHTTPResource(IPublishTraverse, ICanonicalUrlData):
    """An object published through HTTP."""

    def __call__():
        """Publish the object."""


class IJSONPublishable(Interface):
    """An object that can be published as a JSON data structure."""

    def toDataForJSON():
        """Return a representation that can be turned into JSON.

        The representation must consist entirely of simple data
        structures and IJSONPublishable objects.
        """

class IServiceRootResource(IHTTPResource):
    """A service root object that also acts as a resource."""


class IEntryResource(IHTTPResource):
    """A resource that represents an individual object."""

    def path():
        """Find the URL fragment the entry uses for itself."""

    def do_GET():
        """Retrieve this entry.

        :return: A string representation.
        """

    def getContext():
        """Return the underlying entry for this resource."""


class ICollectionResource(IHTTPResource, IPublishTraverse):
    """A resource that represents a collection of entry resources."""

    def path():
        """Find the URL fragment that names this collection."""

    def getEntryPath(entry):
        """Find the URL fragment that names the given entry."""

    def do_GET():
        """Retrieve this collection.

        :return: A string representation.
        """

    def makeEntryResource(entry, request):
        """Construct an entry resource for the given entry.

        The entry is presumed to be have this collection as its
        parent.

        :param entry: The entry that needs to be made into a resource.
        :param request: The HTTP request that's being processed.
        """


class IEntry(IJSONPublishable):
    """An entry, exposed as a resource by an IEntryResource."""

    # Soon, Launchpad's existing Navigation classes will substitute for
    # web service-specific path information, and this will be removed.
    _parent_collection_path = List(
        title=u"Instructions for traversing to the parent collection",
        description=u"This is an alternating list of strings and callables. "
            "The first element in the list, a string, designates one of the "
            "web service's top-level collections. The second element (if "
            "there is one) is a callable which takes the IEntry "
            "implementation as its only argument. It's expected to return one "
            "of the entries in the top-level collection. The third element "
            "(if there is one) is a string which designates one of the scoped "
            "collections associated with that entry. And so on. Strings and "
            "callables alternate, traversing the object graph. The list must "
            "end with a string.")

    def fragment():
        """Return a URI fragment that uniquely identifies this entry.

        This might be the entry's unique ID or some other unique identifier.
        It must be possible to use this fragment to find the entry again
        in a collection of all such entries.
        """


class ICollection(Interface):
    """A collection, driven by an ICollectionResource."""

    def lookupEntry(name):
        """Look up an entry in the collection by unique identifier.

        :return: An IEntry object.
        """

    def find():
        """Retrieve all entries in the collection under the given scope.

        :return: A list of IEntry objects.
        """

    def getEntryPath(child):
        """Choose a URL fragment for one of this collection's entries."""


class IScopedCollection(ICollection):

    relationship = Attribute("The relationship between an entry and a "
                             "collection.")
    collection = Attribute("The collection scoped to an entry.")

