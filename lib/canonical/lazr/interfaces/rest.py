# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces for different kinds of HTTP resources."""

__metaclass__ = type
__all__ = [
    'ICollection',
    'ICollectionResource',
    'IEntry',
    'IEntryResource',
    'IHTTPResource',
    'IJSONPublishable',
    ]

from zope.interface import Interface
from zope.publisher.interfaces import IPublishTraverse


class IHTTPResource(IPublishTraverse):
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


class IEntryResource(IHTTPResource):
    """A resource that represents an individual Launchpad object."""
    def do_GET(self):
        """Retrieve this entry.

        :return: A string representation.
        """


class ICollectionResource(IHTTPResource):
    """A resource that represents a collection of entry resources."""

    def do_GET(self):
        """Retrieve this collection.

        :return: A string representation.
        """


class IEntry(IJSONPublishable):
    """An entry, exposed as a resource by an IEntryResource."""


class ICollection(Interface):
    """A collection, driven by an ICollectionResource."""

    def lookupEntry(self, request, name):
        """Look up an entry in the collection by unique identifier.

        :return: An IEntry object.
        """

    def find(self):
        """Retrieve all entries in the collection.

        :return: A list of IEntry objects.
        """
