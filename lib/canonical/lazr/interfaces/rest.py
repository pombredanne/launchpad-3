# Copyright 2008 Canonical Ltd.  All rights reserved.
# Pylint doesn't grok zope interfaces.
# pylint: disable-msg=E0211,E0213

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
from zope.schema.interfaces import IObject


class ICollectionField(IObject):
    """A collection associated with an entry.

    This is a marker interface.
    """


class IHTTPResource(Interface):
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
    """A resource that represents an individual Launchpad object."""

    def do_GET():
        """Retrieve this entry.

        :return: A string representation.
        """


class ICollectionResource(IHTTPResource):
    """A resource that represents a collection of entry resources."""

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


class IScopedCollection(ICollection):

    relationship = Attribute("The relationship between an entry and a "
                             "collection.")
    collection = Attribute("The collection scoped to an entry.")

